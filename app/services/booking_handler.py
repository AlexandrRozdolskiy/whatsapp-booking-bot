from app.models.booking import BookingData, BookingConfirmation
from typing import Dict, Any, Optional
import logging
from datetime import datetime
from app.api.gcal_book import GoogleCalendarOAuth

class BookingHandler:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.gcal = GoogleCalendarOAuth()

    async def process_booking_confirmation(
        self,
        booking_data: Dict[str, Any],
        session_id: str
    ) -> BookingConfirmation:
        """Process a complete booking confirmation (Google Calendar only)"""
        try:
            # Validate booking data
            if not self._validate_booking_data(booking_data):
                return BookingConfirmation(
                    booking_id="",
                    status="INVALID_DATA",
                    confirmation_message="Please provide all required booking information.",
                    crm_data=None,
                    job_dossier=None
                )
            gcal_result = None
            gcal_error = None
            # Create real Google Calendar event
            try:
                gcal_result = await self.gcal.create_booking_event(booking_data)
            except Exception as e:
                gcal_error = str(e)
                self.logger.error(f"Google Calendar booking error: {gcal_error}")
            confirmation_message = self._generate_confirmation_message(booking_data, gcal_result)
            if gcal_result and gcal_result.get("success"):
                confirmation_message += f"\n\n📅 [View in Google Calendar]({gcal_result.get('event_link', '')})"
            elif gcal_error:
                confirmation_message += f"\n\n⚠️ Google Calendar booking failed: {gcal_error}"
            return BookingConfirmation(
                booking_id=gcal_result.get("event_id", "") if gcal_result else "",
                status="CONFIRMED" if gcal_result and gcal_result.get("success") else "ERROR",
                confirmation_message=confirmation_message,
                crm_data=gcal_result,
                job_dossier=None
            )
        except Exception as e:
            self.logger.error(f"Booking processing error: {str(e)}")
            return BookingConfirmation(
                booking_id="",
                status="ERROR",
                confirmation_message="An unexpected error occurred. Please try again or contact support.",
                crm_data=None,
                job_dossier=None
            )

    def _validate_booking_data(self, booking_data: Dict[str, Any]) -> bool:
        """Validate that all required booking fields are present"""
        required_fields = [
            "job_type", "date", "duration", "location", 
            "budget", "contact_name", "phone", "email"
        ]
        
        return all(booking_data.get(field) for field in required_fields)

    def _generate_confirmation_message(
        self,
        booking_data: Dict[str, Any],
        gcal_result: Dict[str, Any]
    ) -> str:
        """Generate a user-friendly confirmation message"""
        
        message = f"""
✅ **Booking Confirmed!**

Thank you for your booking, {booking_data.get('contact_name')}!

📋 **Booking Details:**
• Job Type: {booking_data.get('job_type')}
• Date: {booking_data.get('date')}
• Duration: {booking_data.get('duration')}
• Location: {booking_data.get('location')}
• Budget: {booking_data.get('budget')}

🆔 **Booking ID:** {gcal_result.get('event_id', 'N/A')}

📧 **Next Steps:**
1. You'll receive a confirmation email shortly
2. Our team will contact you within 24 hours
3. We'll send you a detailed quote and contract

📞 **Contact:** If you have any questions, call us at +1-555-0123

Thank you for choosing our services!
        """.strip()
        
        return message

    async def get_booking_summary(self, booking_id: str) -> Optional[Dict[str, Any]]:
        """Get booking summary by ID"""
        try:
            # In a real implementation, this would query the database
            # For now, we'll return a mock summary
            return {
                "booking_id": booking_id,
                "status": "CONFIRMED",
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error getting booking summary: {str(e)}")
            return None

    def format_booking_for_display(self, booking_data: Dict[str, Any]) -> str:
        """Format booking data for display in the UI"""
        
        summary = f"""
📋 **Booking Summary**

🎯 **Job Details:**
• Type: {booking_data.get('job_type', 'Not specified')}
• Date: {booking_data.get('date', 'Not specified')}
• Duration: {booking_data.get('duration', 'Not specified')}
• Location: {booking_data.get('location', 'Not specified')}
• Budget: {booking_data.get('budget', 'Not specified')}

👤 **Contact Information:**
• Name: {booking_data.get('contact_name', 'Not specified')}
• Phone: {booking_data.get('phone', 'Not specified')}
• Email: {booking_data.get('email', 'Not specified')}

📝 **Additional Notes:**
{booking_data.get('details', 'No additional notes provided')}
        """.strip()
        
        return summary 