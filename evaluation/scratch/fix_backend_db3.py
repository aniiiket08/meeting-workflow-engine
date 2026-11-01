import sys
sys.path.insert(0, "backend")

import sqlite3
from app.core.security import get_password_hash

DB_PATH = "backend/sql_app.db"
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("PRAGMA table_info(users)")
existing_cols = {row[1] for row in cur.fetchall()}
print("Existing columns:", sorted(existing_cols))

if "username" not in existing_cols:
    print("Adding 'username' column...")
    cur.execute("ALTER TABLE users ADD COLUMN username VARCHAR")

cur.execute("PRAGMA table_info(meetings)")
meeting_cols = {row[1] for row in cur.fetchall()}
for col, defn in [("max_attendees","INTEGER"),("equipment_needed","JSON"),("agenda_items_text","VARCHAR")]:
    if col not in meeting_cols:
        print(f"Adding meetings.{col}...")
        cur.execute(f"ALTER TABLE meetings ADD COLUMN {col} {defn}")

cur.execute("PRAGMA table_info(action_items)")
action_cols = {row[1] for row in cur.fetchall()}
for col, defn in [("owner_name","VARCHAR"),("owner_email","VARCHAR"),("source_timestamp","VARCHAR"),
                  ("needs_confirmation","BOOLEAN DEFAULT 0"),("status","VARCHAR DEFAULT 'pending'")]:
    if col not in action_cols:
        print(f"Adding action_items.{col}...")
        cur.execute(f"ALTER TABLE action_items ADD COLUMN {col} {defn}")

conn.commit()

hashed = get_password_hash("changeme")
SEED_USERS = [
    ("Chairman","chairman","chairman@university.com","chairman"),
    ("Principal","principal","principal@university.com","principal"),
    ("HOD","hod","hod@university.com","hod"),
    ("Teacher","teacher","teacher@university.com","teacher"),
    ("Aniket","aniket","aniket@university.com","student"),
    ("Sujal","sujal","sujal@university.com","student"),
    ("Viraj","viraj","viraj@university.com","student"),
    ("Sarvesh","sarvesh","sarvesh@university.com","student"),
]

cur.execute("SELECT email FROM users")
existing_emails = {r[0] for r in cur.fetchall()}
print("Pre-existing emails:", existing_emails)

for name, username, email, role in SEED_USERS:
    if email not in existing_emails:
        cur.execute("INSERT INTO users (name, username, email, hashed_password, role) VALUES (?,?,?,?,?)",
                    (name, username, email, hashed, role))
        print(f"Inserted user {email}")
    else:
        cur.execute("UPDATE users SET username=? WHERE email=?", (username, email))

cur.execute("SELECT COUNT(*) FROM rooms")
if cur.fetchone()[0] == 0:
    for name, cap in [("Auditorium",200),("IoT Lab",40),("STEP Hall",100),("MB 104",60)]:
        cur.execute("INSERT INTO rooms (name, capacity) VALUES (?,?)", (name, cap))
    print("Seeded 4 rooms")

conn.commit()
cur.execute("PRAGMA table_info(users)")
cols = [row[1] for row in cur.fetchall()]
print("Final users columns:", cols)
cur.execute("SELECT id, email, username, role FROM users")
for row in cur.fetchall():
    print(" ", row)
conn.close()
print("DONE")

