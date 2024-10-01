import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_bottles(potions_delivered: list[PotionInventory], order_id: int):
    """ """
    potions = 0
    ml_used = 0
    for potion in potions_delivered:
        potions += potion.quantity
        ml_used += 100*potion.quantity
    
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_potions = num_green_potions + :potions, num_green_ml = num_green_ml - :ml_used"),
                           {"potions": potions, "ml_used": ml_used})
        
    print(f"potions delievered: {potions_delivered} order_id: {order_id}")

    return "OK"

@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """
    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.

    # Initial logic: bottle all barrels into green potions.
    
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_green_ml FROM global_inventory")).mappings()
        inventory = result.fetchone()
        num_green_ml = inventory["num_green_ml"]
        
    green_potions_to_bottle = int(num_green_ml // 100)
    plan = []
    
    if green_potions_to_bottle > 0:
        plan.append(
            {
                "potion_type": [0, 100, 0, 0],
                "quantity": green_potions_to_bottle,
            }
        )

    return plan

if __name__ == "__main__":
    print(get_bottle_plan())