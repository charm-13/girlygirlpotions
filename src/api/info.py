from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth

router = APIRouter(
    prefix="/info",
    tags=["info"],
    dependencies=[Depends(auth.get_api_key)],
)

class Timestamp(BaseModel):
    day: str
    hour: int

@router.post("/current_time")
def post_time(timestamp: Timestamp):
    """
    Share current time.
    """
    day = timestamp.day
    hour = timestamp.hour
    print(f"it's currently {hour} o'clock on {day}")
    return "OK"

@router.get("/current_time")
def get_current_time():
    """
    Get the current time.
    """
    return {"day": "Edgeday", "hour": 0}

