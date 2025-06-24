import os
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging
import pytz

class GoogleCalendarService:
    def __init__(self, credentials_file='oauth-credentials.json', token_file='token.pickle'):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.SCOPES = ['https://www.googleapis.com/auth/calendar']
        self.logger = logging.getLogger(__name__)
        self.service = None
        self._authenticate()

    def _authenticate(self):
        """Authenticate and build Google Calendar service"""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    self.logger.warning(f"OAuth credentials file not found: {self.credentials_file}")
                    # For demo purposes, we'll simulate calendar functionality
                    self.service = None
                    return
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.SCOPES)
                creds = flow.run_local_server(port=8088)
            
            # Save the credentials for the next run
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        if creds:
            self.service = build('calendar', 'v3', credentials=creds)
            self.logger.info("✅ Google Calendar authentication successful")

    def _get_day_date(self, day_input: str) -> Optional[datetime]:
        """Convert day input to datetime object"""
        day_input = day_input.lower().strip()
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Handle specific days
        day_mappings = {
            'today': today,
            'tomorrow': today + timedelta(days=1),
            'monday': self._get_next_weekday(today, 0),
            'tuesday': self._get_next_weekday(today, 1),
            'wednesday': self._get_next_weekday(today, 2),
            'thursday': self._get_next_weekday(today, 3),
            'friday': self._get_next_weekday(today, 4),
            'saturday': self._get_next_weekday(today, 5),
            'sunday': self._get_next_weekday(today, 6),
        }
        
        if day_input in day_mappings:
            return day_mappings[day_input]
        
        # Try to parse as date (DD/MM/YYYY or DD-MM-YYYY)
        try:
            for date_format in ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']:
                try:
                    return datetime.strptime(day_input, date_format)
                except ValueError:
                    continue
        except:
            pass
        
        return None

    def _get_next_weekday(self, start_date: datetime, target_weekday: int) -> datetime:
        """Get the next occurrence of a specific weekday"""
        days_ahead = target_weekday - start_date.weekday()
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        return start_date + timedelta(days=days_ahead)

    async def get_available_slots(self, day_input: str, duration_hours: int = 2) -> Dict[str, Any]:
        """Get available time slots for a given day"""
        try:
            target_date = self._get_day_date(day_input)
            if not target_date:
                return {
                    "success": False,
                    "error": "Invalid day format. Please use 'Monday', 'Tuesday', etc., or DD/MM/YYYY format.",
                    "available_slots": []
                }

            # Define working hours (9 AM to 5 PM)
            start_hour = 9
            end_hour = 17
            slot_duration = duration_hours
            
            available_slots = []
            
            # If no Google Calendar service, return mock slots
            if not self.service:
                return self._get_mock_available_slots(target_date, start_hour, end_hour, slot_duration)
            
            # Check each potential slot
            for hour in range(start_hour, end_hour - slot_duration + 1):
                slot_start = target_date.replace(hour=hour, minute=0)
                slot_end = slot_start + timedelta(hours=slot_duration)
                
                # Check if slot is available
                if await self._is_slot_available(slot_start, slot_end):
                    available_slots.append({
                        "start_time": slot_start.strftime("%H:%M"),
                        "end_time": slot_end.strftime("%H:%M"),
                        "display": f"{slot_start.strftime('%I:%M %p')} - {slot_end.strftime('%I:%M %p')}",
                        "datetime": slot_start.isoformat()
                    })
            
            return {
                "success": True,
                "date": target_date.strftime("%A, %B %d, %Y"),
                "date_iso": target_date.strftime("%Y-%m-%d"),
                "available_slots": available_slots,
                "duration_hours": duration_hours
            }
            
        except Exception as e:
            self.logger.error(f"Error getting available slots: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "available_slots": []
            }

    def _get_mock_available_slots(self, target_date: datetime, start_hour: int, end_hour: int, slot_duration: int) -> Dict[str, Any]:
        """Generate mock available slots for demo purposes"""
        available_slots = []
        
        # Simulate some busy slots
        busy_hours = [12, 14] if target_date.weekday() < 5 else [10, 15]  # Different busy times for weekends
        
        for hour in range(start_hour, end_hour - slot_duration + 1):
            if hour not in busy_hours:
                slot_start = target_date.replace(hour=hour, minute=0)
                slot_end = slot_start + timedelta(hours=slot_duration)
                
                available_slots.append({
                    "start_time": slot_start.strftime("%H:%M"),
                    "end_time": slot_end.strftime("%H:%M"),
                    "display": f"{slot_start.strftime('%I:%M %p')} - {slot_end.strftime('%I:%M %p')}",
                    "datetime": slot_start.isoformat()
                })
        
        return {
            "success": True,
            "date": target_date.strftime("%A, %B %d, %Y"),
            "date_iso": target_date.strftime("%Y-%m-%d"),
            "available_slots": available_slots,
            "duration_hours": slot_duration,
            "mock_mode": True
        }

    async def _is_slot_available(self, start_time: datetime, end_time: datetime) -> bool:
        """Check if a time slot is available in Google Calendar"""
        try:
            # Convert to timezone-aware datetime for proper comparison
            local_tz = pytz.timezone('America/Toronto')
            
            # If datetime is naive, localize it
            if start_time.tzinfo is None:
                start_time = local_tz.localize(start_time)
            if end_time.tzinfo is None:
                end_time = local_tz.localize(end_time)
            
            # Convert to UTC for API query
            start_utc = start_time.astimezone(pytz.UTC)
            end_utc = end_time.astimezone(pytz.UTC)
            
            # Query for events that might overlap with our slot
            # We need to check a broader range to catch overlapping events
            query_start = (start_utc - timedelta(hours=12)).isoformat()
            query_end = (end_utc + timedelta(hours=12)).isoformat()
            
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=query_start,
                timeMax=query_end,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Check each event for overlap with our requested slot
            for event in events:
                event_start_str = event['start'].get('dateTime', event['start'].get('date'))
                event_end_str = event['end'].get('dateTime', event['end'].get('date'))
                
                # Skip all-day events (they don't have 'dateTime')
                if 'dateTime' not in event['start']:
                    continue
                
                # Parse event times
                try:
                    from dateutil import parser
                    event_start = parser.parse(event_start_str)
                    event_end = parser.parse(event_end_str)
                    
                    # Check for overlap: events overlap if one starts before the other ends
                    # and the other starts before the first one ends
                    # We add a small buffer (1 minute) to avoid back-to-back bookings
                    buffer_minutes = 1
                    slot_start_buffered = start_utc - timedelta(minutes=buffer_minutes)
                    slot_end_buffered = end_utc + timedelta(minutes=buffer_minutes)
                    
                    if (event_start < slot_end_buffered and event_end > slot_start_buffered):
                        self.logger.info(f"Slot {start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')} conflicts with event: {event.get('summary', 'No title')} ({event_start_str} - {event_end_str})")
                        return False
                        
                except Exception as e:
                    self.logger.error(f"Error parsing event time: {e}")
                    continue
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking slot availability: {str(e)}")
            return True  # Default to available if check fails

    async def create_booking(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a calendar event for the booking"""
        try:
            # Parse the selected slot datetime
            slot_datetime = datetime.fromisoformat(booking_data['selected_slot']['datetime'])
            
            # Use parsed duration_hours if available, otherwise parse duration string
            duration_hours = booking_data.get('duration_hours')
            if not duration_hours:
                duration_str = booking_data.get('duration', '2')
                if isinstance(duration_str, str):
                    if "full day" in duration_str.lower():
                        duration_hours = 8
                    elif "half day" in duration_str.lower():
                        duration_hours = 4
                    else:
                        import re
                        numbers = re.findall(r'\d+', duration_str)
                        duration_hours = int(numbers[0]) if numbers else 2
                else:
                    duration_hours = int(duration_str)
            
            end_datetime = slot_datetime + timedelta(hours=duration_hours)
            
            if not self.service:
                return self._create_mock_booking(booking_data, slot_datetime, end_datetime)
            
            # Create event
            event = {
                'summary': f"📸 {booking_data['job_type']} - {booking_data.get('contact_name', 'Client')}",
                'description': self._build_event_description(booking_data),
                'start': {
                    'dateTime': slot_datetime.isoformat(),
                    'timeZone': 'America/Toronto',
                },
                'end': {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': 'America/Toronto',
                },
                'location': booking_data.get('location', ''),
                'attendees': self._build_attendees_list(booking_data),
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},
                        {'method': 'popup', 'minutes': 60},
                    ],
                },
                'colorId': '10',
            }
            
            created_event = self.service.events().insert(
                calendarId='primary',
                body=event,
                sendUpdates='all'
            ).execute()
            
            return {
                "success": True,
                "event_id": created_event['id'],
                "event_link": created_event.get('htmlLink'),
                "event_details": {
                    "summary": created_event['summary'],
                    "start": slot_datetime.strftime('%A, %B %d at %I:%M %p'),
                    "end": end_datetime.strftime('%I:%M %p'),
                    "location": created_event.get('location', ''),
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error creating booking: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def _create_mock_booking(self, booking_data: Dict[str, Any], start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Create a mock booking for demo purposes"""
        return {
            "success": True,
            "event_id": f"mock_event_{start_time.strftime('%Y%m%d%H%M')}",
            "event_link": "https://calendar.google.com/calendar/mock",
            "event_details": {
                "summary": f"📸 {booking_data['job_type']} - {booking_data.get('contact_name', 'Client')}",
                "start": start_time.strftime('%A, %B %d at %I:%M %p'),
                "end": end_time.strftime('%I:%M %p'),
                "location": booking_data.get('location', ''),
            },
            "mock_mode": True
        }

    def _build_event_description(self, booking_data: Dict[str, Any]) -> str:
        """Build detailed event description"""
        return f"""
🤖 WHATSAPP BOOKING CONFIRMATION
{'='*40}

📋 JOB DETAILS:
   Type: {booking_data['job_type']}
   Duration: {booking_data.get('duration', 2)} hours
   Budget: {booking_data.get('budget', 'Not specified')}
   Location: {booking_data.get('location', 'TBD')}

👤 CLIENT CONTACT:
   Name: {booking_data.get('contact_name', 'Not provided')}
   Phone: {booking_data.get('phone', 'Not provided')}
   Email: {booking_data.get('email', 'Not provided')}

🕒 BOOKING TIME:
   Selected Slot: {booking_data.get('selected_slot', {}).get('display', 'N/A')}
   
📝 ADDITIONAL NOTES:
   Booked via WhatsApp AI Assistant
   Job ID: JOB_{datetime.now().strftime('%Y%m%d%H%M%S')}
        """.strip()

    def _build_attendees_list(self, booking_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Build attendees list for the event"""
        attendees = []
        if booking_data.get('email'):
            attendees.append({
                'email': booking_data['email'],
                'displayName': booking_data.get('contact_name', 'Client')
            })
        return attendees 