from fastapi import APIRouter, HTTPException, Depends
from app.models.chat import ChatMessage, ChatResponse
from app.services.openai_service import OpenAIService
from app.services.bot_logic import BookingBotLogic
from app.core.dependencies import get_openai_service, get_bot_logic
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/message", response_model=ChatResponse)
async def send_message(
    message: ChatMessage,
    bot_logic: BookingBotLogic = Depends(get_bot_logic)
):
    try:
        # Process user message through conversation flow
        response = await bot_logic.process_message(
            user_message=message.content,
            session_id=message.session_id,
            conversation_state=message.conversation_state
        )
        
        return ChatResponse(
            message=response["message"],
            message_type=response["message_type"],
            conversation_state=response["conversation_state"],
            booking_data=response["booking_data"],
            suggested_actions=response["suggested_actions"],
            available_slots=response.get("available_slots"),
            requires_input=response.get("requires_input", True)
        )
        
    except Exception as e:
        logger.error(f"Chat processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process message")

@router.post("/reset")
async def reset_conversation(
    session_id: str,
    bot_logic: BookingBotLogic = Depends(get_bot_logic)
):
    """Reset conversation state for given session"""
    try:
        success = bot_logic.reset_session(session_id)
        
        if success:
            return {"status": "conversation_reset", "session_id": session_id}
        else:
            return {"status": "session_not_found", "session_id": session_id}
            
    except Exception as e:
        logger.error(f"Reset conversation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to reset conversation")

@router.get("/session/{session_id}")
async def get_session_data(
    session_id: str,
    bot_logic: BookingBotLogic = Depends(get_bot_logic)
):
    """Get current session data"""
    try:
        session_data = bot_logic.get_session_data(session_id)
        
        if session_data:
            return {
                "session_id": session_id,
                "conversation_state": session_data["conversation_state"],
                "booking_data": session_data["booking_data"],
                "message_count": len(session_data["conversation_history"])
            }
        else:
            return {"session_id": session_id, "status": "not_found"}
            
    except Exception as e:
        logger.error(f"Get session data error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get session data") 