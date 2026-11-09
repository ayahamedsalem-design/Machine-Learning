from typing import Optional
from pydantic import BaseModel

# Data Schema using Pydantic
class Item(BaseModel):
    name: str
    price: float
    description: Optional[str] = None
    in_stock: bool = True

class ChatRequest(BaseModel):
    message: str