import uuid

from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter
from googleapiclient.errors import HttpError

from src.agents.query_handler_agent import QueryHandlerAgent
from src.api.dependencies.agent import get_agent
from src.api.dependencies.calendar import get_calendar_service
from src.api.dependencies.diabetes_clf import get_diabetes_service
from src.api.dependencies.drug import get_drug_search_service
from src.models.appointment import BookAppointmentInput
from src.models.chat_request import ChatRequest
from src.models.classify_diabetes import ClassifyDiabetesInput
from src.services.calendar.calendar_service import CalendarService
from src.services.ml.classify_diabetes import ClassifyDiabetesService
from src.services.search.drug_search_service import DrugSearchService

router = APIRouter()


def get_or_create_user_id(request: Request):
    if "user_id" not in request.session:
        request.session["user_id"] = str(uuid.uuid4())
    return request.session["user_id"]


@router.post(
    "/chat",
    summary="Chat with the AI assistant",
    description="Ask medical questions, make appointments or classify diabetes risk",
)
def chat(
    msg: ChatRequest,
    user_id: str = Depends(get_or_create_user_id),
    agent: QueryHandlerAgent = Depends(get_agent),
):
    try:
        response = agent.run(msg.message, user_id)
        return JSONResponse(status_code=200, content=response)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid input")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/predict_diabetes",
    summary="Predict diabetes risk",
    description="Uses a trained ML model to estimate whether a patient is likely to have diabetes.",
)
def predict_diabetes(
    data: ClassifyDiabetesInput,
    service: ClassifyDiabetesService = Depends(get_diabetes_service),
):
    try:
        result = service.classify_diabetes(data)
        return JSONResponse(status_code=200, content=result)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid input. Make sure to include all necessary values.",
        )


@router.get(
    "/list_available_slots",
    summary="Available time slots",
    description="List all the available appointments for the next 5 days excluding the holidays",
)
def list_available_slots(service: CalendarService = Depends(get_calendar_service)):
    try:
        result = service.list_available_slots()
        return JSONResponse(status_code=200, content=result)
    except HttpError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Google Calendar API error: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error listing slots: {str(e)}",
        )


@router.get(
    "/drug_info",
    summary="Find information about drugs",
    description="Find the side effects and use cases by giving the drug name only",
)
def drug_info(
    drug_name: str, service: DrugSearchService = Depends(get_drug_search_service)
):
    try:
        result = service.get_drug_info(drug_name)
        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/me")
def get_current_user(request: Request):
    """Return the current session user_id (creates one if missing)."""
    user_id = get_or_create_user_id(request)
    return JSONResponse(status_code=200, content={"user_id": user_id})


@router.post("/book_appointment")
def book_appointment(
    data: BookAppointmentInput, service: CalendarService = Depends(get_calendar_service)
):
    try:
        result = service.book_appointment(data)
        return JSONResponse(status_code=200, content=result)
    except HttpError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Google Calendar API error: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error listing slots: {str(e)}",
        )


@router.post("/cancel_appointment")
def cancel_appointment(
    data: dict, service: CalendarService = Depends(get_calendar_service)
):
    event_id = data.get("event_id")
    if not event_id:
        raise HTTPException(status_code=400, detail="event_id is required")
    result = service.cancel_appointment(event_id)
    return JSONResponse(status_code=200, content=result)


# @router.get("/")
# def root():
#     """Root endpoint - redirect to docs"""
#     return JSONResponse(
#         status_code=200,
#         content={"message": "Clinic AI API", "docs": "/docs", "health": "/health"},
#     )


# TODO
# add retry mechanism
# use prometheus
