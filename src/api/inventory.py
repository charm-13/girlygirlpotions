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
        inv = connection.execute(
            sqlalchemy.text("""
                SELECT 
                    SUM(num_red_ml) as num_red_ml, SUM(num_green_ml) as num_green_ml, 
                    SUM(num_blue_ml) as num_blue_ml, SUM(num_dark_ml) as num_dark_ml,
                    (SELECT SUM(gold) FROM treasury_log) as gold
                FROM barrel_inventory""")
        ).mappings().fetchone()
        pot_inv = connection.execute(
            sqlalchemy.text("""SELECT COALESCE(SUM(quantity), 0) as num_potions 
                            FROM potion_inventory""")
        ).mappings().fetchone()
        
        num_potions = pot_inv["num_potions"]
        red_ml = inv["num_red_ml"]
        green_ml = inv["num_green_ml"]
        blue_ml = inv["num_blue_ml"]
        dark_ml = inv["num_dark_ml"]
        total_ml = red_ml+green_ml+blue_ml+dark_ml
        gold = inv["gold"]
        
    print(f"Inventory -- num potions: {num_potions}, gold: {gold}, \n"
          f"\t ml in barrels: red = {red_ml}, green = {green_ml}, blue = {blue_ml}, dark = {dark_ml}, total = {total_ml}")
    return {"number_of_potions": num_potions, "ml_in_barrels": total_ml, "gold": gold}

# Gets called once a day
@router.post("/plan")
def get_capacity_plan():
    """ 
    Develops a capacity purchase plan.
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
    """ """

    return "OK"
