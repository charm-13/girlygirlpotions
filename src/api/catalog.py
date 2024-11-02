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
            sqlalchemy.text("""SELECT recipe_book.sku, recipe_book.name, potion_inventory.quantity, recipe_book.price, 
                                recipe_book.red_amt, recipe_book.green_amt, recipe_book.blue_amt, recipe_book.dark_amt 
                            FROM recipe_book
                            JOIN potion_inventory ON potion_inventory.sku = recipe_book.sku
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
