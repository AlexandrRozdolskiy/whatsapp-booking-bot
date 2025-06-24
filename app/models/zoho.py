from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class ZohoContact(BaseModel):
    id: str
    first_name: str
    last_name: str
    phone: str
    email: str
    lead_source: str
    created_time: str
    owner: str

class ZohoCalendarEvent(BaseModel):
    id: str
    subject: str
    start_time: str
    end_time: str
    location: str
    description: str
    attendees: List[str]

class ZohoTask(BaseModel):
    id: str
    subject: str
    due_date: str
    priority: str
    status: str
    description: str
    assigned_to: str

class ZohoWorkflowResponse(BaseModel):
    success: bool
    job_id: Optional[str] = None
    contact: Optional[ZohoContact] = None
    calendar_event: Optional[ZohoCalendarEvent] = None
    task: Optional[ZohoTask] = None
    job_dossier: Optional[str] = None
    crm_status: Optional[str] = None
    error: Optional[str] = None
    fallback_action: Optional[str] = None 