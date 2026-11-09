import logging

from APIs.db import items_db
from fastapi import APIRouter
from APIs.model import chat_with_ai
from APIs.schemas import Item, ChatRequest

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Items - POST"])

# import schema from a separate schemas.py file

# add a new
@router.post("/items")
def create_item(item: Item):
    logger.info("Adding new item: %s", item.name)
    logger.debug("Item payload: %s", item.model_dump())

    items_db.append(item)
    logger.info("Item '%s' added successfully. Current total: %d", item.name, len(items_db))
    return {"message": "Item added Successfully...", "item": item}

# send a question to the model
@router.post("/chat")
def chat_endpoint(request: ChatRequest):
    logger.info("Received chat request from user.")
    reply = chat_with_ai(request.message)
    return {"response": reply}