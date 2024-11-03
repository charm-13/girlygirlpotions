import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.post("/reset")
def reset():
    """
    Reset the game state. Gold goes to 100, all potions are removed from
    inventory, and all barrels are removed from inventory. Carts are all reset.
    """
    with db.engine.begin() as connection:
        connection.execute(
            sqlalchemy.text("DELETE FROM global_inventory"))
        connection.execute(
            sqlalchemy.text("""INSERT INTO global_inventory
                            (num_red_ml, num_green_ml, num_blue_ml, num_dark_ml,
                            gold, potion_capacity, ml_capacity)
                            VALUES (0, 0, 0, 0, 100, 50, 10000)"""))
        connection.execute(
            sqlalchemy.text("DELETE FROM potion_inventory"))
        connection.execute(
            sqlalchemy.text("DELETE FROM carts CASCADE"))
        connection.execute(
            sqlalchemy.text("DELETE FROM carts_items"))
        connection.execute(
            sqlalchemy.text("DELETE FROM time"))
        
    return "OK"

