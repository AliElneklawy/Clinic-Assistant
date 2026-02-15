import uuid

from fastapi import Depends, Request, HTTPException
from fastapi.routing import APIRouter
from fastapi.responses import JSONResponse

from src.agents.query_handler_agent import QueryHandlerAgent
from src.models.classify_diabetes import ClassifyDiabetesInput
from src.models.chat_request import ChatRequest
from src.services.ml.classify_diabetes import ClassifyDiabetesService
from src.settings.paths import DIABETES_MODEL_PATH


router = APIRouter()

_agent_instance = None
_diabetes_service_instance = None

# agent = QueryHandlerAgent()
# diabetes_classifier_service = ClassifyDiabetesService(
#     model=joblib.load(DIABETES_MODEL_PATH)
# )

def get_agent():
    global _agent_instance # use the variable from the module’s global scope — not create a new local one

    if _agent_instance is None:
        _agent_instance = QueryHandlerAgent()

    return _agent_instance

def get_diabetes_service():
    global _diabetes_service_instance

    if _diabetes_service_instance is None:
        import joblib
        model=joblib.load(DIABETES_MODEL_PATH)
        _diabetes_service_instance = ClassifyDiabetesService(model=model)
    
    return _diabetes_service_instance

def get_or_creaet_user_id(request: Request):
    if 'user_id' not in request.session:
        request.session['user_id'] = str(uuid.uuid4())
    return request.session['user_id']   

@router.post(
    "/chat",
    summary="Chat with the AI assistant",
    description="Ask medical questions, make appointments or classify diabetes risk"
)
def chat(
    msg: ChatRequest, 
    user_id: str = Depends(get_or_creaet_user_id),
    agent: QueryHandlerAgent = Depends(get_agent)
    ):
    # if 'user_id' not in request.session:
    #     request.session['user_id'] = str(uuid.uuid4())
    # user_id = request.session['user_id']   

    try:
        response = agent.run(msg.message, user_id)
        return JSONResponse(status_code=200, content=response["output"])
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid input")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post(
    "/predict_diabetes",
    summary="Predict diabetes risk",
    description="Uses a trained ML model to estimate whether a patient is likely to have diabetes."
)
def predict_diabetes(
    data: ClassifyDiabetesInput,
    service: ClassifyDiabetesService = Depends(get_diabetes_service)
    ):
    try:
        result = service.classify_diabetes(data)
        return JSONResponse(status_code=200, content=result)
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail="Invalid input. Make sure to include all necessary values."
            )

@router.post("/book_appointment")
def book_appointment():
    pass

@router.get("/")
def root():
    """Root endpoint - redirect to docs"""
    return JSONResponse(
        status_code=200,
        content={
            "message": "Clinic AI API",
            "docs": "/docs",
            "health": "/health"
        }
    )
