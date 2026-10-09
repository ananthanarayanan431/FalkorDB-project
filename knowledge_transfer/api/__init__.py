"""FastAPI service. Run with: uv run uvicorn knowledge_transfer.api:app --reload"""
from knowledge_transfer.api.app import create_app
from knowledge_transfer.api.deps import Services

app = create_app()

__all__ = ["Services", "app", "create_app"]
