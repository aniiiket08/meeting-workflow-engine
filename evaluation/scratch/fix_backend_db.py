# Fix backend/sql_app.db by applying all migrations manually via SQLAlchemy
# This is equivalent to running 'alembic upgrade head' but without the path issues.
import sys
sys.path.insert(0, "backend")

from app.db.base import Base
import app.db.models  # registers all models
from sqlalchemy import create_engine, text, inspect

DB_PATH = "backend/sql_app.db"
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})

# Create all tables from current models (safe: create_all is idempotent for existing tables)
Base.metadata.create_all(bind=engine)

# Verify
insp = inspect(engine)
cols = [c["name"] for c in insp.get_columns("users")]
print("users columns after fix:", cols)

tables = insp.get_table_names()
print("All tables:", tables)

# Re-seed users from seed script
from app.db.session import SessionLocal
from sqlalchemy.orm import Session

# Override the engine to point at backend/sql_app.db for this session
from sqlalchemy.orm import sessionmaker
BSession = sessionmaker(bind=engine)

from app.db.models.user import User, UserRole
from app.core.security import get_password_hash

SEED_USERS = [
    ("Chairman", "chairman", "chairman@university.com", UserRole.CHAIRMAN),
    ("Principal", "principal", "principal@university.com", UserRole.PRINCIPAL),
    ("HOD", "hod", "hod@university.com", UserRole.HOD),
    ("Teacher", "teacher", "teacher@university.com", UserRole.TEACHER),
    ("Aniket", "aniket", "aniket@university.com", UserRole.STUDENT),
    ("Sujal", "sujal", "sujal@university.com", UserRole.STUDENT),
    ("Viraj", "viraj", "viraj@university.com", UserRole.STUDENT),
    ("Sarvesh", "sarvesh", "sarvesh@university.com", UserRole.STUDENT),
]

SEED_PWD = "changeme"
hashed = get_password_hash(SEED_PWD)

with BSession() as db:
    created = 0
    for name, username, email, role in SEED_USERS:
        existing = db.query(User).filter(User.email == email).first()
        if not existing:
            db.add(User(name=name, username=username, email=email, hashed_password=hashed, role=role))
            created += 1
        elif not existing.username:
            existing.username = username
    db.commit()
    print(f"Seeded/updated {created} users")
    total = db.query(User).count()
    print(f"Total users in backend/sql_app.db: {total}")

    # Seed rooms
    from app.db.models.room import Room
    ROOMS = [
        ("Auditorium", 200, []),
        ("IoT Lab", 40, []),
        ("STEP Hall", 100, []),
        ("MB 104", 60, []),
    ]
    room_count = db.query(Room).count()
    if room_count == 0:
        for name, cap, equip in ROOMS:
            db.add(Room(name=name, capacity=cap, equipment=equip))
        db.commit()
        print(f"Seeded {len(ROOMS)} rooms")
    else:
        print(f"Rooms already seeded: {room_count}")

