from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.services.llm_client import get_llm_status

router = APIRouter(prefix="/ai")


@router.get("/status")
def ai_status(_user=Depends(get_current_user)):
    return get_llm_status()

