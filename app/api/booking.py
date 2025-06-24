from fastapi import APIRouter, HTTPException, Query
from app.models.booking import BookingRequest, BookingConfirmation, BookingData
from app.services.booking_handler import BookingHandler
from app.services.openai_service import OpenAIService
import logging
from datetime import datetime
from app.api.gcal_book import GoogleCalendarOAuth

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/confirm", response_model=BookingConfirmation)
async def confirm_booking(
    booking_request: BookingRequest
):
    """Confirm a booking and create it in Google Calendar"""
    try:
        booking_handler = BookingHandler()
        # Process the booking confirmation
        confirmation = await booking_handler.process_booking_confirmation(
            booking_data=booking_request.booking_data.dict(),
            session_id=booking_request.session_id
        )
        return confirmation
    except Exception as e:
        logger.error(f"Booking confirmation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to confirm booking")

@router.post("/ai/booking")
async def ai_booking_batch(booking_data: BookingData):
    """Send all booking data to OpenAI in one batch and return the AI's response."""
    try:
        openai_service = OpenAIService()
        # Compose a single prompt with all booking data
        prompt = f"""
        Here is a booking request. Please review, validate, and summarize it. If any fields are missing or look invalid, suggest corrections. Otherwise, confirm the booking details in a friendly, professional tone.
        
        Booking Data:
        Job Type: {booking_data.job_type}
        Date: {booking_data.date}
        Duration: {booking_data.duration}
        Location: {booking_data.location}
        Budget: {booking_data.budget}
        Contact Name: {booking_data.contact_name}
        Phone: {booking_data.phone}
        Email: {booking_data.email}
        Details: {booking_data.details}
        """
        ai_response = openai_service.client.chat.completions.create(
            model=openai_service.model,
            messages=[{"role": "system", "content": prompt}],
            temperature=0.7,
            max_tokens=300
        )
        message = ai_response.choices[0].message.content
        return {"message": message}
    except Exception as e:
        logger.error(f"AI batch booking error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process booking with AI")

@router.get("/summary/{booking_id}")
async def get_booking_summary(
    booking_id: str
):
    """Get booking summary by ID"""
    try:
        booking_handler = BookingHandler()
        summary = await booking_handler.get_booking_summary(booking_id)
        
        if summary:
            return summary
        else:
            raise HTTPException(status_code=404, detail="Booking not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get booking summary error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get booking summary")

@router.get("/analytics")
async def get_booking_analytics():
    """Get booking analytics and statistics"""
    try:
        # This endpoint is removed as per the instructions
        raise HTTPException(status_code=404, detail="Analytics endpoint not available")
    except Exception as e:
        logger.error(f"Get analytics error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get analytics")

@router.post("/format-summary")
async def format_booking_summary(booking_data: dict):
    """Format booking data for display"""
    try:
        booking_handler = BookingHandler()
        
        formatted_summary = booking_handler.format_booking_for_display(booking_data)
        
        return {
            "formatted_summary": formatted_summary,
            "booking_data": booking_data
        }
        
    except Exception as e:
        logger.error(f"Format summary error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to format booking summary")

@router.post("/book-test", response_model=BookingConfirmation)
async def book_test_meeting():
    """Immediately book a test meeting for today at 6pm with mock data."""
    try:
        booking_handler = BookingHandler()
        today = datetime.now().strftime("%d/%m/%Y")
        booking_data = {
            "job_type": "Test Meeting",
            "date": today,
            "duration": "1",
            "location": "Test Location",
            "budget": "100",
            "contact_name": "Test Client",
            "phone": "123-456-7890",
            "email": "test@email.com",
            "details": "This is a test booking.",
            "start_time": "18"
        }
        confirmation = await booking_handler.process_booking_confirmation(
            booking_data=booking_data,
            session_id="test-session"
        )
        return confirmation
    except Exception as e:
        logger.error(f"Book test meeting error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to book test meeting")

@router.get("/available-slots")
async def get_available_slots(date: str = Query(..., description="Date in DD/MM/YYYY format or day of week")):
    """Return available 1-hour slots for the given date or day of week from Google Calendar."""
    try:
        gcal = GoogleCalendarOAuth()
        # If input is a day of week, convert to next date
        import datetime as dt
        weekdays = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
        today = dt.datetime.now()
        date_str = date.strip().lower()
        if date_str in weekdays:
            days_ahead = (weekdays.index(date_str) - today.weekday() + 7) % 7
            target_date = today + dt.timedelta(days=days_ahead)
            date_str = target_date.strftime("%d/%m/%Y")
        else:
            target_date = dt.datetime.strptime(date, "%d/%m/%Y")
        # Check each hour from 9 to 17
        available = []
        for hour in range(9, 17):
            slot_start = target_date.replace(hour=hour, minute=0, second=0, microsecond=0)
            slot_end = slot_start + dt.timedelta(hours=1)
            result = await gcal.check_availability(date_str, 1, start_hour=hour)
            if result["available"]:
                available.append(f"{hour}:00")
        return {"date": date_str, "available_slots": available}
    except Exception as e:
        logger.error(f"Get available slots error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get available slots") 