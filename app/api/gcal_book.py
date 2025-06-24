# app/services/google_calendar_oauth.py
import os
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging
import re

class GoogleCalendarOAuth:
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
                    raise FileNotFoundError(f"OAuth credentials file not found: {self.credentials_file}")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.SCOPES)
                creds = flow.run_local_server(port=8088)
            
            # Save the credentials for the next run
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        self.service = build('calendar', 'v3', credentials=creds)
        self.logger.info("✅ Google Calendar OAuth authentication successful")

    async def check_availability(self, date_str: str, duration_hours: int, start_hour: int = 9) -> Dict[str, Any]:
        """Check calendar availability for given date and duration"""
        try:
            # Parse date (DD/MM/YYYY format from user)
            day, month, year = date_str.split('/')
            start_date = datetime(int(year), int(month), int(day), start_hour, 0)
            end_date = start_date + timedelta(hours=duration_hours)
            
            # Check for conflicts
            time_min = start_date.isoformat() + 'Z'
            time_max = end_date.isoformat() + 'Z'
            
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            return {
                "available": len(events) == 0,
                "conflicts": len(events),
                "requested_time": {
                    "start": start_date.strftime('%d/%m/%Y %H:%M'),
                    "end": end_date.strftime('%d/%m/%Y %H:%M'),
                    "duration": f"{duration_hours} hours"
                },
                "existing_events": [
                    {
                        "summary": event.get('summary', 'Busy'),
                        "start": self._format_event_time(event['start']),
                        "end": self._format_event_time(event['end'])
                    }
                    for event in events
                ],
                "suggested_times": self._suggest_alternative_times(start_date, duration_hours) if events else []
            }
            
        except Exception as e:
            self.logger.error(f"Error checking availability: {str(e)}")
            return {
                "available": True, 
                "conflicts": 0, 
                "existing_events": [], 
                "suggested_times": [],
                "error": str(e)
            }

    async def create_booking_event(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a calendar event for the booking"""
        try:
            # Parse booking date and time
            day, month, year = booking_data['date'].split('/')
            start_hour = int(booking_data.get('start_time', '9'))  # Default 9 AM
            start_time = datetime(int(year), int(month), int(day), start_hour, 0)
            
            # Parse duration - handle both string and numeric formats
            duration_str = booking_data['duration']
            if isinstance(duration_str, str):
                if "full day" in duration_str.lower():
                    duration_hours = 8
                elif "half day" in duration_str.lower():
                    duration_hours = 4
                else:
                    # Extract first number from string
                    numbers = re.findall(r'\d+', duration_str)
                    duration_hours = int(numbers[0]) if numbers else 2
            else:
                duration_hours = int(duration_str)
            
            end_time = start_time + timedelta(hours=duration_hours)
            
            # Create event with detailed information
            event = {
                'summary': f"📸 {booking_data['job_type']} - {booking_data.get('contact_name', 'Client')}",
                'description': self._build_event_description(booking_data),
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'America/Toronto',  # Adjust to your timezone
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'America/Toronto',
                },
                'location': booking_data.get('location', ''),
                'attendees': self._build_attendees_list(booking_data),
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                        {'method': 'popup', 'minutes': 60},       # 1 hour before
                    ],
                },
                'colorId': '10',  # Green color for bookings
                'extendedProperties': {
                    'private': {
                        'booking_source': 'WhatsApp Bot',
                        'job_id': f"JOB_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        'budget': booking_data.get('budget', ''),
                        'phone': booking_data.get('phone', ''),
                        'booking_status': 'CONFIRMED'
                    }
                }
            }
            
            # Insert event into calendar
            created_event = self.service.events().insert(
                calendarId='primary',
                body=event,
                sendUpdates='all'  # Send email notifications to attendees
            ).execute()
            
            return {
                "success": True,
                "event_id": created_event['id'],
                "event_link": created_event.get('htmlLink'),
                "calendar_url": f"https://calendar.google.com/calendar/event?eid={created_event['id']}",
                "event_details": {
                    "summary": created_event['summary'],
                    "start": self._format_event_time(created_event['start']),
                    "end": self._format_event_time(created_event['end']),
                    "location": created_event.get('location', ''),
                    "attendees": len(created_event.get('attendees', [])),
                },
                "notifications": {
                    "email_sent": True,
                    "reminders_set": True,
                    "calendar_updated": True
                }
            }
            
        except HttpError as e:
            self.logger.error(f"Google Calendar API error: {str(e)}")
            return {
                "success": False,
                "error": f"Calendar booking failed: {str(e)}",
                "error_code": e.resp.status,
                "fallback": "manual_calendar_entry_required"
            }
        except Exception as e:
            self.logger.error(f"Unexpected error creating calendar event: {str(e)}")
            return {
                "success": False,
                "error": f"Booking creation failed: {str(e)}",
                "fallback": "manual_calendar_entry_required"
            }

    def _build_event_description(self, booking_data: Dict[str, Any]) -> str:
        """Build detailed event description"""
        job_id = f"JOB_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        return f"""
🤖 WHATSAPP BOOKING CONFIRMATION
{'='*40}

📋 JOB DETAILS:
   Type: {booking_data['job_type']}
   Duration: {booking_data['duration']} hours
   Budget: {booking_data.get('budget', 'Not specified')}
   Location: {booking_data.get('location', 'TBD')}

👤 CLIENT CONTACT:
   Name: {booking_data.get('contact_name', 'Not provided')}
   Phone: {booking_data.get('phone', 'Not provided')}
   Email: {booking_data.get('email', 'Not provided')}

📝 ADDITIONAL NOTES:
{booking_data.get('details', 'No additional details provided')}

🆔 BOOKING REFERENCE:
   Job ID: {job_id}
   Booked: {datetime.now().strftime('%d/%m/%Y at %H:%M')}
   Source: WhatsApp Bot
   Status: CONFIRMED

🔔 REMINDERS SET:
   • Email reminder 24 hours before
   • Popup reminder 1 hour before

📧 Next steps: Crew assignment in progress
        """.strip()

    def _build_attendees_list(self, booking_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Build attendees list for calendar event"""
        attendees = []
        
        if booking_data.get('email'):
            attendees.append({
                'email': booking_data['email'],
                'displayName': booking_data.get('contact_name', 'Client'),
                'responseStatus': 'needsAction'
            })
        
        return attendees

    def _format_event_time(self, time_data: Dict[str, str]) -> str:
        """Format event time for display"""
        if 'dateTime' in time_data:
            dt = datetime.fromisoformat(time_data['dateTime'].replace('Z', '+00:00'))
            return dt.strftime('%d/%m/%Y %H:%M')
        elif 'date' in time_data:
            return time_data['date']
        return 'Unknown time'

    def _suggest_alternative_times(self, requested_time: datetime, duration: int) -> List[Dict[str, str]]:
        """Suggest alternative times if requested slot is busy"""
        suggestions = []
        
        # Suggest times around the requested time
        for offset in [2, 4, -2]:  # +2h, +4h, -2h
            alt_time = requested_time + timedelta(hours=offset)
            
            # Only suggest business hours (8 AM to 6 PM)
            if 8 <= alt_time.hour <= 18:
                suggestions.append({
                    "time": alt_time.strftime('%H:%M'),
                    "date": alt_time.strftime('%d/%m/%Y'),
                    "display": alt_time.strftime('%d/%m/%Y at %H:%M'),
                    "datetime": alt_time.isoformat()
                })
        
        return suggestions[:3]  # Return max 3 suggestions

    async def get_upcoming_bookings(self, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """Get upcoming bookings for dashboard display"""
        try:
            now = datetime.now()
            time_min = now.isoformat() + 'Z'
            time_max = (now + timedelta(days=days_ahead)).isoformat() + 'Z'
            
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=10,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            bookings = []
            for event in events:
                # Check if this is a booking from our bot
                extended_props = event.get('extendedProperties', {}).get('private', {})
                is_bot_booking = extended_props.get('booking_source') == 'WhatsApp Bot'
                
                bookings.append({
                    "id": event['id'],
                    "summary": event.get('summary', 'Untitled Event'),
                    "start": self._format_event_time(event['start']),
                    "end": self._format_event_time(event['end']),
                    "location": event.get('location', ''),
                    "is_whatsapp_booking": is_bot_booking,
                    "job_id": extended_props.get('job_id', ''),
                    "status": extended_props.get('booking_status', 'UNKNOWN'),
                    "link": event.get('htmlLink', '')
                })
            
            return bookings
            
        except Exception as e:
            self.logger.error(f"Error fetching upcoming bookings: {str(e)}")
            return []

    def test_connection(self) -> Dict[str, Any]:
        """Test the calendar connection"""
        try:
            # Try to get calendar info
            calendar_info = self.service.calendars().get(calendarId='primary').execute()
            
            return {
                "success": True,
                "calendar_name": calendar_info.get('summary', 'Primary Calendar'),
                "calendar_id": calendar_info['id'],
                "timezone": calendar_info.get('timeZone', 'Unknown'),
                "message": "✅ Google Calendar connection successful!"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "❌ Google Calendar connection failed"
            }