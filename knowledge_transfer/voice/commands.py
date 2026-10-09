"""Spoken commands. Only short utterances are checked, so a real answer that happens to
contain the word "skip" is never mistaken for one."""
import re

COMMANDS = {
    "skip": {"skip", "skip it", "skip this", "skip this one", "next", "next question", "pass"},
    "repeat": {"repeat", "repeat that", "say that again", "say it again", "come again",
               "repeat the question", "what was the question", "sorry what"},
    "wait": {"wait", "hold on", "one second", "one moment", "give me a second", "just a second",
             "let me think"},
    "stop": {"stop", "stop the interview", "that's enough", "that is enough", "i'm done",
             "i am done", "end the interview", "let's stop", "we're done"},
}
_LOOKUP = {phrase: name for name, phrases in COMMANDS.items() for phrase in phrases}


def parse_command(text: str) -> str | None:
    words = re.sub(r"[^a-z' ]", " ", text.lower()).split()
    if not words or len(words) > 5:
        return None
    return _LOOKUP.get(" ".join(words))
