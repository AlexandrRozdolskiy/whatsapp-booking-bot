import openai
from app.core.config import settings
from typing import Dict, List, Any
import json
import logging

class OpenAIService:
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.logger = logging.getLogger(__name__)

    async def generate_bot_response(
        self,
        user_message: str,
        conversation_context: List[Dict[str, str]],
        booking_state: str,
        booking_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        
        system_prompt = self._build_system_prompt(booking_state, booking_data)
        
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_context)
        messages.append({"role": "user", "content": user_message})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=200,
                tools=[{"type": "function", "function": self._get_booking_function_schema()}],
                tool_choice="auto"
            )
            
            return self._parse_openai_response(response)
            
        except Exception as e:
            self.logger.error(f"OpenAI API error: {str(e)}")
            return {
                "message": "Sorry, I'm having trouble processing your request. Please try again.",
                "action": "retry",
                "booking_data": None
            }

    def _build_system_prompt(self, booking_state: str, booking_data: Dict[str, Any] = None) -> str:
        # Get the user's actual name if available
        user_name = "the user"
        if booking_data and booking_data.get('contact_name'):
            user_name = booking_data['contact_name']
        
        base_prompt = f"""
        You are JobBot, a friendly and professional booking assistant for freelance jobs.
        Your goal is to collect booking information in a conversational, WhatsApp-like manner.
        
        Always be:
        - Friendly and conversational
        - Clear about what information you need
        - Patient with user corrections
        - Professional but not robotic
        
        IMPORTANT: Always use the user's actual name when available. The user's name is: {user_name}. Use this name in your responses, especially in confirmations. Never use generic terms like 'Client' or 'Test User' when you have their real name. If the user says to mock, skip, or just book, or if the user is not providing a required field, you MUST fill in any missing booking fields with reasonable test/mock values (using the user's actual name if available, otherwise 'Test User', 'test@email.com', '123-456-7890', 'Outdoor', '1000', '2 hours', today's date, etc.) and proceed to booking/confirmation without further prompting for missing details. Do not ask for the same information more than once. Your goal is to get to booking as quickly as possible.
        
        Current booking stage: {booking_state}
        """
        
        stage_prompts = {
            "collecting_job_type": "The user has provided their name. Now ask about the specific type of work they need (Photography, Videography, Audio, etc.). Do not greet them again.",
            "collecting_date": "Ask for the job date in DD/MM/YYYY format.",
            "collecting_duration": "Ask how many hours the job will take.",
            "collecting_location": "Ask for the job location/venue.",
            "collecting_budget": "Ask about their budget range.",
            "collecting_contact": "Ask for their name only (not phone/email).",
            "confirming_details": f"Show a summary of all booking details using {user_name}'s actual name and ask for confirmation. Be specific and personal."
        }
        
        return base_prompt + "\n" + stage_prompts.get(booking_state, "")

    def _get_booking_function_schema(self) -> Dict[str, Any]:
        return {
            "name": "update_booking_data",
            "description": "Update booking information based on user input",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_type": {
                        "type": "string",
                        "description": "Type of job (e.g., Photography, Videography, Audio)"
                    },
                    "date": {
                        "type": "string",
                        "description": "Job date in DD/MM/YYYY format"
                    },
                    "duration": {
                        "type": "string",
                        "description": "Duration in hours"
                    },
                    "location": {
                        "type": "string",
                        "description": "Job location or venue"
                    },
                    "budget": {
                        "type": "string",
                        "description": "Budget range"
                    },
                    "contact_name": {
                        "type": "string",
                        "description": "Client's full name"
                    },
                    "phone": {
                        "type": "string",
                        "description": "Client's phone number"
                    },
                    "email": {
                        "type": "string",
                        "description": "Client's email address"
                    }
                }
            }
        }

    def _parse_openai_response(self, response) -> Dict[str, Any]:
        try:
            message = response.choices[0].message
            
            # Check if tool was called
            if message.tool_calls:
                tool_call = message.tool_calls[0]
                function_args = json.loads(tool_call.function.arguments)
                
                return {
                    "message": message.content or "",
                    "action": "update_booking",
                    "booking_data": function_args
                }
            else:
                return {
                    "message": message.content or "",
                    "action": "continue",
                    "booking_data": None
                }
                
        except Exception as e:
            self.logger.error(f"Error parsing OpenAI response: {str(e)}")
            return {
                "message": "I didn't understand that. Could you please rephrase?",
                "action": "retry",
                "booking_data": None
            } 