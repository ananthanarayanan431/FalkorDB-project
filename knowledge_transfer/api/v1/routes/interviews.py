from fastapi import APIRouter, status

from knowledge_transfer.api.deps import ServicesDep, resolve_leaver
from knowledge_transfer.api.responses import ApiResponse, ok
from knowledge_transfer.api.schemas import AnswerIn, StartInterviewIn

router = APIRouter(prefix="/interviews", tags=["interviews"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def start_interview(body: StartInterviewIn, services: ServicesDep) -> ApiResponse[dict]:
    leaver = await resolve_leaver(services, body.leaver)
    session, q = await services.interviews.start(leaver)
    data = {"interview_id": session.id, "leaver": leaver, "question": q.to_dict() if q else None}
    return ok(data, "Interview started" if q else "Interview started; no open gaps to ask about")


@router.get("/{interview_id}")
async def get_interview(interview_id: str, services: ServicesDep) -> ApiResponse[dict]:
    session = await services.interviews.get(interview_id)
    data = {
        "interview_id": session.id,
        "leaver": session.leaver,
        "status": session.status,
        "turns": session.turns,
        "question": session.current.to_dict() if session.current else None,
        "transcript": await services.interviews.transcript(interview_id),
    }
    return ok(data, "Interview found")


@router.post("/{interview_id}/answer")
async def answer(interview_id: str, body: AnswerIn, services: ServicesDep) -> ApiResponse[dict]:
    return ok(await services.interviews.answer(interview_id, body.answer), "Answer recorded")


@router.post("/{interview_id}/skip")
async def skip(interview_id: str, services: ServicesDep) -> ApiResponse[dict]:
    return ok(await services.interviews.skip(interview_id), "Question skipped")
