from fastapi import APIRouter
from src.models import APIOutput

router = APIRouter()


@router.get("/health")
def health():
    return APIOutput.success(status_code=200, message="service is working fine")
