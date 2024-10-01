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
    green_ml = 0
    gold_paid = 0
    for barrel in barrels_delivered:
        if barrel.potion_type == [0, 1, 0, 0]: 
            green_ml += barrel.ml_per_barrel*barrel.quantity
            gold_paid += barrel.price*barrel.quantity
    if green_ml > 0:
        with db.engine.begin() as connection:
            connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_ml = num_green_ml + :green_ml, gold = gold - :gold_paid"),
                               {"green_ml": green_ml, "gold_paid": gold_paid})

    print(f"barrels delievered: {barrels_delivered} order_id: {order_id}")

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)
    
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_green_potions, gold FROM global_inventory")).mappings()
        inventory = result.fetchone()
        num_green_potions = inventory["num_green_potions"]
        gold = inventory["gold"]
        
    plan = []
    
    if num_green_potions < 10:
        smallest = None
        
        for barrel in wholesale_catalog:
            if barrel.potion_type == [0, 1, 0, 0]:
                if not smallest or barrel.ml_per_barrel < smallest.ml_per_barrel:
                    smallest = barrel               
        
        if smallest and smallest.price <= gold:
            plan.append({"sku": smallest.sku, "quantity": 1})
        
    print(f"Wholesale purchase plan: {plan}")
    return plan

