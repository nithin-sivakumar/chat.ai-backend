from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

class DataBase:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None

db_manager = DataBase()

async def connect_to_mongo():
    print("Connecting to MongoDB...")
    try:
        db_manager.client = AsyncIOMotorClient(settings.MONGO_DETAILS)
        db_manager.db = db_manager.client[settings.DATABASE_NAME]
        # You can try a simple command to verify connection
        await db_manager.db.command('ping') 
        print(f"Successfully connected to MongoDB database: {settings.DATABASE_NAME}")
        # Create indexes if they don't exist
        message_collection = db_manager.db[settings.MESSAGE_COLLECTION_NAME]
        await message_collection.create_index([("conversation_id", 1), ("timestamp", 1)])
        await message_collection.create_index([("timestamp", 1)])
        print(f"Ensured indexes on '{settings.MESSAGE_COLLECTION_NAME}' collection.")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        # Potentially raise an error or exit if connection is critical for startup
        raise

async def close_mongo_connection():
    print("Closing MongoDB connection...")
    if db_manager.client:
        db_manager.client.close()
        print("MongoDB connection closed.")

async def get_database() -> AsyncIOMotorDatabase:
    if db_manager.db is None:
        # This case should ideally not happen if connect_to_mongo is called at startup
        await connect_to_mongo() 
    return db_manager.db
