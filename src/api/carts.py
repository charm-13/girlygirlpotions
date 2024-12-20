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
    
    try:
        carts = sqlalchemy.Table("carts", sqlalchemy.MetaData(), autoload_with=db.engine)
        carts_items = sqlalchemy.Table("carts_items", sqlalchemy.MetaData(), autoload_with=db.engine)
        potions = sqlalchemy.Table("recipe_book", sqlalchemy.MetaData(), autoload_with=db.engine)
        
        search = (
            sqlalchemy.select(
                carts_items.c.id,
                carts_items.c.item_sku,
                (carts_items.c.quantity * potions.c.price).label("line_item_total"),
                carts_items.c.time_created,
                carts.c.customer_name
            )
            .join(carts, carts_items.c.cart_id == carts.c.id)
            .join(potions, carts_items.c.item_sku == potions.c.sku)
        )
        
        limit = 5 
        offset = 0
        if search_page != "":
            offset = int(search_page)
        if potion_sku != "":
            search = search.where(carts_items.c.item_sku.ilike(f"%{potion_sku}%"))
        if customer_name != "":
            search = search.where(carts.c.customer_name.ilike(f"%{customer_name}%"))
        
        match sort_col:
            case search_sort_options.customer_name:
                sort = carts.c.customer_name
            case search_sort_options.item_sku:
                sort = carts_items.c.item_sku
            case search_sort_options.line_item_total:
                sort = carts_items.c.quantity
            case search_sort_options.timestamp:  
                sort = carts_items.c.time_created
            case _:
                raise ValueError(f"sort_col was not in one of the listed options: customer_name, item_sku, line_item_total, or timestamp. Given {sort_col}")      
        
        match sort_order:
            case search_sort_order.desc:
                order_by = sqlalchemy.desc(sort)
            case search_sort_order.asc:
                order_by = sort
            case _:
                raise ValueError(f"sort_order was not in one of the listed options: asc, or desc. Given {sort_order}")
            
        search = search.limit(limit).offset(offset).order_by(order_by)
    
        with db.engine.begin() as connection:
            result = connection.execute(search).fetchall()
            
            json = []
            for row in result:
                json.append({
                    "line_item_id": row.id,
                    "item_sku": row.item_sku,
                    "customer_name": row.customer_name,
                    "line_item_total": row.line_item_total,
                    "timestamp": row.time_created,
                })
                
        previous_page = offset - limit if offset > 0 else None
        next_page = offset + limit if len(result) == limit else None

        return {
            "previous": str(previous_page) if previous_page is not None else "",
            "next": str(next_page) if next_page is not None else "",
            "results": json,
        }
    
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {"success": False, "error": str(e)}


class Customer(BaseModel):
    customer_name: str
    character_class: str
    level: int

@router.post("/visits/{visit_id}")
def post_visits(visit_id: int, customers: list[Customer]):
    """
    Which customers visited the shop today?
    """
    print(f"visit_id: {visit_id}, customers visited: {customers}")

    return { "success": True }


@router.post("/")
def create_cart(new_cart: Customer):
    """ """
    try:
        with db.engine.begin() as connection:
            id = connection.execute(
                sqlalchemy.text("""INSERT INTO carts (customer_name, character_class, level, time_created)
                                SELECT :name, :class, :level, CURRENT_TIMESTAMP AT TIME ZONE 'America/Los_Angeles' 
                                RETURNING id"""),
                {"name": new_cart.customer_name, "class": new_cart.character_class, "level": new_cart.level}
            ).mappings()
            
            cart_id = id.fetchone()["id"]
            
            print(f"cart id: {cart_id}, new cart for: {new_cart}")
            return { "cart_id": cart_id }
        
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {"success": False, "error": str(e)}


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """
    print(f"Finding cart {cart_id}...")
    
    try:
        with db.engine.begin() as connection:
            ids = connection.execute(
                sqlalchemy.text("""SELECT id 
                                FROM carts 
                                WHERE id = :cart_id"""), 
                {"cart_id": cart_id}
            ).fetchone()
            
            if ids is None:
                print(f"cart {cart_id} doesn't exist")
                return {"success": False} 
        
            connection.execute(
                sqlalchemy.text("""INSERT INTO carts_items (cart_id, item_sku, quantity) 
                                VALUES (:id, :sku, :amt)"""), 
                {"id": cart_id, "sku": item_sku, "amt": cart_item.quantity}
            )
            connection.execute(
                sqlalchemy.text("""INSERT INTO potion_inventory (sku, quantity)
                                VALUES (:item_sku, -:cart_quantity)"""),
                                {"cart_quantity": cart_item.quantity, "item_sku": item_sku})

        print(f"Added {cart_item.quantity} {item_sku} to cart {cart_id}")
        return {"success": True}
    
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {"success": False, "error": str(e)}


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    print(f"Starting checkout for cart {cart_id}...")
    total_potions_bought = 0
    total_gold_paid = 0
    
    try:
        with db.engine.begin() as connection:
            items = connection.execute(
                sqlalchemy.text("""SELECT carts_items.cart_id, carts_items.item_sku, carts_items.quantity, recipe_book.price
                                FROM carts_items 
                                JOIN recipe_book ON recipe_book.sku = carts_items.item_sku
                                WHERE cart_id = :cart_id"""), 
                {"cart_id": cart_id}
            ).mappings()
            
            if not items:
                print(f"cart {cart_id} is empty or doesn't exist")
                return {"error": "Cart is empty or doesn't exist"}
            
            purchases = []
            for item in items:
                sku = item["item_sku"]
                quantity = item["quantity"]
                price = item["price"]
                total_potions_bought += quantity
                total_gold_paid += quantity*price
                
                purchases.append({"sku": sku, "quantity": quantity, "price per item": price})          
            
            connection.execute(sqlalchemy.text("""INSERT INTO treasury_log (gold)
                                                VALUES (:total_gold_paid)"""),
                            {"total_gold_paid": total_gold_paid})
                
            print(f"cart {cart_id} bought {purchases} \n"
                  f"\t cart {cart_id} bought {total_potions_bought} potions and paid {total_gold_paid} gold with {cart_checkout.payment} as payment") 
            
        return {"total_potions_bought": total_potions_bought,
                "total_gold_paid": total_gold_paid}
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return {"error": str(e)}
