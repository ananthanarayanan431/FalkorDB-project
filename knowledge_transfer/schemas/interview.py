"""Interview session state. Plain data so both the service and the stores can use it."""
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Question:
    item_id: str
    item_name: str
    text: str
    reasons: list[str]
    risk: int
    is_follow_up: bool = False

    def to_dict(self):
        return self.__dict__.copy()


@dataclass
class Session:
    id: str
    leaver: str
    current: Question | None = None
    follow_ups: list[Question] = field(default_factory=list)
    skipped: set[str] = field(default_factory=set)
    turns: int = 0
    version: int = 0
    # Epoch seconds when a request claimed this session to write an answer to the graph.
    busy_since: float | None = None

    @property
    def status(self) -> str:
        return "active" if self.current else "completed"

    def to_state(self) -> dict[str, Any]:
        d = asdict(self)
        d["skipped"] = sorted(self.skipped)
        del d["id"], d["version"]
        return d

    @classmethod
    def from_state(cls, id: str, d: dict[str, Any], version: int) -> "Session":
        current = Question(**d["current"]) if d["current"] else None
        return cls(id, d["leaver"], current, [Question(**q) for q in d["follow_ups"]],
                   set(d["skipped"]), d["turns"], version, d.get("busy_since"))
