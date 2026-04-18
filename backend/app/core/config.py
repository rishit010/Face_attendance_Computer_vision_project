"""
Configuration and settings for Face Attendance System
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Face Attendance System"
    DEBUG: bool = True

    # JWT (dummy secret for dev)
    JWT_SECRET: str = "DUMMY_SECRET_CHANGE_IN_PRODUCTION_PLEASE"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120

    # Database
    DATABASE_URL: str = "sqlite:///./attendance.db"

    # CV Pipeline
    FACE_SIMILARITY_THRESHOLD: float = 0.55   # Cosine similarity for ArcFace embeddings
    LIVENESS_THRESHOLD: float = 0.6           # Passive liveness model confidence
    SPOOF_REJECTION_THRESHOLD: float = 0.45   # Below this → definitely spoof

    # Geofence
    DEFAULT_ROOM_RADIUS_METERS: float = 20.0  # Default classroom radius

    # Liveness challenge
    CHALLENGE_TIMEOUT_SECONDS: int = 30
    LIVENESS_FRAME_COUNT: int = 5             # Frames to analyze for active challenge

    # SMTP — for sending OTP emails
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""         # e.g. yourapp@gmail.com
    SMTP_PASSWORD: str = ""     # App password (not your login password)
    SMTP_FROM_NAME: str = "Face Attendance System"
    SMTP_ENABLED: bool = False  # Set True + fill creds to send real emails

    class Config:
        env_file = ".env"


settings = Settings()
