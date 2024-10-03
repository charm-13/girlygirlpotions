import sqlalchemy
from src import database as db
from fastapi import APIRouter

router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_potions FROM global_inventory")).mappings()
        inventory = result.fetchone()
        num_potions = inventory["num_potions"]
        
    catalog = []
    
    if num_potions > 0:
        catalog.append(
            {
                "sku": "GREEN_POTION_0",
                "name": "green potion",
                "quantity": int(num_potions),
                "price": 50,
                "potion_type": [0, 100, 0, 0],
            }
        )

    return catalog
