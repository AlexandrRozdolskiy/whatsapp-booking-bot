from app.services.openai_service import OpenAIService
from app.services.google_calendar_service import GoogleCalendarService
from app.models.chat import ConversationState, MessageType
from typing import Dict, List, Any, Optional
import logging
import re
from datetime import datetime, timedelta

class BookingBotLogic:
    def __init__(self, openai_service: OpenAIService):
        self.openai_service = openai_service
        self.calendar_service = GoogleCalendarService()
        self.logger = logging.getLogger(__name__)
        
        # In-memory session storage (in production, use Redis or database)
        self.sessions = {}

    async def process_message(
        self,
        user_message: str,
        session_id: str,
        conversation_state: Optional[ConversationState] = None
    ) -> Dict[str, Any]:
        
        # Initialize session if not exists
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "conversation_state": ConversationState.GREETING,
                "booking_data": {},
                "conversation_history": [],
                "available_slots": []
            }
        
        session = self.sessions[session_id]
        current_state = conversation_state or session["conversation_state"]
        
        # Handle initial greeting - ask for username first
        if current_state == ConversationState.GREETING:
            session["conversation_state"] = ConversationState.COLLECTING_CONTACT
            return {
                "message": "👋 Hi! I'm JobBot, your AI booking assistant. I can help you book photography, videography, audio, or other freelance services. What's your name?",
                "message_type": MessageType.TEXT,
                "conversation_state": ConversationState.COLLECTING_CONTACT,
                "booking_data": session["booking_data"],
                "suggested_actions": [],
                "requires_input": True
            }
        
        # Add user message to history (only if not empty)
        if user_message.strip():
            session["conversation_history"].append({
                "role": "user",
                "content": user_message,
                "timestamp": datetime.now().isoformat()
            })
        
        try:
            # Handle special cases for day and timeslot selection
            if current_state == ConversationState.COLLECTING_DAY:
                return await self._handle_day_selection(user_message, session_id, session)
            elif current_state == ConversationState.COLLECTING_TIMESLOT:
                return await self._handle_timeslot_selection(user_message, session_id, session)
            elif current_state == ConversationState.COLLECTING_CONTACT:
                return await self._handle_contact_collection(user_message, session_id, session)
            
            # Get AI response for other states
            ai_response = await self.openai_service.generate_bot_response(
                user_message=user_message,
                conversation_context=session["conversation_history"][-5:],  # Last 5 messages
                booking_state=current_state.value,
                booking_data=session["booking_data"]
            )
            
            # Update booking data if provided
            if ai_response.get("booking_data"):
                session["booking_data"].update(ai_response["booking_data"])
            
            # Determine next state
            next_state = self._determine_next_state(current_state, session["booking_data"])
            session["conversation_state"] = next_state
            
            # Add bot response to history
            session["conversation_history"].append({
                "role": "assistant",
                "content": ai_response["message"],
                "timestamp": datetime.now().isoformat()
            })
            
            # Prepare response
            response = {
                "message": ai_response["message"],
                "message_type": MessageType.TEXT,
                "conversation_state": next_state,
                "booking_data": session["booking_data"],
                "suggested_actions": self._get_suggested_actions(next_state),
                "requires_input": True
            }
            
            # Special handling for completion
            if next_state == ConversationState.COMPLETED:
                response["message_type"] = MessageType.CONFIRMATION
                response["requires_input"] = False
                # Create the calendar booking
                await self._create_calendar_booking(session)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")
            return {
                "message": "I'm sorry, I encountered an error. Please try again.",
                "message_type": MessageType.ERROR,
                "conversation_state": current_state,
                "booking_data": session["booking_data"],
                "suggested_actions": ["Try again"],
                "requires_input": True
            }

    async def _handle_contact_collection(self, user_message: str, session_id: str, session: Dict[str, Any]) -> Dict[str, Any]:
        """Handle contact name collection"""
        try:
            # Store the user's name
            session["booking_data"]["contact_name"] = user_message.strip()
            
            # Move to job type collection
            session["conversation_state"] = ConversationState.COLLECTING_JOB_TYPE
            
            return {
                "message": f"Nice to meet you, {user_message.strip()}! 😊 What type of job do you need help with?",
                "message_type": MessageType.TEXT,
                "conversation_state": ConversationState.COLLECTING_JOB_TYPE,
                "booking_data": session["booking_data"],
                "suggested_actions": ["Photography", "Videography", "Audio", "Other"],
                "requires_input": True
            }
            
        except Exception as e:
            self.logger.error(f"Error handling contact collection: {str(e)}")
            return {
                "message": "Sorry, I didn't catch that. What's your name?",
                "message_type": MessageType.ERROR,
                "conversation_state": ConversationState.COLLECTING_CONTACT,
                "booking_data": session["booking_data"],
                "suggested_actions": [],
                "requires_input": True
            }

    async def _handle_day_selection(self, user_message: str, session_id: str, session: Dict[str, Any]) -> Dict[str, Any]:
        """Handle day selection and get available slots"""
        try:
            # Store the selected day
            session["booking_data"]["selected_day"] = user_message
            
            # Get duration from booking data or default to 2 hours
            duration_str = session["booking_data"].get("duration", "2")
            
            # Extract numeric value from duration string
            if isinstance(duration_str, str):
                # Handle cases like "2 hours", "4 hours", "Full day", etc.
                if "full day" in duration_str.lower():
                    duration = 8
                elif "half day" in duration_str.lower():
                    duration = 4
                else:
                    # Extract first number from string
                    numbers = re.findall(r'\d+', duration_str)
                    duration = int(numbers[0]) if numbers else 2
            else:
                duration = int(duration_str)
            
            self.logger.info(f"Parsed duration: {duration} hours from '{duration_str}'")
            
            # Get available slots for the selected day
            slots_result = await self.calendar_service.get_available_slots(
                day_input=user_message,
                duration_hours=duration
            )
            
            if not slots_result["success"]:
                return {
                    "message": f"Sorry, I couldn't find available slots for {user_message}. {slots_result.get('error', '')} Please try another day.",
                    "message_type": MessageType.ERROR,
                    "conversation_state": ConversationState.COLLECTING_DAY,
                    "booking_data": session["booking_data"],
                    "suggested_actions": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                    "requires_input": True
                }
            
            # Store available slots
            session["available_slots"] = slots_result["available_slots"]
            session["booking_data"]["booking_date"] = slots_result["date"]
            session["booking_data"]["date_iso"] = slots_result["date_iso"]
            session["booking_data"]["duration_hours"] = duration  # Store parsed duration
            
            if not slots_result["available_slots"]:
                return {
                    "message": f"Unfortunately, there are no available {duration}-hour slots on {slots_result['date']}. Please try another day.",
                    "message_type": MessageType.TEXT,
                    "conversation_state": ConversationState.COLLECTING_DAY,
                    "booking_data": session["booking_data"],
                    "suggested_actions": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                    "requires_input": True
                }
            
            # Move to timeslot selection
            session["conversation_state"] = ConversationState.COLLECTING_TIMESLOT
            
            slot_options = [slot["display"] for slot in slots_result["available_slots"]]
            
            return {
                "message": f"Great! Here are the available {duration}-hour slots for {slots_result['date']}:",
                "message_type": MessageType.TIMESLOT_SELECTION,
                "conversation_state": ConversationState.COLLECTING_TIMESLOT,
                "booking_data": session["booking_data"],
                "available_slots": slots_result["available_slots"],
                "suggested_actions": slot_options,
                "requires_input": True
            }
            
        except Exception as e:
            self.logger.error(f"Error handling day selection: {str(e)}")
            return {
                "message": "Sorry, I encountered an error checking availability. Please try again.",
                "message_type": MessageType.ERROR,
                "conversation_state": ConversationState.COLLECTING_DAY,
                "booking_data": session["booking_data"],
                "suggested_actions": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                "requires_input": True
            }

    async def _handle_timeslot_selection(self, user_message: str, session_id: str, session: Dict[str, Any]) -> Dict[str, Any]:
        """Handle timeslot selection"""
        try:
            # Find the selected slot with more robust matching
            selected_slot = None
            user_input = user_message.strip()
            
            self.logger.info(f"Looking for timeslot: '{user_input}' in available slots: {[slot['display'] for slot in session['available_slots']]}")
            
            for slot in session["available_slots"]:
                slot_display = slot["display"]
                
                # Try exact match first
                if user_input == slot_display:
                    selected_slot = slot
                    break
                    
                # Try case-insensitive match
                if user_input.lower() == slot_display.lower():
                    selected_slot = slot
                    break
                    
                # Try substring match (user input contains slot or vice versa)
                if user_input in slot_display or slot_display in user_input:
                    selected_slot = slot
                    break
                    
                # Try matching just the time parts (remove spaces and compare)
                user_clean = user_input.replace(" ", "").upper()
                slot_clean = slot_display.replace(" ", "").upper()
                if user_clean == slot_clean:
                    selected_slot = slot
                    break
                    
                # Try matching start time only
                start_time = slot_display.split(" - ")[0]
                if user_input == start_time or user_input.lower() == start_time.lower():
                    selected_slot = slot
                    break
            
            if not selected_slot:
                self.logger.warning(f"Could not match timeslot '{user_input}' with available slots")
                return {
                    "message": "I couldn't find that time slot. Please select from the available options:",
                    "message_type": MessageType.TIMESLOT_SELECTION,
                    "conversation_state": ConversationState.COLLECTING_TIMESLOT,
                    "booking_data": session["booking_data"],
                    "available_slots": session["available_slots"],
                    "suggested_actions": [slot["display"] for slot in session["available_slots"]],
                    "requires_input": True
                }
            
            self.logger.info(f"Successfully matched timeslot: {selected_slot['display']}")
            
            # Store the selected slot
            session["booking_data"]["selected_slot"] = selected_slot
            session["booking_data"]["selected_time"] = selected_slot["display"]
            
            # Move to next state (location collection)
            next_state = ConversationState.COLLECTING_LOCATION
            session["conversation_state"] = next_state
            
            return {
                "message": f"Perfect! I've reserved {selected_slot['display']} on {session['booking_data']['booking_date']} for you. Now, where would you like the {session['booking_data']['job_type'].lower()} session to take place?",
                "message_type": MessageType.TEXT,
                "conversation_state": next_state,
                "booking_data": session["booking_data"],
                "suggested_actions": self._get_suggested_actions(next_state),
                "requires_input": True
            }
            
        except Exception as e:
            self.logger.error(f"Error handling timeslot selection: {str(e)}")
            return {
                "message": "Sorry, I encountered an error selecting the time slot. Please try again.",
                "message_type": MessageType.ERROR,
                "conversation_state": ConversationState.COLLECTING_TIMESLOT,
                "booking_data": session["booking_data"],
                "available_slots": session["available_slots"],
                "suggested_actions": [slot["display"] for slot in session["available_slots"]],
                "requires_input": True
            }

    async def _create_calendar_booking(self, session: Dict[str, Any]) -> bool:
        """Create the calendar booking when booking is completed"""
        try:
            if "selected_slot" in session["booking_data"]:
                booking_result = await self.calendar_service.create_booking(session["booking_data"])
                if booking_result["success"]:
                    session["booking_data"]["calendar_event"] = booking_result
                    self.logger.info(f"Calendar booking created: {booking_result.get('event_id')}")
                    return True
                else:
                    self.logger.error(f"Failed to create calendar booking: {booking_result.get('error')}")
            return False
        except Exception as e:
            self.logger.error(f"Error creating calendar booking: {str(e)}")
            return False

    def _determine_next_state(self, current_state: ConversationState, booking_data: Dict[str, Any]) -> ConversationState:
        """Determine the next conversation state based on current state and collected data"""
        
        state_flow = {
            ConversationState.GREETING: ConversationState.COLLECTING_CONTACT,  # Collect username first
            ConversationState.COLLECTING_CONTACT: ConversationState.COLLECTING_JOB_TYPE,
            ConversationState.COLLECTING_JOB_TYPE: ConversationState.COLLECTING_DURATION,
            ConversationState.COLLECTING_DURATION: ConversationState.COLLECTING_DAY,
            ConversationState.COLLECTING_DAY: ConversationState.COLLECTING_TIMESLOT,
            ConversationState.COLLECTING_TIMESLOT: ConversationState.COLLECTING_LOCATION,
            ConversationState.COLLECTING_LOCATION: ConversationState.COLLECTING_BUDGET,
            ConversationState.COLLECTING_BUDGET: ConversationState.CONFIRMING_DETAILS,
            ConversationState.CONFIRMING_DETAILS: ConversationState.COMPLETED
        }
        
        # Check if we have all required data for current state
        required_fields = {
            ConversationState.COLLECTING_CONTACT: ["contact_name"],  # Just username/name
            ConversationState.COLLECTING_JOB_TYPE: ["job_type"],
            ConversationState.COLLECTING_DURATION: ["duration"],
            ConversationState.COLLECTING_DAY: ["selected_day"],
            ConversationState.COLLECTING_TIMESLOT: ["selected_slot"],
            ConversationState.COLLECTING_LOCATION: ["location"],
            ConversationState.COLLECTING_BUDGET: ["budget"],
        }
        
        if current_state in required_fields:
            required = required_fields[current_state]
            if all(booking_data.get(field) for field in required):
                return state_flow.get(current_state, ConversationState.COMPLETED)
            else:
                return current_state  # Stay in same state until data is collected
        
        return state_flow.get(current_state, ConversationState.COMPLETED)

    def _get_suggested_actions(self, state: ConversationState) -> List[str]:
        """Get suggested actions based on current conversation state"""
        
        suggestions = {
            ConversationState.GREETING: ["Tell me about your job"],
            ConversationState.COLLECTING_CONTACT: ["What's your name?"],
            ConversationState.COLLECTING_JOB_TYPE: ["Photography", "Videography", "Audio", "Other"],
            ConversationState.COLLECTING_DURATION: ["2 hours", "4 hours", "8 hours", "Full day"],
            ConversationState.COLLECTING_DAY: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Today", "Tomorrow"],
            ConversationState.COLLECTING_TIMESLOT: [],  # Will be populated dynamically
            ConversationState.COLLECTING_LOCATION: ["Studio", "Outdoor", "Client's venue", "My location"],
            ConversationState.COLLECTING_BUDGET: ["Under $500", "$500-$1000", "$1000+", "Discuss later"],
            ConversationState.CONFIRMING_DETAILS: ["Confirm booking", "Make changes"],
            ConversationState.COMPLETED: ["Start new booking"]
        }
        
        return suggestions.get(state, [])

    def reset_session(self, session_id: str) -> bool:
        """Reset a conversation session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    def get_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data for a given session ID"""
        return self.sessions.get(session_id) 