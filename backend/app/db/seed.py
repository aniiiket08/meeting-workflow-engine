from sqlalchemy.orm import Session

from app.config import settings
from app.core.logging import setup_logging
from app.core.security import get_password_hash
from app.db.models.audit import AuditLog
from app.db.models.room import Room
from app.db.models.user import User, UserRole
from app.db.session import SessionLocal

logger = setup_logging()


def seed_database(db: Session) -> None:
    """Seed initial users, rooms, and audit entry.

    The seed password is read from the ``SEED_PASSWORD`` environment variable
    (see ``.env.example``). Running with an empty value raises an error to avoid
    creating users with predictable credentials.
    """
    seed_password = settings.SEED_PASSWORD
    if not seed_password:
        raise ValueError(
            "SEED_PASSWORD is not set. Define it in your .env file before "
            "running the seed script (see .env.example)."
        )
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
    preserved_users = 0
    hashed_password = None
    for name, username, email, role in users:
        matching_users = (
            db.query(User)
            .filter((User.username == username) | (User.email == email))
            .all()
        )
        if len(matching_users) > 1:
            raise ValueError(f"Conflicting seeded user identity for username {username!r}.")
        if matching_users:
            preserved_users += 1
            continue

        if hashed_password is None:
            hashed_password = get_password_hash(seed_password)
        db.add(
            User(
                name=name,
                username=username,
                email=email,
                role=role,
                hashed_password=hashed_password,
            )
        )
        created_users += 1
    if created_users:
        logger.info("Seeded %d missing university users.", created_users)
    if preserved_users:
        logger.info("Preserved %d existing university user records unchanged.", preserved_users)

    # Seed missing rooms only; existing room data may have been customized.
    from app.services.environment_parser import environment_data_service

    desired_rooms = environment_data_service.get_room_facilities()
    created_rooms = 0
    for spec in desired_rooms:
        room = db.query(Room).filter_by(name=spec["name"]).first()
        if room is None:
            db.add(Room(name=spec["name"], capacity=spec["capacity"], equipment=spec["equipment"]))
            created_rooms += 1
    if created_rooms:
        logger.info("Seeded %d new rooms.", created_rooms)
    else:
        logger.info("Rooms already present; existing room data was left unchanged.")

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