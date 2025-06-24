from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from app.api import chat, booking, calendar
from app.core.config import settings
import uvicorn
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = FastAPI(
    title="WhatsApp JobBot PoC",
    description="AI-powered booking agent with WhatsApp-style interface",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Include API routers
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(booking.router, prefix="/api/v1/booking", tags=["booking"])
app.include_router(calendar.router, prefix="/api/v1/calendar", tags=["calendar"])

@app.get("/")
async def read_root(request: Request):
    """Main chat interface"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "service": "WhatsApp JobBot PoC",
        "version": "1.0.0"
    }

@app.get("/demo")
async def demo_page(request: Request):
    """Demo page with instructions"""
    return templates.TemplateResponse("demo.html", {"request": request})

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    ) 