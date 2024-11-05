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
    print(f"order {order_id} attempting to deliver: {barrels_delivered}")
    
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
        connection.execute(sqlalchemy.text("""INSERT INTO barrel_inventory (num_red_ml, num_green_ml, num_blue_ml, num_dark_ml)
                                            VALUES (:red_ml, :green_ml, :blue_ml, :dark_ml)"""),
                            {"red_ml": red_ml, "green_ml": green_ml, "blue_ml": blue_ml, "dark_ml": dark_ml})
        connection.execute(sqlalchemy.text("""INSERT INTO treasury_log (gold)
                                            VALUES (-:gold_paid)"""),
                            {"gold_paid": gold_paid})

    print(f"order {order_id} successful! \ndelivered: {barrels_delivered}")
    return "OK"

def serious_budget_calculations(gold: int) -> int:
    """
    Calculate barrel budget based on current gold.
    """
    budget = gold
    
    if gold > 500:
        gold_adjusted = (gold - 300) / 100
        budget = (200*math.log(gold_adjusted, 2)) + 300
    
    return budget

def potion_value(need):
    """
    Assigns weights to each potion type (red, green, blue, dark)
    based on the day and need.
    """
    return need

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
        
    with db.engine.begin() as connection:
        inventory = connection.execute(
            sqlalchemy.text("""
                SELECT
                    SUM(num_red_ml) as num_red_ml, 
                    SUM(num_green_ml) as num_green_ml, 
                    SUM(num_blue_ml) as num_blue_ml, 
                    SUM(num_dark_ml) as num_dark_ml,
                    SUM(num_red_ml+num_green_ml+num_blue_ml+num_dark_ml) AS total_ml,
                    (SELECT SUM(gold) FROM treasury_log) as gold,
                    (SELECT SUM(ml_capacity) FROM shop_capacity) as ml_capacity
                FROM barrel_inventory""")
            ).mappings().fetchone()
        
        gold = inventory["gold"]
        total_red = inventory["num_red_ml"]
        total_green = inventory["num_green_ml"]
        total_blue = inventory["num_blue_ml"]
        total_dark = inventory["num_dark_ml"]
        total_ml_capacity = inventory["ml_capacity"]
        total_current_ml = inventory["total_ml"]
    
    # Determine need
    min_dark_ml = 0
    if total_ml_capacity >= 20000:
        min_dark_ml = 10000
        
    max_ml_to_buy = total_ml_capacity - total_current_ml
    max_ml_per_type = round((total_ml_capacity - min_dark_ml) / 3)
    
    ml_needed = {"red": 0, "green": 0, "blue": 0, "dark": 0}  # red, green, blue, dark
    
    ml_needed["red"] = max_ml_per_type - total_red
    ml_needed["green"] = max_ml_per_type - total_green
    ml_needed["blue"] = max_ml_per_type - total_blue
    ml_needed["dark"] = max_ml_to_buy - total_dark  # dark is always the priority
        
    priority = dict(sorted(ml_needed.items(), key=lambda x:x[1], reverse=True))
    print(f"Sorted ml required based on need: {priority}\n"
        f"Sorted catalog based on cost-effectiveness: {sorted_catalog}")
    
    # Calculate budget
    budget = round(serious_budget_calculations(gold))
    
    # Develop the plan
    plan = []
    print(f"gold: {gold}, budget: {budget}, current ml in inventory: {total_current_ml}, max ml to buy: {max_ml_to_buy}")
    
    for type, ml_need in priority.items():
        if max_ml_to_buy <= 0:
            break   # if max ml capacity is reached, cannot buy anymore ml
        
        if ml_need <= 0:
            continue # shouldn't buy this specific potion if there's no need    
          
        for barrel in sorted_catalog[type]:
            if barrel.quantity <= 0 or barrel.ml_per_barrel > max_ml_to_buy:
                continue
            
            # useful for when I have little gold, and a lot of need
            if budget < 500 and barrel.price > 150:
                continue
            
            max_afford = budget // barrel.price
            if max_afford <= 0 and (barrel.price - budget) > 50:
                if type != "dark" or barrel.price > gold:
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

