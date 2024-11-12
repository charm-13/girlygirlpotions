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
            sqlalchemy.text("""
                            WITH time AS (
                                SELECT day 
                                FROM time
                                ORDER BY id DESC LIMIT 1
                            ),
                            avg_sold_today AS (
                                SELECT sku, avg_sold
                                FROM demand_view
                                JOIN time ON demand_view.day = time.day
                            )
                            SELECT 
                                recipe_book.sku, recipe_book.name, 
                                SUM(potion_inventory.quantity) as quant, recipe_book.price, 
                                recipe_book.red_amt, recipe_book.green_amt, 
                                recipe_book.blue_amt, recipe_book.dark_amt 
                            FROM recipe_book
                            JOIN potion_inventory ON potion_inventory.sku = recipe_book.sku
                            LEFT JOIN avg_sold_today ON avg_sold_today.sku = recipe_book.sku
                            GROUP BY 
                                recipe_book.sku, recipe_book.name, 
                                recipe_book.price, avg_sold_today.avg_sold,
                                recipe_book.red_amt, recipe_book.green_amt, 
                                recipe_book.blue_amt, recipe_book.dark_amt
                            HAVING SUM(potion_inventory.quantity) > 0
                            ORDER BY 
                                COALESCE(avg_sold_today.avg_sold, 0) desc,
                                SUM(potion_inventory.quantity) desc
                            LIMIT 6
                            """)
        ).mappings()
        
    catalog = []
    
    
    for potion in inv_result:
        potion_type = [potion["red_amt"], potion["green_amt"], potion["blue_amt"], potion["dark_amt"]]
    
        catalog.append(
            {
                "sku": potion["sku"],
                "name": potion["name"],
                "quantity": potion["quant"],
                "price": potion["price"],
                "potion_type": potion_type
            }
        )
        
    print("Catalog: \n" + "\n".join(f"{item}" for item in catalog))        
    return catalog
