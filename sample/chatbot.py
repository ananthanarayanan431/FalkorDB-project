"""LangGraph chatbot that uses FalkorDB as long-term memory.

Each turn runs three nodes:
  extract  -> pull facts and entity names out of the user message, write facts to FalkorDB
  retrieve -> read facts connected to those entities back from FalkorDB
  respond  -> answer using the retrieved facts plus the conversation history
"""
import os

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from pydantic import BaseModel, Field

from sample.graph_store import GraphStore

EXTRACT_PROMPT = """You maintain a knowledge graph built from a user's chat messages.
From the user's latest message return:
- facts: durable facts stated in the message, as (subject, relation, object) triples.
  Use "user" as the subject for first-person statements. Keep entity names short
  (e.g. "hyderabad", "langgraph"). Use short verb phrases for relations
  (e.g. "works at", "lives in", "likes"). Return no facts for questions or small talk.
- entities: every entity the latest message mentions or asks about, so related facts can be looked up.
Earlier messages are context only. Use them to resolve pronouns such as "he" or "it",
and only extract facts that the latest message states."""

ANSWER_PROMPT = """You are a helpful assistant with a long-term memory stored in a graph database.
Facts retrieved from memory for this message (format: subject RELATION object):
{facts}

Use these facts when they are relevant. If the answer is not in the facts or the
conversation, say you don't know it rather than guessing."""


class Fact(BaseModel):
    subject: str
    relation: str
    object: str


class Extraction(BaseModel):
    facts: list[Fact] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)


# How many recent messages the extractor sees, so follow-ups like "he is two"
# can be tied back to the entity named earlier.
EXTRACT_CONTEXT_MESSAGES = 6


class State(MessagesState):
    entities: list[str]
    facts: list[str]


def default_llm() -> ChatOpenAI:
    """Use OpenRouter when OPENROUTER_API_KEY is set, otherwise OpenAI."""
    if key := os.getenv("OPENROUTER_API_KEY"):
        return ChatOpenAI(
            model=os.getenv("LLM_MODEL", "openai/gpt-4o-mini"),
            api_key=key,
            base_url="https://openrouter.ai/api/v1",
            temperature=0,
        )
    return ChatOpenAI(model=os.getenv("LLM_MODEL", "gpt-4o-mini"), temperature=0)


def build_chatbot(llm=None, store: GraphStore | None = None):
    llm = llm or default_llm()
    store = store or GraphStore()
    extractor = llm.with_structured_output(Extraction)

    def extract(state: State):
        recent = state["messages"][-EXTRACT_CONTEXT_MESSAGES:]
        result = extractor.invoke([SystemMessage(EXTRACT_PROMPT), *recent])
        for f in result.facts:
            store.add_fact(f.subject, f.relation, f.object)
        return {"entities": result.entities}

    def retrieve(state: State):
        return {
            "facts": store.facts_about(state.get("entities", []), fallback=["user"])
        }

    def respond(state: State):
        facts = "\n".join(state.get("facts", [])) or "(none)"
        system = SystemMessage(ANSWER_PROMPT.format(facts=facts))
        return {"messages": [llm.invoke([system, *state["messages"]])]}

    builder = StateGraph(State)
    builder.add_node("extract", extract)
    builder.add_node("retrieve", retrieve)
    builder.add_node("respond", respond)
    builder.add_edge(START, "extract")
    builder.add_edge("extract", "retrieve")
    builder.add_edge("retrieve", "respond")
    builder.add_edge("respond", END)

    # InMemorySaver keeps the message history for the current process only.
    # The facts in FalkorDB persist across restarts.
    return builder.compile(checkpointer=InMemorySaver()), store