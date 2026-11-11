from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dbs.redisdb import redis_client

app = FastAPI()

# Pydantic model for setting data
class ItemData(BaseModel):
    key: str
    value: str

# API endpoint to save data in Redis (SET)
@app.post("/redis/set")
def set_item(item: ItemData):
    try:
        # Save key-value pair in Redis
        redis_client.set(item.key, item.value)
        return {"message": "Data saved successfully in Redis!", "key": item.key, "value": item.value}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# API endpoint to retrieve data from Redis by key (GET)
@app.get("/redis/get/{key}")
def get_item(key: str):
    value = redis_client.get(key)
    if value is None:
        raise HTTPException(status_code=404, detail="Key not found in Redis")
    return {"key": key, "value": value}