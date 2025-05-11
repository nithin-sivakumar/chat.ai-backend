# app/routers/chat.py
from fastapi import APIRouter, Depends, HTTPException, Path, Query, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List
import uuid # For generating conversation_id if not provided or for new conversations

from app.db.mongodb import get_database
from app.models.message import NewMessageRequest, MessageResponse
from app.services import chat_service

router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)

@router.post("/{conversation_id}/send", response_model=MessageResponse)
async def send_message(
    payload: NewMessageRequest,
    conversation_id: str = Path(..., description="The ID of the conversation. Can be a new UUID if starting a new chat."),
    db: AsyncIOMotorDatabase = Depends(get_database),
    background_tasks: BackgroundTasks = BackgroundTasks() # If you have tasks to run after response
):
    """
    Send a new message from a user to a conversation.
    The system will process it, get a response from the AI, and return the AI's message.
    Both user and AI messages are stored.

    - **conversation_id**: A unique identifier for the chat session. If you send a message
      to a new `conversation_id`, a new chat history will begin. It's recommended to use UUIDs.
    - **content**: The text of the user's message.
    """
    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="Message content cannot be empty.")

    try:
        # Validate conversation_id format (optional, e.g., if you expect UUIDs)
        # uuid.UUID(conversation_id) 
        pass
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation_id format. Expected UUID.")

    ai_response_message = await chat_service.get_ai_response_and_save(
        db=db,
        conversation_id=conversation_id,
        user_message_content=payload.content,
        background_tasks=background_tasks
    )
    return ai_response_message

@router.get("/{conversation_id}/history", response_model=List[MessageResponse])
async def get_message_history(
    conversation_id: str = Path(..., description="The ID of the conversation."),
    skip: int = Query(0, ge=0, description="Number of messages to skip."),
    limit: int = Query(100, ge=1, le=200, description="Maximum number of messages to return."),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Retrieve the message history for a given conversation.
    Messages are returned in chronological order (oldest first).
    """
    try:
        # Validate conversation_id format (optional)
        # uuid.UUID(conversation_id)
        pass
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation_id format. Expected UUID.")

    history = await chat_service.get_formatted_history(
        db=db,
        conversation_id=conversation_id,
        skip=skip,
        limit=limit
    )
    if not history and skip == 0: # Only raise 404 if it's a genuinely new/empty convo, not if skip > results
        # Check if conversation_id actually exists, even if empty
        count = await db[chat_service.settings.MESSAGE_COLLECTION_NAME].count_documents({"conversation_id": conversation_id})
        if count == 0:
             raise HTTPException(status_code=404, detail="Conversation not found.")
    return history

# Optional: Endpoint to start a new conversation and get an ID
@router.post("/new", status_code=201, summary="Start a new conversation")
async def start_new_conversation():
    """
    Generates a new unique conversation ID.
    Use this ID for subsequent calls to /send and /history.
    """
    new_conv_id = str(uuid.uuid4())
    return {"conversation_id": new_conv_id, "message": "New conversation started. Use this ID for future messages."}
