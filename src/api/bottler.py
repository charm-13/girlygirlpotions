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
    
    red_cost_per_ml = 0.5
    green_cost_per_ml = 0.5
    blue_cost_per_ml = 0.5
    dark_cost_per_ml = 0.6
    
    with db.engine.begin() as connection:
        inventory_potions = connection.execute(
            sqlalchemy.text("SELECT sku, red_amt, green_amt, blue_amt, dark_amt \
                            FROM potion_mixes")
        ).mappings()
    
        for potion in potions_delivered:
            red_ml = potion.potion_type[0]
            green_ml = potion.potion_type[1]
            blue_ml = potion.potion_type[2]
            dark_ml = potion.potion_type[3]
            
            red_ml_used += red_ml
            green_ml_used += green_ml
            blue_ml_used += blue_ml
            dark_ml_used += dark_ml
            
            sku = "NONE"
            name = "None" 
            
            price = red_cost_per_ml*red_ml + green_cost_per_ml*green_ml + \
                    blue_cost_per_ml*blue_ml + dark_cost_per_ml*dark_ml
            
            for pot in inventory_potions:
                pot_mix = [pot["red_amt"], pot["green_amt"], pot["blue_amt"], pot["dark_amt"]]
                if pot_mix == potion.potion_type:
                    sku = pot["sku"]
                    break
            
            if sku == "NONE":
                print(f"{potion} doesn't exist :|")
                
            # connection.execute(
            # sqlalchemy.text("INSERT INTO potion_inventory (sku, name, quantity, price) \
            #                 SELECT :sku, :name, :quantity, :price \
            #                 WHERE NOT EXISTS \
            #                     (UPDATE potion_inventory SET quantity = quantity + :quantity WHERE sku = :sku)"),
            # {"sku": sku, "name": name, "quantity": potion.quantity, "price": price})  
            connection.execute(
            sqlalchemy.text("UPDATE potion_inventory SET quantity = quantity + :quantity WHERE sku = :sku"),
            {"sku": sku, "quantity": potion.quantity})  
            # connection.execute(
            # sqlalchemy.text("INSERT INTO potion_mixes (sku, red_amt, green_amt, blue_amt, dark_amt) \
            #                 SELECT :sku, :name, :quantity, :price \
            #                 WHERE NOT EXISTS \
            #                     (UPDATE potion_mixes \
            #                     SET red_amt = red_amt + :red_amt, \
            #                     green_amt = green_amt + :green_amt, \
            #                     blue_amt = blue_amt + :blue_amt, \
            #                     dark_amt = dark_amt + :dark_amt, \
            #                     WHERE sku = :sku)"),
            # {"sku": sku, "name": name, "red_amt": red_ml_used, "green_amt": green_ml_used, "blue_amt": blue_ml_used, "dark_amt": dark_ml_used})   
        connection.execute(
            sqlalchemy.text("UPDATE global_inventory \
                            SET num_red_ml = num_red_ml - :red_ml_used, \
                                num_green_ml = num_green_ml - :green_ml_used, \
                                num_blue_ml = num_blue_ml - :blue_ml_used, \
                                num_dark_ml = num_dark_ml - :dark_ml_used"),
                           {"red_ml_used": red_ml_used, 
                            "green_ml_used": green_ml_used, 
                            "blue_ml_used": blue_ml_used, 
                            "dark_ml_used": dark_ml_used})
        
    print(f"potions delievered: {potions_delivered} order_id: {order_id}")
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
            sqlalchemy.text("SELECT num_red_ml, num_green_ml, num_blue_ml, num_dark_ml, potion_capacity FROM global_inventory")
            ).mappings()
        pot_result = connection.execute(
            sqlalchemy.text("SELECT potion_inventory.sku, red_amt, green_amt, blue_amt, dark_amt, potion_inventory.quantity \
                            FROM potion_mixes \
                            JOIN potion_inventory ON potion_inventory.sku = potion_mixes.sku \
                            ORDER BY potion_inventory.quantity")
        ).mappings()
        num_potions_result = connection.execute(
            sqlalchemy.text("SELECT SUM(quantity) as num_potions \
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
    print(f"max potions to bottle: {max_potions_to_bottle}")
    
    #TODO: change logic when there's more than 6 possible potions
    # Develop plan
    for potion in pot_result:
        print(f"potion: {potion}")
        if max_potions_to_bottle <= 0:
            break   # not enough capacity for 1 potion
        
        if num_red_ml+num_green_ml+num_blue_ml+num_dark_ml < 100:
            break   # not enough ml for 1 potion
        
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
            
        num_to_bottle = min(red_capability, green_capbility, blue_capability, dark_capability)
        
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