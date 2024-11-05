import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth

router = APIRouter(
    prefix="/info",
    tags=["info"],
)

class Timestamp(BaseModel):
    day: str
    hour: int

@router.post("/current_time", dependencies=[Depends(auth.get_api_key)])
def post_time(timestamp: Timestamp):
    """
    Share current time.
    """
    day = timestamp.day
    hour = timestamp.hour
    
    with db.engine.begin() as connection:
        connection.execute(
            sqlalchemy.text("""INSERT INTO time (day, hour)
                                SELECT :day, :hour"""),
            {"day": day, "hour": hour}
        )
        
    print(f"it's currently {hour} o'clock on {day}")
    return "OK"

@router.get("/current_time")
def get_current_time():
    """
    Get the current time.
    """
    with db.engine.begin() as connection:
        time = connection.execute(
            sqlalchemy.text("""SELECT day, hour
                                FROM time
                                ORDER BY id DESC LIMIT 1""")
        ).mappings().fetchone()
        
        day = time["day"]
        hour = time["hour"]
        
    return {"day": day, "hour": hour}

