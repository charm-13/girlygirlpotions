import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import math

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.get("/audit")
def get_inventory():
    """ """
    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text("SELECT num_potions, num_red_ml, num_green_ml, num_blue_ml, num_dark_ml, gold \
                            FROM global_inventory")
        ).mappings()
        inv = result.fetchone()
        num_potions = inv["num_potions"]
        total_ml = inv["num_red_ml"]+inv["num_green_ml"]+inv["num_blue_ml"]+inv["num_dark_ml"]
        gold = inv["gold"]
        
    print(f"Inventory -- num potions: {num_potions}, ml in barrels: {total_ml}, gold: {gold}")
    return {"number_of_potions": num_potions, "ml_in_barrels": total_ml, "gold": gold}

# Gets called once a day
@router.post("/plan")
def get_capacity_plan():
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """

    return {
        "potion_capacity": 0,
        "ml_capacity": 0
        }

class CapacityPurchase(BaseModel):
    potion_capacity: int
    ml_capacity: int

# Gets called once a day
@router.post("/deliver/{order_id}")
def deliver_capacity_plan(capacity_purchase : CapacityPurchase, order_id: int):
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """

    return "OK"
