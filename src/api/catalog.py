import sqlalchemy
from src import database as db
from fastapi import APIRouter

router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Provides all available potions.
    """
    #TODO: implement good logic for what to offer when
    with db.engine.begin() as connection:
        inv_result = connection.execute(
            sqlalchemy.text("""SELECT potion_inventory.sku, name, quantity, price, red_amt, 
                                    green_amt, blue_amt, dark_amt 
                            FROM potion_inventory
                            WHERE quantity > 0
                            ORDER BY quantity desc
                            LIMIT 6""")
        ).mappings()
        
    catalog = []
    
    
    for potion in inv_result:
        print(f"inv: {potion}")
        potion_type = [potion["red_amt"], potion["green_amt"], potion["blue_amt"], potion["dark_amt"]]
    
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
