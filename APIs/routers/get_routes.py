import logging

from fastapi import APIRouter
from APIs.db import items_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Items - GET"])

# 1. Root Endpoint
@router.get("/")
def home():
    logger.info("Root endpoint accessed.")
    return {"message": "Hello FastAPI!"}

# 2. Retrieve all items (GET)
@router.get("/items")
def get_items():
    logger.info("Fetching all items. Total count: %d", len(items_db))
    return {"items": items_db}

# 3. Retrieving a specific item by ID (Path Parameter)
@router.get("/items/{item_id}")
def get_item(item_id: int):
    logger.info("Fetching item with ID: %d", item_id)
    if 0 <= item_id < len(items_db):
        return items_db[item_id]
    
    logger.warning("Item lookup failed. ID %d not found in database.", item_id)
    return {"error": "Item not found"}
