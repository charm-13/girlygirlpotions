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
    # adds total ml from order, and takes away what was spent
    cost = 0 
    green_ml = 0
    for barrel in barrels_delivered:
        cost += barrel.price
        green_ml += barrel.ml_per_barrel
    
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("UPDATE global_inventory SET gold -= cost SET num_green_ml += green_ml"))
    """ """
    print(f"barrels delievered: {barrels_delivered} order_id: {order_id}")

    return result

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_green_potions FROM global_inventory"))
        
    print(wholesale_catalog)

    quant = 0    
        
    if result < 10:
        quant += 1

    return [
        {
            "sku": "SMALL_GREEN_BARREL",
            "quantity": quant,
        }
    ]

