"""
Face Attendance System — FastAPI Backend
Main application entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.api import auth, sessions, attendance, students
from app.core.database import init_db
from app.core.config import settings

app = FastAPI(
    title="Face Attendance System",
    description="CV-powered attendance system with liveness detection and geofencing",
    version="1.0.0",
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount uploads directory for enrolled face images
os.makedirs("uploads/faces", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.on_event("startup")
async def startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


# Routers
app.include_router(auth.router,       prefix="/api/auth",       tags=["Auth"])
app.include_router(sessions.router,   prefix="/api/sessions",   tags=["Sessions"])
app.include_router(attendance.router, prefix="/api/attendance", tags=["Attendance"])
app.include_router(students.router,   prefix="/api/students",   tags=["Students"])
