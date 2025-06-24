import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any
import logging

class ZohoCRMMock:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.mock_database = {
            "contacts": [],
            "calendar_events": [],
            "tasks": []
        }

    async def create_booking_workflow(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate complete Zoho CRM booking workflow"""
        
        try:
            # Step 1: Create Contact
            contact_result = await self._create_contact(booking_data)
            await asyncio.sleep(0.5)  # Simulate API delay
            
            # Step 2: Create Calendar Event
            event_result = await self._create_calendar_event(booking_data)
            await asyncio.sleep(0.3)
            
            # Step 3: Create Task for Diary Manager
            task_result = await self._create_task(booking_data)
            await asyncio.sleep(0.2)
            
            # Step 4: Generate Job Dossier
            job_dossier = self._generate_job_dossier(booking_data)
            
            return {
                "success": True,
                "job_id": event_result["id"],
                "contact": contact_result,
                "calendar_event": event_result,
                "task": task_result,
                "job_dossier": job_dossier,
                "crm_status": "BOOKING_CONFIRMED"
            }
            
        except Exception as e:
            self.logger.error(f"Zoho CRM workflow error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "fallback_action": "manual_booking_required"
            }

    async def _create_contact(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        contact = {
            "id": f"CONTACT_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "first_name": booking_data.get("contact_name", "").split()[0],
            "last_name": " ".join(booking_data.get("contact_name", "").split()[1:]),
            "phone": booking_data.get("phone"),
            "email": booking_data.get("email"),
            "lead_source": "WhatsApp Bot",
            "created_time": datetime.now().isoformat(),
            "owner": "JobBot System"
        }
        
        self.mock_database["contacts"].append(contact)
        return contact

    async def _create_calendar_event(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        # Parse date and create event
        try:
            job_date = datetime.strptime(booking_data.get("date", ""), "%d/%m/%Y")
        except:
            job_date = datetime.now() + timedelta(days=1)
        
        duration_hours = int(booking_data.get("duration", "2").split()[0])
        
        event = {
            "id": f"EVENT_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "subject": f"{booking_data.get('job_type', 'Job')} - {booking_data.get('contact_name', 'Client')}",
            "start_time": job_date.replace(hour=9, minute=0).isoformat(),
            "end_time": job_date.replace(hour=9 + duration_hours, minute=0).isoformat(),
            "location": booking_data.get("location", "TBD"),
            "description": f"Job Type: {booking_data.get('job_type')}\nDuration: {booking_data.get('duration')}\nBudget: {booking_data.get('budget')}\nContact: {booking_data.get('contact_name')}",
            "attendees": [booking_data.get("email", "")]
        }
        
        self.mock_database["calendar_events"].append(event)
        return event

    async def _create_task(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        task = {
            "id": f"TASK_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "subject": f"Process booking for {booking_data.get('contact_name', 'Client')}",
            "due_date": (datetime.now() + timedelta(hours=2)).isoformat(),
            "priority": self._calculate_priority(booking_data.get("date")),
            "status": "Open",
            "description": f"New booking received via WhatsApp Bot\nJob: {booking_data.get('job_type')}\nDate: {booking_data.get('date')}\nLocation: {booking_data.get('location')}",
            "assigned_to": "Diary Manager"
        }
        
        self.mock_database["tasks"].append(task)
        return task

    def _calculate_priority(self, date_str: str) -> str:
        """Calculate priority based on job date"""
        try:
            job_date = datetime.strptime(date_str, "%d/%m/%Y")
            days_until = (job_date - datetime.now()).days
            
            if days_until <= 1:
                return "High"
            elif days_until <= 3:
                return "Medium"
            else:
                return "Normal"
        except:
            return "Normal"

    def _generate_job_dossier(self, booking_data: Dict[str, Any]) -> str:
        priority = self._calculate_priority(booking_data.get("date"))
        
        dossier = f"""
🤖 JOB DOSSIER - {datetime.now().strftime('%d/%m/%Y %H:%M')}
{'='*50}

📋 JOB DETAILS:
   Type: {booking_data.get('job_type')}
   Date: {booking_data.get('date')}
   Duration: {booking_data.get('duration')} hours
   Location: {booking_data.get('location')}
   Budget: {booking_data.get('budget')}

👤 CLIENT CONTACT:
   Name: {booking_data.get('contact_name')}
   Phone: {booking_data.get('phone')}
   Email: {booking_data.get('email')}

⚡ BOOKING STATUS:
   Priority: {priority}
   CRM Status: CONFIRMED
   Crew Assignment: PENDING
   
📝 ADDITIONAL NOTES:
{booking_data.get('details', 'No additional details provided')}

🎯 NEXT ACTIONS:
   □ Assign suitable crew member
   □ Send confirmation to client
   □ Prepare equipment checklist
   □ Schedule pre-job briefing
        """.strip()
        
        return dossier

    def get_booking_analytics(self) -> Dict[str, Any]:
        """Generate booking analytics for dashboard"""
        analytics = {
            "total_bookings": len(self.mock_database["calendar_events"]),
            "total_contacts": len(self.mock_database["contacts"]),
            "pending_tasks": len([t for t in self.mock_database["tasks"] if t["status"] == "Open"]),
            "recent_bookings": len([e for e in self.mock_database["calendar_events"] 
                                  if datetime.fromisoformat(e["start_time"]) > datetime.now() - timedelta(days=7)])
        }
        
        return analytics 