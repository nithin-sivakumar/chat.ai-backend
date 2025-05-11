from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid

class MessageBase(BaseModel):
    conversation_id: str = Field(..., description="Identifier for the conversation thread.")
    sender: str = Field(..., description="Sender of the message ('user' or 'assistant').")
    content: str = Field(..., description="Content of the message.")

class MessageCreate(MessageBase):
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class MessageInDB(MessageCreate):
    id: str = Field(alias="_id", default_factory=lambda: str(uuid.uuid4()), description="Unique message identifier.")
    
    class Config:
        # For Pydantic V2, use `populate_by_name = True` instead of `allow_population_by_field_name = True`
        # populate_by_name = True
        # allow_population_by_field_name = True # Allows using '_id' from MongoDB
        validate_by_name = True
        json_encoders = {datetime: lambda dt: dt.isoformat()} # For proper datetime serialization

class NewMessageRequest(BaseModel):
    content: str = Field(..., description="The new message content from the user.")
    # conversation_id will be a path parameter

class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    sender: str
    content: str
    timestamp: datetime

    class Config:
        # Pydantic V2
        from_attributes = True
        # orm_mode = True # Allows creating model from ORM objects (like our dicts from MongoDB)
        json_encoders = {datetime: lambda dt: dt.isoformat()}
