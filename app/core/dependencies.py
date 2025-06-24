from app.services.openai_service import OpenAIService
from app.services.zoho_mock import ZohoCRMMock
from app.services.bot_logic import BookingBotLogic
from app.services.booking_handler import BookingHandler
from app.services.google_calendar_service import GoogleCalendarService
from app.core.config import settings

# Singleton instances
_openai_service = None
_bot_logic = None

def get_openai_service() -> OpenAIService:
    """Dependency to get OpenAI service instance"""
    global _openai_service
    if _openai_service is None:
        _openai_service = OpenAIService()
    return _openai_service

def get_zoho_service() -> ZohoCRMMock:
    """Dependency to get Zoho CRM mock service instance"""
    return ZohoCRMMock()

def get_bot_logic() -> BookingBotLogic:
    """Dependency to get booking bot logic instance (singleton)"""
    global _bot_logic
    if _bot_logic is None:
        openai_service = get_openai_service()
        _bot_logic = BookingBotLogic(openai_service)
    return _bot_logic

def get_booking_handler() -> BookingHandler:
    """Get booking handler service instance"""
    return BookingHandler()

def get_calendar_service() -> GoogleCalendarService:
    """Get Google Calendar service instance"""
    return GoogleCalendarService() 