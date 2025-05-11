import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env file from the project root if it exists
# This is useful for local development
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

class Settings(BaseSettings):
    MONGO_DETAILS: str
    DATABASE_NAME: str = "chat_db"
    MESSAGE_COLLECTION_NAME: str = "messages"
    
    GROQ_API_KEY: str
    GROQ_MODEL_NAME: str = "llama3-8b-8192"
    SYSTEM_PROMPT: str = "You are a helpful AI assistant."

    # Optional: For future security enhancements
    # SECRET_KEY: str = "a_very_secret_key"
    # ALGORITHM: str = "HS256"
    # ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env" # Redundant if load_dotenv is used above, but good for explicitness
        env_file_encoding = 'utf-8'
        # For Pydantic V2, use extra='ignore' if you have extra fields in .env
        # extra = 'ignore' 

settings = Settings()
