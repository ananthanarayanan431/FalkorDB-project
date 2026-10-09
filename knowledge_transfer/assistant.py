"""The LLM-backed pieces. The graph decides *what* to ask and *what* to hand over;
the LLM only extracts structure from free text and phrases things.

Without an LLM, or when a call fails, question writing and plan summaries fall
back to templates, so the interview and handover still work. Free-text
extraction needs an LLM and raises LLMUnavailable otherwise.
"""
import logging
import os

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from knowledge_transfer.errors import LLMUnavailable
from knowledge_transfer.gaps import Gap
from knowledge_transfer.models import AnswerAnalysis, Extraction

log = logging.getLogger(__name__)

BRAINDUMP_PROMPT = """You build a knowledge graph from an employee who is leaving the company.
From their free-text description list the systems, decisions and topics they worked on.
kind: system (software/infrastructure), decision (a choice made, e.g. a magic number or
schedule), topic (process or know-how). Set owned=true only if they say they own it.
depends_on: things it technically relies on. prerequisites: things a newcomer must
understand first. Use short names. Do not invent anything the text does not say."""

ANSWER_PROMPT = """A departing employee answered an exit-interview question about "{item}".
Question: {question}
Classify the answer (rationale = why it was built this way, trap = a known pitfall,
procedure = steps to follow, contact = who to ask, other). List any new systems,
decisions or topics the answer mentions that deserve their own questions. If the answer
is vague or incomplete, give ONE specific follow_up question, otherwise leave it null."""

QUESTION_PROMPT = """You are running an exit interview so a departing engineer's undocumented
knowledge is not lost. Write ONE specific question about "{item}" ({kind}).
Facts from the company graph: {facts}.
Ask for the reasoning, history or hidden traps, not a description of what it does.
Mention a concrete fact from the graph so the person sees you did your homework.
Return only the question."""

SUMMARY_PROMPT = """Write a 2-3 sentence welcome summary of this handover plan for {name}
({seniority}). {style} Plan steps in order: {steps}. Return only the summary."""


def default_llm():
    """None when no API key is configured."""
    if not (os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")):
        return None
    from sample.chatbot import default_llm as make_llm

    return make_llm()


class Assistant:
    def __init__(self, llm=None):
        self.llm = llm

    @property
    def has_llm(self) -> bool:
        return self.llm is not None

    def _structured(self, schema: type[BaseModel], system: str, human: str):
        if not self.llm:
            raise LLMUnavailable("No LLM configured (set OPENROUTER_API_KEY or OPENAI_API_KEY)")
        try:
            return self.llm.with_structured_output(schema).invoke(
                [SystemMessage(system), HumanMessage(human)]
            )
        except Exception as e:  # provider/network errors vary by backend
            raise LLMUnavailable(f"LLM call failed: {e}") from e

    def _text(self, prompt: str) -> str | None:
        """LLM free text, or None when there is no LLM or the call fails (callers fall back)."""
        if not self.llm:
            return None
        try:
            return str(self.llm.invoke([HumanMessage(prompt)]).content).strip() or None
        except Exception:
            log.warning("LLM call failed; using template fallback", exc_info=True)
            return None

    def extract_braindump(self, text: str) -> Extraction:
        return self._structured(Extraction, BRAINDUMP_PROMPT, text)

    def analyse_answer(self, item: str, question: str, answer: str) -> AnswerAnalysis:
        if not self.llm:
            return AnswerAnalysis()
        try:
            return self._structured(
                AnswerAnalysis, ANSWER_PROMPT.format(item=item, question=question), answer
            )
        except LLMUnavailable:
            # The answer itself is still stored; only the classification is lost.
            log.warning("answer analysis failed; storing answer unclassified", exc_info=True)
            return AnswerAnalysis()

    def write_question(self, gap: Gap, related: dict) -> str:
        facts = _facts(gap, related)
        prompt = QUESTION_PROMPT.format(item=gap.name, kind=gap.kind, facts="; ".join(facts))
        return self._text(prompt) or template_question(gap, related)

    def summarise_plan(self, name: str, seniority: str, style: str, steps: list[str]) -> str:
        prompt = SUMMARY_PROMPT.format(name=name, seniority=seniority, style=style, steps=", ".join(steps))
        return self._text(prompt) or f"{len(steps)} steps for {name}. {style}"


def _facts(gap: Gap, related: dict) -> list[str]:
    facts = list(gap.reasons)
    if gap.description:
        facts.append(gap.description)
    if related.get("used_by"):
        facts.append("used by " + ", ".join(related["used_by"]))
    if related.get("depends_on"):
        facts.append("relies on " + ", ".join(related["depends_on"]))
    return facts


def template_question(gap: Gap, related: dict) -> str:
    lead = []
    if gap.sole_owner:
        lead.append("you are the only person who has worked on it")
    if gap.undocumented:
        lead.append("it has no documentation")
    if related.get("used_by"):
        lead.append("it is used by " + ", ".join(related["used_by"][:3]))
    prefix = f"On \"{gap.name}\": " + "; ".join(lead) + ". " if lead else f"On \"{gap.name}\": "
    if gap.kind == "decision":
        return prefix + "Why was it decided this way, what alternatives did you reject, and what breaks if someone changes it?"
    return prefix + "What would someone taking over most need to know, and what are the traps that are not written down?"
