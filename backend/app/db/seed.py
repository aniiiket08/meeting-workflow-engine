import logging
from sqlalchemy.orm import Session

from app.config import settings
from app.core.logging import setup_logging
from app.core.security import get_password_hash
from app.db.base import Base
from app.db.models.audit import AuditLog
from app.db.models.room import Room
from app.db.models.user import User, UserRole
from app.db.session import SessionLocal, engine

logger = setup_logging()


def seed_database(db: Session) -> None:
    """Seed initial users, rooms, and audit entry.

    The seed password is read from the ``SEED_PASSWORD`` environment variable
    (see ``.env.example``). Production deployments MUST set a strong value;
    running with an empty value raises an error to avoid shipping predictable
    credentials.
    """
    Base.metadata.create_all(bind=engine)

    seed_password = settings.SEED_PASSWORD
    if not seed_password:
        raise ValueError(
            "SEED_PASSWORD is not set. Define it in your .env file before "
            "running the seed script (see .env.example)."
        )
    hashed_password = get_password_hash(seed_password)

    legacy_student = db.query(User).filter_by(username="student").first()
    if legacy_student and not db.query(User).filter_by(username="aniket").first():
        legacy_student.username = "aniket"

    users = [
        ("Chairman", "chairman", "chairman@university.com", UserRole.CHAIRMAN),
        ("Principal", "principal", "principal@university.com", UserRole.PRINCIPAL),
        ("HOD", "hod", "hod@university.com", UserRole.HOD),
        ("Teacher", "teacher", "teacher@university.com", UserRole.TEACHER),
        ("Aniket", "aniket", "aniket@university.com", UserRole.STUDENT),
        ("Sujal", "sujal", "sujal@university.com", UserRole.STUDENT),
        ("Viraj", "viraj", "viraj@university.com", UserRole.STUDENT),
        ("Sarvesh", "sarvesh", "sarvesh@university.com", UserRole.STUDENT),
    ]
    created_users = 0
    for name, username, email, role in users:
        user = (
            legacy_student
            if username == "aniket" and legacy_student and legacy_student.username == "aniket"
            else db.query(User).filter_by(username=username).first()
        )
        if user is None:
            user = User(
                name=name,
                username=username,
                email=email,
                role=role,
                hashed_password=hashed_password,
            )
            db.add(user)
            created_users += 1
        else:
            user.name = name
            user.email = email
            user.role = role
            user.hashed_password = hashed_password
    if created_users:
        logger.info("Seeded %d missing university users.", created_users)

    # Upsert rooms by name — idempotent; read from environment_data_service (Meeting_Room_Facilities.docx)
    from app.services.environment_parser import environment_data_service

    desired_rooms = environment_data_service.get_room_facilities()
    created_rooms = 0
    for spec in desired_rooms:
        room = db.query(Room).filter_by(name=spec["name"]).first()
        if room is None:
            db.add(Room(name=spec["name"], capacity=spec["capacity"], equipment=spec["equipment"]))
            created_rooms += 1
        else:
            room.capacity = spec["capacity"]
            room.equipment = spec["equipment"]
    if created_rooms:
        logger.info("Seeded %d new rooms.", created_rooms)
    else:
        logger.info("Rooms already present; updated capacity/equipment in place.")

    # Seed initial audit log entry
    if not db.query(AuditLog).first():
        audit = AuditLog(
            actor="system",
            action="seed",
            entity="database",
            details={"message": "Initial database seed completed"},
        )
        db.add(audit)

    db.commit()
    logger.info("Database seeding completed successfully.")


# Backwards-compatible alias for older callers.
seed_db = seed_database


if __name__ == "__main__":
    with SessionLocal() as db_session:
        seed_database(db_session)