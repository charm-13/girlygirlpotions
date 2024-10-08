import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from enum import Enum

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)

cart_id = 0
all_carts = {}

class search_sort_options(str, Enum):
    customer_name = "customer_name"
    item_sku = "item_sku"
    line_item_total = "line_item_total"
    timestamp = "timestamp"

class search_sort_order(str, Enum):
    asc = "asc"
    desc = "desc"   

@router.get("/search/", tags=["search"])
def search_orders(
    customer_name: str = "",
    potion_sku: str = "",
    search_page: str = "",
    sort_col: search_sort_options = search_sort_options.timestamp,
    sort_order: search_sort_order = search_sort_order.desc,
):
    """
    Search for cart line items by customer name and/or potion sku.

    Customer name and potion sku filter to orders that contain the 
    string (case insensitive). If the filters aren't provided, no
    filtering occurs on the respective search term.

    Search page is a cursor for pagination. The response to this
    search endpoint will return previous or next if there is a
    previous or next page of results available. The token passed
    in that search response can be passed in the next search request
    as search page to get that page of results.

    Sort col is which column to sort by and sort order is the direction
    of the search. They default to searching by timestamp of the order
    in descending order.

    The response itself contains a previous and next page token (if
    such pages exist) and the results as an array of line items. Each
    line item contains the line item id (must be unique), item sku, 
    customer name, line item total (in gold), and timestamp of the order.
    Your results must be paginated, the max results you can return at any
    time is 5 total line items.
    """

    return {
        "previous": "",
        "next": "",
        "results": [
            {
                "line_item_id": 1,
                "item_sku": "1 oblivion potion",
                "customer_name": "Scaramouche",
                "line_item_total": 50,
                "timestamp": "2021-01-01T00:00:00Z",
            }
        ],
    }


class Customer(BaseModel):
    customer_name: str
    character_class: str
    level: int

@router.post("/visits/{visit_id}")
def post_visits(visit_id: int, customers: list[Customer]):
    """
    Which customers visited the shop today?
    """
    print(f"customers visited: {customers}")
    print(f"visit_id: {visit_id}")

    return { "success": True }


@router.post("/")
def create_cart(new_cart: Customer):
    """ """
    # TODO: create a new table to handle the carts
    global cart_id
    cart_id += 1
    all_carts[cart_id] = {"customer": new_cart, "items": {}}
    print(f"cart id: {cart_id}, new cart: {new_cart}")
    
    return { "cart_id": cart_id }


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """
    print(f"cart_id: {cart_id}, item_sku: {item_sku}, cart_item: {cart_item}")
    
    if cart_id not in all_carts:
        return {"success": False}
    
    with db.engine.begin() as connection:
    # assume there is a row for each potion type
        connection.execute(
            sqlalchemy.text("UPDATE potion_inventory \
                            SET quantity = quantity - :cart_quantity \
                            WHERE sku = :item_sku"),
                            {"cart_quantity": cart_item.quantity, "item_sku": item_sku})

    cart = all_carts[cart_id]
        
    cart["items"][item_sku] = cart_item.quantity
    print(f"Added {cart_item.quantity} {item_sku} to cart {cart_id}")
    return {"success": True}


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    total_potions_bought = 0
    total_gold_paid = 0
    # catalog =  #retrieves the catalog
        
    # calculate how much they bought and how much they owe me :)
    if cart_id in all_carts:
        cart = all_carts[cart_id]
        for item_sku, item_quantity in cart["items"].items():
            total_potions_bought += item_quantity
            if item_sku == "RED_POTION":
                total_gold_paid += item_quantity*50
                
            if item_sku == "GREEN_POTION":
                total_gold_paid += item_quantity*50
                
            if item_sku == "BLUE_POTION":
                total_gold_paid += item_quantity*60
                
            if item_sku == "DARK_POTION":
                total_gold_paid += item_quantity*70
                
            
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text("UPDATE global_inventory \
                                            SET num_potions = num_potions - :total_potions_bought, \
                                                gold = gold + :total_gold_paid"),
                        {"total_potions_bought": total_potions_bought, "total_gold_paid": total_gold_paid})
        
    print(f"for cart {cart_id} -- total_potions_bought: {total_potions_bought}, total_gold_paid: {total_gold_paid} with payment: {cart_checkout.payment}")
    return {"total_potions_bought": total_potions_bought,
            "total_gold_paid": total_gold_paid}
