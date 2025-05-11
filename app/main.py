# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.db.mongodb import connect_to_mongo, close_mongo_connection, db_manager
from app.routers import chat as chat_router
from app.core.config import settings # To ensure settings are loaded

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Application startup...")
    await connect_to_mongo()
    # You could add other startup events here, like initializing ML models, etc.
    yield
    # Shutdown
    print("Application shutdown...")
    await close_mongo_connection()

app = FastAPI(
    title="Chat API with FastAPI, MongoDB, and Groq",
    description="An API for managing chat conversations and interacting with Groq AI.",
    version="1.0.0",
    lifespan=lifespan # New way to handle startup/shutdown in FastAPI 0.9 lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to your frontend's domain(s)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router.router)

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the Chat API. Visit /docs for API documentation."}

# To run the app (save this in a file like run.py in project root or use uvicorn directly):
# import uvicorn
# if __name__ == "__main__":
#     uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
