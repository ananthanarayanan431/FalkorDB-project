"""Domain errors raised by the services. The API maps each one to an HTTP status."""
from typing import Any


class KnowledgeTransferError(Exception):
    def __init__(self, message: str, details: Any = None):
        super().__init__(message)
        self.message = message
        self.details = details


class NotFound(KnowledgeTransferError):
    """A person, item or interview id does not exist."""


class InvalidInput(KnowledgeTransferError):
    """Input is well-formed but inconsistent with the graph, e.g. unknown references."""


class InvalidState(KnowledgeTransferError):
    """The operation is not allowed in the current state, e.g. answering a finished interview."""


class LLMUnavailable(KnowledgeTransferError):
    """No LLM is configured, or the call to it failed, and there is no fallback."""
