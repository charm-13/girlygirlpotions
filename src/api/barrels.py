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
            
        if barrel.potion_type == [0, 0, 1, 0]: # dark potion
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
        
    # Logic: Buy a barrel for each type that has less than 10 potions
    # Give priority to the type with the most need
    with db.engine.begin() as connection:
        gold_result = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).mappings()
        potion_result = connection.execute(
            sqlalchemy.text("SELECT quantity, potion_mixes.red_amt, potion_mixes.green_amt, potion_mixes.blue_amt, potion_mixes.dark_amt \
                            FROM potion_inventory \
                            JOIN potion_mixes ON potion_inventory.sku = potion_mixes.sku")
        ).mappings()
        print(potion_result)
        gold = gold_result.fetchone()["gold"]
    
    # Determine need 
    ml_per_potion = 100     # TO ASK PIERCE: does the ml per potion have to be 100? Can I change that amount?
    ml_needed = {"red": 0, "green": 0, "blue": 0, "dark": 0}  # red, green, blue, dark
        
    for potion in potion_result:
        num_potions_needed = max(10 - potion["quantity"], 0)
        
        ml_needed["red"] += potion["red_amt"]*num_potions_needed
        ml_needed["green"] += potion["green_amt"]*num_potions_needed
        ml_needed["blue"] += potion["blue_amt"]*num_potions_needed
        ml_needed["dark"] += potion["dark_amt"]*num_potions_needed
        
    priority = dict(sorted(ml_needed.items(), key=lambda x:x[1], reverse=True))
    print(f"Sorted ml required based on need: {priority}")
             
    # Develop the plan
    plan = []
    budget = gold
    
    for type, ml_need in ml_needed.items():
        if ml_need <= 0:
            continue
          
        for barrel in sorted_catalog[type]:
            if barrel.quantity <= 0:
                continue
            
            max_afford = budget // barrel.price
            if max_afford <= 0:
                continue
            
            max_purchase = min(max_afford, barrel.quantity)
            barrels_needed = (ml_need + barrel.ml_per_barrel - 1) // barrel.ml_per_barrel
            purchase_amt = min(max_purchase, barrels_needed)
            if purchase_amt <= 0:
                continue
            
            plan.append({"sku": barrel.sku, "quantity": purchase_amt})
            
            budget -= barrel.price*purchase_amt

        
    print(f"Wholesale purchase plan: {plan}")
    return plan

