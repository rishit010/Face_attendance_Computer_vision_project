"""
SQLModel database models.
"""

from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime


class UserRole(str, Enum):
    TEACHER = "teacher"
    STUDENT = "student"


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: str = Field(primary_key=True)
    name: str
    email: str = Field(unique=True, index=True)
    password_plain: str              # DUMMY — plaintext for dev
    role: UserRole
    roll_number: Optional[str] = None  # Students only

    # CV: path to stored face embedding (.npy file)
    face_embedding_path: Optional[str] = None
    # CV: path to enrolled face image
    face_image_path: Optional[str] = None
    # Whether face enrollment is complete
    face_enrolled: bool = False

    created_at: datetime = Field(default_factory=datetime.utcnow)
