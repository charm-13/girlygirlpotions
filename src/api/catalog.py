import sqlalchemy
from src import database as db
from fastapi import APIRouter

router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Provides all available potions.
    """
    with db.engine.begin() as connection:
        inv_result = connection.execute(
            sqlalchemy.text("SELECT sku, name, quantity, price FROM potion_inventory")
        ).mappings()
        mix_result = connection.execute(
            sqlalchemy.text("SELECT red_amt, green_amt, blue_amt, dark_amt FROM potion_mixes")
        ).mappings()
        
    catalog = []
    
    for potion in inv_result:
        mix = mix_result.fetchone()
        
        if potion["quantity"] > 0:
            catalog.append(
                {
                    "sku": potion["sku"],
                    "name": potion["name"],
                    "quantity": potion["quantity"],
                    "price": potion["price"],
                    "potion_type": [mix["red_amt"], mix["green_amt"], mix["blue_amt"], mix["dark_amt"]]
                }
            )
            
    return catalog
