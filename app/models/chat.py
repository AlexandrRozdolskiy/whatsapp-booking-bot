from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from enum import Enum

class MessageType(str, Enum):
    TEXT = "text"
    BOOKING_FORM = "booking_form"
    CONFIRMATION = "confirmation"
    ERROR = "error"
    DAY_SELECTION = "day_selection"
    TIMESLOT_SELECTION = "timeslot_selection"

class ConversationState(str, Enum):
    GREETING = "greeting"
    COLLECTING_JOB_TYPE = "collecting_job_type"
    COLLECTING_DAY = "collecting_day"
    COLLECTING_TIMESLOT = "collecting_timeslot"
    COLLECTING_DATE = "collecting_date"
    COLLECTING_DURATION = "collecting_duration"
    COLLECTING_LOCATION = "collecting_location"
    COLLECTING_BUDGET = "collecting_budget"
    COLLECTING_CONTACT = "collecting_contact"
    CONFIRMING_DETAILS = "confirming_details"
    COMPLETED = "completed"

class ChatMessage(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000)
    session_id: str = Field(..., min_length=1)
    conversation_state: Optional[ConversationState] = ConversationState.GREETING
    timestamp: Optional[str] = None

class ChatResponse(BaseModel):
    message: str
    message_type: MessageType = MessageType.TEXT
    conversation_state: ConversationState
    booking_data: Optional[Dict[str, Any]] = None
    suggested_actions: Optional[List[str]] = None
    available_slots: Optional[List[Dict[str, str]]] = None
    requires_input: bool = True 