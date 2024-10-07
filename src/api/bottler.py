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
    total_potions = 0
    red_potions = 0
    green_potions = 0
    blue_potions = 0
    dark_potions = 0
    red_ml_used = 0
    green_ml_used = 0
    blue_ml_used = 0
    dark_ml_used = 0
    
    ml_per_potion = 100
    
    for potion in potions_delivered:
        total_potions += potion.quantity
        
        if potion.potion_type == [100, 0, 0, 0]: # red potion
            red_potions += potion.quantity
            red_ml_used += ml_per_potion*potion.quantity
            
        if potion.potion_type == [0, 100, 0, 0]: # green potion
            green_potions += potion.quantity
            green_ml_used += ml_per_potion*potion.quantity
            
        if potion.potion_type == [0, 0, 100, 0]: # blue potion
            blue_potions += potion.quantity
            blue_ml_used += ml_per_potion*potion.quantity
            
        if potion.potion_type == [0, 0, 100, 0]: # dark potion
            dark_potions += potion.quantity
            dark_ml_used += ml_per_potion*potion.quantity
            
    
    with db.engine.begin() as connection:
        # assume there is a row for each potion type
        connection.execute(
            sqlalchemy.text("UPDATE potion_inventory \
                            SET quantity = \
                                CASE \
                                WHEN sku = 'RED_POTION' THEN quantity + :red_potions \
                                WHEN sku = 'GREEN_POTION' THEN quantity + :green_potions \
                                WHEN sku = 'BLUE_POTION' THEN quantity + :blue_potions \
                                WHEN sku = 'DARK_POTION' THEN quantity + :dark_potions \
                                END"),
                            {"red_potions": red_potions, 
                            "green_potions": green_potions, 
                            "blue_potions": blue_potions, 
                            "dark_potions": dark_potions})
        connection.execute(
            sqlalchemy.text("UPDATE global_inventory \
                            SET num_potions = num_potions + :total_potions, \
                                num_red_ml = num_red_ml - :red_ml_used, \
                                num_green_ml = num_green_ml - :green_ml_used, \
                                num_blue_ml = num_blue_ml - :blue_ml_used, \
                                num_dark_ml = num_dark_ml - :dark_ml_used"),
                           {"total_potions": total_potions, 
                            "red_ml_used": red_ml_used, 
                            "green_ml_used": green_ml_used, 
                            "blue_ml_used": blue_ml_used, 
                            "dark_ml_used": dark_ml_used})
        
    print(f"potions delievered: {potions_delivered} order_id: {order_id}")

    return "OK"

@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """
    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text("SELECT num_red_ml, num_green_ml, num_blue_ml, num_dark_ml FROM global_inventory")
            ).mappings()
        inventory = result.fetchone()
        num_red_ml = inventory["num_red_ml"]
        num_green_ml = inventory["num_green_ml"]
        num_blue_ml = inventory["num_blue_ml"]
        num_dark_ml = inventory["num_dark_ml"]
        
    plan = []
    ml_per_potion = 100
    
    red_potions_to_bottle = num_red_ml // ml_per_potion
    if red_potions_to_bottle > 0:
        plan.append(
            {
                "potion_type": [100, 0, 0, 0],
                "quantity": red_potions_to_bottle,
            }
        )
        
    green_potions_to_bottle = num_green_ml // ml_per_potion
    if green_potions_to_bottle > 0:
        plan.append(
            {
                "potion_type": [0, 100, 0, 0],
                "quantity": green_potions_to_bottle,
            }
        )
    
    blue_potions_to_bottle = num_blue_ml // ml_per_potion
    if blue_potions_to_bottle > 0:
        plan.append(
            {
                "potion_type": [0, 0, 100, 0],
                "quantity": blue_potions_to_bottle,
            }
        )
    
    dark_potions_to_bottle = num_dark_ml // ml_per_potion
    if dark_potions_to_bottle > 0:
        plan.append(
            {
                "potion_type": [0, 0, 0, 100],
                "quantity": dark_potions_to_bottle,
            }
        )

    return plan

if __name__ == "__main__":
    print(get_bottle_plan())