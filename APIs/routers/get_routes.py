
from fastapi import APIRouter
from db import items_db

router = APIRouter(tags=["Items - GET"])

# 1. Root Endpoint
@router.get("/")
def home():
    return {"message": "Hello FastAPI!"}

# 2. Retrieve all items (GET)
@router.get("/items")
def get_items():
    return {"items": items_db}

# 3. Retrieving a specific item by ID (Path Parameter)
@router.get("/items/{item_id}")
def get_item(item_id: int):
    if 0 <= item_id < len(items_db):
        return items_db[item_id]
    return {"error": "Item not found"}
