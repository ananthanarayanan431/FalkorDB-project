from dotenv import load_dotenv

load_dotenv()

from sample.chatbot import build_chatbot  # noqa: E402


def main():
    chatbot, store = build_chatbot()
    config = {"configurable": {"thread_id": "cli"}}
    print("Chat started. Commands: /facts  /profile <entity>  /reset  /quit\n")

    while True:
        try:
            text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not text:
            continue
        if text == "/quit":
            break
        if text == "/facts":
            print("\n".join(store.all_facts()) or "(graph is empty)", "\n")
            continue
        command, *rest = text.split(maxsplit=1)
        if command == "/profile":
            print(store.profile_retrieval([rest[0] if rest else "user"]), "\n")
            continue
        if text == "/reset":
            store.reset()
            print("Graph cleared.\n")
            continue

        result = chatbot.invoke({"messages": [("user", text)]}, config)
        print(f"bot> {result['messages'][-1].content}\n")


if __name__ == "__main__":
    main()