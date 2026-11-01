# Apply missing migration to backend/sql_app.db via raw SQLite
import sqlite3
from app.core.security import get_password_hash

DB_PATH = "backend/sql_app.db"
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Check what columns exist
cur.execute("PRAGMA table_info(users)")
existing_cols = {row[1] for row in cur.fetchall()}
print("Existing columns:", existing_cols)

# Add username column if missing (migration 005_username)
if "username" not in existing_cols:
    print("Adding 'username' column to users...")
    cur.execute("ALTER TABLE users ADD COLUMN username VARCHAR")
    conn.commit()
    print("Done.")

# Verify
cur.execute("PRAGMA table_info(users)")
cols = [row[1] for row in cur.fetchall()]
print("After fix:", cols)

# Check other missing columns from later migrations (010, 011, 012, 013)
cur.execute("PRAGMA table_info(meetings)")
meeting_cols = {row[1] for row in cur.fetchall()}
print("meetings columns:", meeting_cols)

cur.execute("PRAGMA table_info(action_items)")
action_cols = {row[1] for row in cur.fetchall()}
print("action_items columns:", action_cols)

# Apply meeting column additions if missing (migrations 010, 013)
for col, defn in [
    ("max_attendees", "INTEGER"),
    ("equipment_needed", "JSON"),
    ("agenda_items_text", "VARCHAR"),
]:
    if col not in meeting_cols:
        print(f"Adding meetings.{col}...")
        cur.execute(f"ALTER TABLE meetings ADD COLUMN {col} {defn}")

# Apply action_items column additions if missing (011, 012, 013)
for col, defn in [
    ("owner_name", "VARCHAR"),
    ("owner_email", "VARCHAR"),
    ("source_timestamp", "VARCHAR"),
    ("needs_confirmation", "BOOLEAN DEFAULT 0"),
    ("status", "VARCHAR DEFAULT 'pending'"),
]:
    if col not in action_cols:
        print(f"Adding action_items.{col}...")
        cur.execute(f"ALTER TABLE action_items ADD COLUMN {col} {defn}")

conn.commit()

# Now seed the university users
SEED_PWD = "changeme"
hashed = get_password_hash(SEED_PWD)

SEED_USERS = [
    ("Chairman", "chairman", "chairman@university.com", "chairman"),
    ("Principal", "principal", "principal@university.com", "principal"),
    ("HOD", "hod", "hod@university.com", "hod"),
    ("Teacher", "teacher", "teacher@university.com", "teacher"),
    ("Aniket", "aniket", "aniket@university.com", "student"),
    ("Sujal", "sujal", "sujal@university.com", "student"),
    ("Viraj", "viraj", "viraj@university.com", "student"),
    ("Sarvesh", "sarvesh", "sarvesh@university.com", "student"),
]

cur.execute("SELECT email FROM users")
existing_emails = {r[0] for r in cur.fetchall()}
print("Existing emails:", existing_emails)

inserted = 0
for name, username, email, role in SEED_USERS:
    if email not in existing_emails:
        cur.execute(
            "INSERT INTO users (name, username, email, hashed_password, role) VALUES (?, ?, ?, ?, ?)",
            (name, username, email, hashed, role),
        )
        inserted += 1
    else:
        cur.execute("UPDATE users SET username=? WHERE email=?", (username, email))

# Seed rooms
cur.execute("SELECT COUNT(*) FROM rooms")
room_count = cur.fetchone()[0]
ROOMS = [("Auditorium", 200), ("IoT Lab", 40), ("STEP Hall", 100), ("MB 104", 60)]
if room_count == 0:
    for name, cap in ROOMS:
        cur.execute("INSERT INTO rooms (name, capacity) VALUES (?, ?)", (name, cap))
    print(f"Seeded {len(ROOMS)} rooms")

conn.commit()
conn.close()
print(f"Done. Inserted {inserted} new users.")
print("backend/sql_app.db is now ready.")

