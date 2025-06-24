from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class BookingData(BaseModel):
    job_type: Optional[str] = None
    date: Optional[str] = None
    duration: Optional[str] = None
    location: Optional[str] = None
    budget: Optional[str] = None
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    details: Optional[str] = None

class BookingConfirmation(BaseModel):
    booking_id: str
    status: str
    confirmation_message: str
    crm_data: Optional[Dict[str, Any]] = None
    job_dossier: Optional[str] = None

class BookingRequest(BaseModel):
    session_id: str
    booking_data: BookingData 