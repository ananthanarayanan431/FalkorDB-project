from fastapi import APIRouter, status

from knowledge_transfer.api.deps import ServicesDep, resolve_leaver
from knowledge_transfer.api.errors import ConflictError, NotFoundError
from knowledge_transfer.api.responses import ApiResponse, ok
from knowledge_transfer.api.schemas import AnswerIn, StartInterviewIn

router = APIRouter(prefix="/interviews", tags=["interviews"])


@router.post("", status_code=status.HTTP_201_CREATED)
def start_interview(body: StartInterviewIn, services: ServicesDep) -> ApiResponse[dict]:
    leaver = resolve_leaver(services, body.leaver)
    try:
        session, q = services.interviews.start(leaver)
    except KeyError as e:
        raise NotFoundError(e.args[0]) from e
    data = {"interview_id": session.id, "leaver": leaver, "question": q.to_dict() if q else None}
    return ok(data, "Interview started" if q else "Interview started; no open gaps to ask about")


@router.post("/{interview_id}/answer")
def answer(interview_id: str, body: AnswerIn, services: ServicesDep) -> ApiResponse[dict]:
    try:
        result = services.interviews.answer(interview_id, body.answer)
    except KeyError as e:
        raise NotFoundError(e.args[0]) from e
    except ValueError as e:
        raise ConflictError(str(e)) from e
    return ok(result, "Answer recorded")


@router.post("/{interview_id}/skip")
def skip(interview_id: str, services: ServicesDep) -> ApiResponse[dict]:
    try:
        result = services.interviews.skip(interview_id)
    except KeyError as e:
        raise NotFoundError(e.args[0]) from e
    return ok(result, "Question skipped")
