import math
import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)

class Barrel(BaseModel):
    sku: str

    ml_per_barrel: int
    potion_type: list[int]
    price: int

    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_barrels(barrels_delivered: list[Barrel], order_id: int):
    """ """
    red_ml = 0
    green_ml = 0
    blue_ml = 0
    dark_ml = 0
    gold_paid = 0
    
    for barrel in barrels_delivered:
        if barrel.potion_type == [1, 0, 0, 0]: # red potion
            red_ml += barrel.ml_per_barrel*barrel.quantity
            gold_paid += barrel.price*barrel.quantity
            
        if barrel.potion_type == [0, 1, 0, 0]: # green potion
            green_ml += barrel.ml_per_barrel*barrel.quantity
            gold_paid += barrel.price*barrel.quantity
            
        if barrel.potion_type == [0, 0, 1, 0]: # blue potion
            blue_ml += barrel.ml_per_barrel*barrel.quantity
            gold_paid += barrel.price*barrel.quantity
            
        if barrel.potion_type == [0, 0, 0, 1]: # dark potion
            dark_ml += barrel.ml_per_barrel*barrel.quantity
            gold_paid += barrel.price*barrel.quantity
        
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text("UPDATE global_inventory \
                                            SET num_red_ml = num_red_ml + :red_ml, \
                                                num_green_ml = num_green_ml + :green_ml, \
                                                num_blue_ml = num_blue_ml + :blue_ml, \
                                                num_dark_ml = num_dark_ml + :dark_ml, \
                                                gold = gold - :gold_paid"),
                            {"red_ml": red_ml, "green_ml": green_ml, "blue_ml": blue_ml, "dark_ml": dark_ml, "gold_paid": gold_paid})

    print(f"barrels delievered: {barrels_delivered} order_id: {order_id}")
    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ 
    Develops a purchase plan to maximize profits and minimize spending 
    """   
    sorted_catalog = {
        "red": sorted(
            [barrel for barrel in wholesale_catalog if barrel.potion_type == [1, 0, 0, 0]],
            key=lambda x: x.price / x.ml_per_barrel
        ),
        "green": sorted(
            [barrel for barrel in wholesale_catalog if barrel.potion_type == [0, 1, 0, 0]],
            key=lambda x: x.price / x.ml_per_barrel
        ),
        "blue": sorted(
            [barrel for barrel in wholesale_catalog if barrel.potion_type == [0, 0, 1, 0]],
            key=lambda x: x.price / x.ml_per_barrel
        ),
        "dark": sorted(
            [barrel for barrel in wholesale_catalog if barrel.potion_type == [0, 0, 0, 1]],
            key=lambda x: x.price / x.ml_per_barrel
        ),
    }

    print(f"Sorted catalog based on cost-effectiveness: {sorted_catalog}")
        
    # Logic: Buy a barrel for each type that has less than 1/4 of the ml capcity
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT gold, num_red_ml, num_green_ml, num_blue_ml, num_dark_ml, ml_capacity \
                                                        FROM global_inventory")).mappings()
        inventory = result.fetchone()
        
        gold = inventory["gold"]
        total_red = inventory["num_red_ml"]
        total_green = inventory["num_green_ml"]
        total_blue = inventory["num_blue_ml"]
        total_dark = inventory["num_dark_ml"]
        total_ml_capacity = inventory["ml_capacity"]
    
    # Determine need
    max_ml_per_type = total_ml_capacity / 4
    ml_needed = {"red": 0, "green": 0, "blue": 0, "dark": 0}  # red, green, blue, dark
    
    ml_needed["red"] = max_ml_per_type - total_red
    ml_needed["green"] = max_ml_per_type - total_green
    ml_needed["blue"] = max_ml_per_type - total_blue
    ml_needed["dark"] = max_ml_per_type - total_dark
        
    priority = dict(sorted(ml_needed.items(), key=lambda x:x[1], reverse=True))
    print(f"Sorted ml required based on need: {priority}")
    
    # Calculate budget
    def budget_calculations(gold: int) -> int:
        if gold <= 200:
            return gold
        
        gold_adjusted = gold / 100
        budget = (100*math.log(gold_adjusted, 2)) + 100
        return budget
             
    budget = round(budget_calculations(gold))
    
    # Develop the plan
    plan = []
    total_current_ml = total_red + total_green + total_blue + total_dark
    max_ml_to_buy = total_ml_capacity - total_current_ml
    print(f"gold: {gold}, budget: {budget}, current ml in inventory: {total_current_ml}, max ml to buy: {max_ml_to_buy}")
    
    for type, ml_need in priority.items():
        if max_ml_to_buy <= 0:
            break   # if max ml capacity is reached, cannot buy anymore ml
        
        if ml_need <= 0:
            continue # shouldn't buy this specific potion if there's no need
          
        for barrel in sorted_catalog[type]:
            if barrel.quantity <= 0 or barrel.ml_per_barrel > max_ml_to_buy:
                continue
            
            if gold < 500 and barrel.price > 150:
                continue
            
            max_afford = budget // barrel.price
            if max_afford <= 0:
                continue
            
            max_purchase = 1
            barrels_needed = (ml_need + barrel.ml_per_barrel - 1) // barrel.ml_per_barrel
            purchase_amt = min(max_purchase, barrels_needed)
            if purchase_amt > 0:
                plan.append({"sku": barrel.sku, "quantity": purchase_amt})
                budget -= barrel.price*purchase_amt
                max_ml_to_buy -= barrel.ml_per_barrel
                break
        
    print(f"Wholesale purchase plan: {plan}")
    return plan

