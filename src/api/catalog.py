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
            sqlalchemy.text("SELECT potion_inventory.sku, name, quantity, price, potion_mixes.red_amt, \
                                    potion_mixes.green_amt, potion_mixes.blue_amt, potion_mixes.dark_amt \
                            FROM potion_inventory \
                            JOIN potion_mixes ON potion_inventory.sku = potion_mixes.sku")
        ).mappings()
        
    catalog = []
    
    for potion in inv_result:
        potion_type = [potion["red_amt"], potion["green_amt"], potion["blue_amt"], potion["dark_amt"]]
        
        if potion["quantity"] > 0:
            catalog.append(
                {
                    "sku": potion["sku"],
                    "name": potion["name"],
                    "quantity": potion["quantity"],
                    "price": potion["price"],
                    "potion_type": potion_type
                }
            )
            
    print(f"Catalog: {catalog}")
            
    return catalog
