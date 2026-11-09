from fastapi import FastAPI
from APIs.routers.get_routes import router as get_router
from APIs.routers.post_routes import router as post_router

app = FastAPI(title="My First Modular API", version="1.0")

app.include_router(get_router)
app.include_router(post_router)

