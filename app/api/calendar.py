from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
from app.services.google_calendar_service import GoogleCalendarService
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class AvailableSlotsRequest(BaseModel):
    day: str
    duration_hours: int = 2

class AvailableSlotsResponse(BaseModel):
    success: bool
    date: Optional[str] = None
    date_iso: Optional[str] = None
    available_slots: List[Dict[str, str]] = []
    duration_hours: int = 2
    error: Optional[str] = None
    mock_mode: Optional[bool] = False

class BookingRequest(BaseModel):
    booking_data: Dict[str, Any]

class BookingResponse(BaseModel):
    success: bool
    event_id: Optional[str] = None
    event_link: Optional[str] = None
    event_details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    mock_mode: Optional[bool] = False

def get_calendar_service():
    """Dependency to get Google Calendar service"""
    return GoogleCalendarService()

@router.post("/available-slots", response_model=AvailableSlotsResponse)
async def get_available_slots(
    request: AvailableSlotsRequest,
    calendar_service: GoogleCalendarService = Depends(get_calendar_service)
):
    """Get available time slots for a given day"""
    try:
        logger.info(f"Getting available slots for day: {request.day}, duration: {request.duration_hours}h")
        
        result = await calendar_service.get_available_slots(
            day_input=request.day,
            duration_hours=request.duration_hours
        )
        
        return AvailableSlotsResponse(**result)
        
    except Exception as e:
        logger.error(f"Error getting available slots: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/book", response_model=BookingResponse)
async def create_booking(
    request: BookingRequest,
    calendar_service: GoogleCalendarService = Depends(get_calendar_service)
):
    """Create a calendar booking"""
    try:
        logger.info(f"Creating booking for: {request.booking_data.get('contact_name', 'Unknown')}")
        
        result = await calendar_service.create_booking(request.booking_data)
        
        return BookingResponse(**result)
        
    except Exception as e:
        logger.error(f"Error creating booking: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def calendar_health_check():
    """Health check for calendar service"""
    try:
        calendar_service = GoogleCalendarService()
        return {
            "status": "healthy",
            "service_available": calendar_service.service is not None,
            "mock_mode": calendar_service.service is None
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        } 