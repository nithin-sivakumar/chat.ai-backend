# app/services/chat_service.py
import os
from datetime import datetime, timezone # Ensure timezone for consistency
from typing import List, Dict, Any
from fastapi import HTTPException, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase
from groq import Groq
from app.core.config import settings
from app.models.message import MessageCreate, MessageInDB, MessageResponse # Make sure these models are V1
from fastapi.concurrency import run_in_threadpool

# Initialize Groq client
try:
    groq_client = Groq(api_key=settings.GROQ_API_KEY)
    if not settings.GROQ_API_KEY:
        print("Warning: GROQ_API_KEY is not set. Groq functionality will not work.")
except Exception as e:
    print(f"Error initializing Groq client: {e}")
    groq_client = None

# MAX_HISTORY_TOKENS will be ignored for now due to debugging changes below
MAX_HISTORY_TOKENS = 7800 

async def add_message_to_db(
    db: AsyncIOMotorDatabase,
    conversation_id: str,
    sender: str,
    content: str
) -> MessageInDB:
    message_data = MessageCreate(
        conversation_id=conversation_id,
        sender=sender,
        content=content,
        timestamp=datetime.now(timezone.utc)
    )
    # --- PYDANTIC V1 ---
    message_dict = message_data.dict() 
    new_message_doc = MessageInDB.parse_obj(message_dict)
    await db[settings.MESSAGE_COLLECTION_NAME].insert_one(new_message_doc.dict(by_alias=True))
    # --- END PYDANTIC V1 ---
    
    return new_message_doc

async def get_conversation_history_for_grog(
    db: AsyncIOMotorDatabase,
    conversation_id: str,
    limit: int = 20 # Fetch up to 20 *individual messages* (10 turns) for context
) -> List[Dict[str, str]]:
    """
    Fetches conversation history and formats it for the Groq API.
    Returns a list of {"role": "...", "content": "..."} dicts.
    Orders from oldest to newest suitable for Groq.
    TOKEN TRUNCATION TEMPORARILY DISABLED FOR DEBUGGING.
    """
    print(f"DEBUG_HISTORY_FUNC: Fetching history for conv {conversation_id}, DB message limit {limit}")
    cursor = db[settings.MESSAGE_COLLECTION_NAME].find(
        {"conversation_id": conversation_id}
    ).sort("timestamp", -1).limit(limit) # Get latest 'limit' messages
    
    history_docs_raw = await cursor.to_list(length=limit)
    history_docs_raw.reverse() # Put them in chronological order (oldest first)
    print(f"DEBUG_HISTORY_FUNC: Raw docs fetched and reversed: {len(history_docs_raw)}")

    # --- PYDANTIC V1 ---
    history_models = [MessageInDB.parse_obj(doc) for doc in history_docs_raw]
    # --- END PYDANTIC V1 ---

    formatted_history_for_groq: List[Dict[str, str]] = []
    
    # --- TEMPORARILY DISABLE TOKEN TRUNCATION ---
    print("DEBUG_HISTORY_FUNC: TOKEN TRUNCATION IS CURRENTLY DISABLED.")
    for msg_model in history_models: # Iterate chronologically (already reversed)
        formatted_history_for_groq.append({"role": msg_model.sender, "content": msg_model.content})
    # --- END TEMPORARY DISABLE ---
            
    print(f"DEBUG_HISTORY_FUNC: Formatted history for Groq (length {len(formatted_history_for_groq)}):")
    for i, h_msg in enumerate(formatted_history_for_groq):
        print(f"  DEBUG_HISTORY_FUNC Hist Msg {i}: Role: {h_msg['role']}, Content: '{h_msg['content'][:60]}...'")
    return formatted_history_for_groq


async def get_ai_response_and_save(
    db: AsyncIOMotorDatabase,
    conversation_id: str,
    user_message_content: str,
    background_tasks: BackgroundTasks 
) -> MessageResponse:
    if not groq_client:
        raise HTTPException(status_code=503, detail="Groq AI service is not available. API key might be missing or invalid.")

    user_msg_doc = await add_message_to_db(db, conversation_id, "user", user_message_content)
    
    # Fetch history. With token truncation disabled, 'limit' in get_conversation_history_for_grog
    # will directly determine how many past messages are sent.
    # Let's use a smaller limit for easier debugging initially.
    chat_history_for_groq = await get_conversation_history_for_grog(db, conversation_id, limit=10) # Try with last 10 messages (5 turns)

    messages_for_groq_api: List[Dict[str, str]] = []
    messages_for_groq_api.append({"role": "system", "content": settings.SYSTEM_PROMPT})
    messages_for_groq_api.extend(chat_history_for_groq)
    
    # The user's current message IS INCLUDED in chat_history_for_groq because:
    # 1. We called add_message_to_db() for the user message BEFORE calling get_conversation_history_for_grog().
    # 2. get_conversation_history_for_grog() fetches based on the current DB state.

    print("-" * 80)
    print(f"DEBUG_MAIN_FUNC: Conversation ID: {conversation_id}")
    print(f"DEBUG_MAIN_FUNC: System Prompt: {settings.SYSTEM_PROMPT}")
    print(f"DEBUG_MAIN_FUNC: Final messages_for_groq_api (length {len(messages_for_groq_api)}):")
    for i, api_msg in enumerate(messages_for_groq_api):
        print(f"  DEBUG_MAIN_FUNC API Msg {i}: Role: {api_msg['role']}, Content: '{api_msg['content'][:100]}...'")
    print("-" * 80)

    try:
        chat_completion = await run_in_threadpool(
            groq_client.chat.completions.create,
            messages=messages_for_groq_api,
            model=settings.GROQ_MODEL_NAME,
        )
        ai_content = chat_completion.choices[0].message.content
    except Exception as e:
        print(f"Error calling Groq API for conversation {conversation_id}: {e}")
        raise HTTPException(status_code=503, detail=f"AI service error: {str(e)}")

    assistant_msg_doc = await add_message_to_db(db, conversation_id, "assistant", ai_content)
    
    # --- PYDANTIC V1 ---
    return MessageResponse.from_orm(assistant_msg_doc) 
    # --- END PYDANTIC V1 ---

async def get_formatted_history( 
    db: AsyncIOMotorDatabase,
    conversation_id: str,
    skip: int = 0,
    limit: int = 100
) -> List[MessageResponse]:
    cursor = db[settings.MESSAGE_COLLECTION_NAME].find(
        {"conversation_id": conversation_id}
    ).sort("timestamp", 1).skip(skip).limit(limit)
    
    history_docs = await cursor.to_list(length=limit)
    
    # --- PYDANTIC V1 ---
    # Assuming MessageInDB and MessageResponse are Pydantic V1 models
    # and MessageResponse.Config has orm_mode = True
    response_list = [MessageResponse.from_orm(MessageInDB.parse_obj(doc)) for doc in history_docs]
    # --- END PYDANTIC V1 ---
    return response_list