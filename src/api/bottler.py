import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_bottles(potions_delivered: list[PotionInventory], order_id: int):
    """ """
    red_ml_used = 0
    green_ml_used = 0
    blue_ml_used = 0
    dark_ml_used = 0
    
    quantities = []
    mixes = []
    
    with db.engine.begin() as connection:

        for potion in potions_delivered:
            red_ml = potion.potion_type[0]
            green_ml = potion.potion_type[1]
            blue_ml = potion.potion_type[2]
            dark_ml = potion.potion_type[3]
            
            quantity = potion.quantity
            
            red_ml_used += red_ml*quantity
            green_ml_used += green_ml*quantity
            blue_ml_used += blue_ml*quantity
            dark_ml_used += dark_ml*quantity
            
            mix = {"red_amt": red_ml, "green_amt": green_ml, "blue_amt": blue_ml, "dark_amt": dark_ml}
            
            sku = connection.execute(
                sqlalchemy.text("""SELECT sku
                                FROM recipe_book
                                WHERE red_amt = :red_amt
                                    AND green_amt = :green_amt
                                    AND blue_amt = :blue_amt
                                    AND dark_amt = :dark_amt"""),
                mix).mappings().fetchone()["sku"]
            
            quantities.append({"sku": sku, "quantity": quantity}) 
            mixes.append(mix)
        
        connection.execute(
            sqlalchemy.text("""INSERT INTO potion_inventory (sku, quantity)
                            VALUES (:sku, :quantity)"""),
                            quantities) 
        connection.execute(
            sqlalchemy.text("""INSERT INTO barrel_inventory (num_red_ml, num_green_ml, num_blue_ml, num_dark_ml)
                            VALUES (-:red_ml_used, -:green_ml_used, -:blue_ml_used, -:dark_ml_used)"""),
                           {"red_ml_used": red_ml_used, "green_ml_used": green_ml_used, 
                            "blue_ml_used": blue_ml_used, "dark_ml_used": dark_ml_used})
        
    print(f"potions delievered: {potions_delivered}, order_id: {order_id}")
    return "OK"

@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """
    plan = []
    ml_per_potion = 100
    
    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text("""
                SELECT 
                    SUM(num_red_ml) as num_red_ml, 
                    SUM(num_green_ml) as num_green_ml, 
                    SUM(num_blue_ml) as num_blue_ml, 
                    SUM(num_dark_ml) as num_dark_ml,
                    (SELECT SUM(potion_capacity) FROM shop_capacity) as potion_capacity
                FROM barrel_inventory""")
            ).mappings()
        pot_result = connection.execute(
            sqlalchemy.text("""SELECT 
                                recipe_book.sku, recipe_book.red_amt, recipe_book.green_amt,
                                recipe_book.blue_amt, recipe_book.dark_amt, COALESCE(SUM(quantity),0) as quantity
                            FROM recipe_book
                            LEFT JOIN potion_inventory on potion_inventory.sku = recipe_book.sku
                            GROUP BY recipe_book.sku, recipe_book.red_amt, recipe_book.green_amt, 
                                recipe_book.blue_amt, recipe_book.dark_amt, recipe_book.demand
                            ORDER BY recipe_book.demand desc, COALESCE(SUM(quantity),0)""")
            ).mappings().fetchall()
        num_potions_result = connection.execute(
            sqlalchemy.text("SELECT COALESCE(SUM(quantity),0) as num_potions \
                            FROM potion_inventory")
            ).mappings()
        
        inventory = result.fetchone()
        num_potions = num_potions_result.fetchone()["num_potions"]
        num_red_ml = inventory["num_red_ml"]
        num_green_ml = inventory["num_green_ml"]
        num_blue_ml = inventory["num_blue_ml"]
        num_dark_ml = inventory["num_dark_ml"]
        max_potions = inventory["potion_capacity"]
        
    max_potions_to_bottle = max_potions - num_potions
    print(f"num potions: {num_potions}, capacity: {max_potions}, max potions to bottle: {max_potions_to_bottle}")
    
    # Develop plan
    for potion in pot_result:
        if max_potions_to_bottle <= 0:
            break   # not enough capacity for 1 potion
        
        if num_red_ml+num_green_ml+num_blue_ml+num_dark_ml < 100:
            break   # not enough ml for 1 potion
        
        max_per_type = (max_potions // 6) - potion["quantity"]
        
        print(f"potion: {potion}, max to bottle: {max_per_type}")
        if max_per_type <= 0:
            continue
        sku = potion["sku"]
        red_used = potion["red_amt"]
        green_used = potion["green_amt"]
        blue_used = potion["blue_amt"]
        dark_used = potion["dark_amt"]
        
        if red_used+green_used+blue_used+dark_used < ml_per_potion:
            print(f"why tf does ml used for {sku} not add up to {ml_per_potion} >:|")
            break
        
        # check if there's enough ml for the potion
        if red_used > num_red_ml:
            continue
        if green_used > num_green_ml:
            continue
        if blue_used > num_blue_ml:
            continue
        if dark_used > num_dark_ml:
            continue
        
        red_capability = green_capbility = blue_capability = dark_capability = max_potions_to_bottle
        
        if red_used > 0:
            red_capability = num_red_ml // red_used
        if green_used > 0:
            green_capbility = num_green_ml // green_used
        if blue_used > 0:
            blue_capability = num_blue_ml // blue_used
        if dark_used > 0:
            dark_capability = num_dark_ml // dark_used
            
        num_to_bottle = min(red_capability, green_capbility, blue_capability, dark_capability, max_per_type)
        
        max_potions_to_bottle -= num_to_bottle
        num_red_ml -= red_used*num_to_bottle
        num_green_ml -= green_used*num_to_bottle
        num_blue_ml -= blue_used*num_to_bottle
        num_dark_ml -= dark_used*num_to_bottle
        
        print(f"Bottling {num_to_bottle} {sku}!")
        
        plan.append({
            "potion_type": [red_used, green_used, blue_used, dark_used],
            "quantity": num_to_bottle
        })
    
    print(f"Bottle plan: {plan}")
    return plan

if __name__ == "__main__":
    print(get_bottle_plan())