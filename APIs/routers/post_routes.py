from APIs.db import items_db
from fastapi import APIRouter
from APIs.model import chat_with_ai
from APIs.schemas import Item, ChatRequest

router = APIRouter(tags=["Items - POST"])

# import schema from a separate schemas.py file

# add a new
@router.post("/items")
def create_item(item: Item):
    items_db.append(item)
    return {"message": "Item added Successfully...", "item": item}

# send a question to the model
@router.post("/chat")
def chat_endpoint(request: ChatRequest):
    reply = chat_with_ai(request.message)
    return {"response": reply}