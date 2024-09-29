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
        result = connection.execute(sqlalchemy.text("SELECT num_green_potions FROM global_inventory"))

    return [
            {
                "sku": "GREEN_POTION_0",
                "name": "green potion",
                "quantity": result,
                "price": 50,
                "potion_type": [0, 1, 0, 0],
            }
        ]
