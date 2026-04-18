"""
Database initialization and session management
Using SQLite via SQLModel for simplicity (swap to PostgreSQL in production)
"""

from sqlmodel import SQLModel, create_engine, Session
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite-specific
    echo=settings.DEBUG,
)


def init_db():
    """Create all tables and seed dummy data."""
    # Import all models so SQLModel registers them
    from app.models.user import User  # noqa: F401
    from app.models.otp import OTPRecord  # noqa: F401
    from app.models.session import AttendanceSession, AttendanceRecord  # noqa: F401
    SQLModel.metadata.create_all(engine)
    _seed_dummy_data()


def get_session():
    """FastAPI dependency — yields a DB session."""
    with Session(engine) as session:
        yield session


def _seed_dummy_data():
    """
    Seed dummy teacher and student accounts so the app runs
    without any manual setup.
    Passwords are stored in plain text here — DUMMY ONLY.
    """
    from sqlmodel import Session, select
    from app.models.user import User, UserRole

    with Session(engine) as session:
        # Check if already seeded
        existing = session.exec(select(User)).first()
        if existing:
            return

        dummy_users = [
            User(
                id="teacher-001",
                name="Prof. Sharma",
                email="teacher@muj.manipal.edu",
                password_plain="teacher123",
                role=UserRole.TEACHER,
            ),
            # Student portal login — shared account for onboarding kiosk
            User(
                id="student-portal",
                name="Student",
                email="student@muj.manipal.edu",
                password_plain="student123",
                role=UserRole.STUDENT,
            ),
        ]

        for user in dummy_users:
            session.add(user)
        session.commit()
        print("[DB] Seeded dummy users.")
