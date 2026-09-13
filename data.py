from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import models

SQLALCHEMY_DATABASE_URL = "sqlite:///./cinema.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

db = SessionLocal()

print("Καθαρισμός προηγούμενων δεδομένων από τη βάση...")

# Διαγραφή με σειρά που σέβεται τα Foreign Keys (από τα "παιδιά" στους "γονείς")
db.query(models.Screening).delete()
db.query(models.ProgramStaff).delete()
db.query(models.ProgramProgrammer).delete()
db.query(models.Program).delete()
db.query(models.User).delete()
db.commit()

print("Ξεκινάει η εισαγωγή νέων δεδομένων...")

# 1. 5 ΧΡΗΣΤΕΣ (IDs: 1001 - 1005)
users_data = [
    {"id": 1001, "username": "programmer_1", "password": "123", "full_name": "Alice Programmer"},
    {"id": 1002, "username": "submitter_1", "password": "123", "full_name": "Bob Submitter (Strictly Submitter)"},
    {"id": 1003, "username": "staff_handler_1", "password": "123", "full_name": "Charlie Staff"},
    {"id": 1004, "username": "staff_handler_2", "password": "123", "full_name": "Diana Reviewer"},
    {"id": 1005, "username": "programmer_2", "password": "123", "full_name": "Evan Programmer"}
]
for u in users_data:
    db.add(models.User(**u))

# 2. 5 ΠΡΟΓΡΑΜΜΑΤΑ με διαφορετικές φάσεις (States)[cite: 9]
programs_data = [
    {"id": 1001, "name": "Athens Film Festival 2026", "description": "Submission phase active", "start_date": "2026-09-01", "end_date": "2026-09-10", "state": "SUBMISSION"},
    {"id": 1002, "name": "Sci-Fi Weeks", "description": "Review phase active", "start_date": "2026-10-01", "end_date": "2026-10-05", "state": "REVIEW"},
    {"id": 1003, "name": "Documentary Nights", "description": "Scheduling phase active", "start_date": "2026-11-01", "end_date": "2026-11-04", "state": "SCHEDULING"},
    {"id": 1004, "name": "Short Film Showcase", "description": "Decision phase active", "start_date": "2026-12-01", "end_date": "2026-12-03", "state": "DECISION"},
    {"id": 1005, "name": "Classic Retrospective", "description": "Newly created phase", "start_date": "2027-01-10", "end_date": "2027-01-15", "state": "CREATED"}
]
for p in programs_data:
    db.add(models.Program(**p))

# 3. PROGRAMMERS (Χωρίς επικάλυψη με τον Submitter για αποφυγή conflict of interest)[cite: 9]
prog_programmers_data = [
    {"id": 1001, "program_id": 1001, "user_id": 1001},
    {"id": 1002, "program_id": 1002, "user_id": 1005},
    {"id": 1003, "program_id": 1003, "user_id": 1001},
    {"id": 1004, "program_id": 1004, "user_id": 1005},
    {"id": 1005, "program_id": 1005, "user_id": 1001}
]
for pp in prog_programmers_data:
    db.add(models.ProgramProgrammer(**pp))

# 4. STAFF (Ανάθεση προσωπικού ανά πρόγραμμα)[cite: 9]
staff_data = [
    {"id": 1001, "program_id": 1001, "user_id": 1003},
    {"id": 1002, "program_id": 1002, "user_id": 1004},
    {"id": 1003, "program_id": 1003, "user_id": 1003},
    {"id": 1004, "program_id": 1004, "user_id": 1004},
    {"id": 1005, "program_id": 1005, "user_id": 1003}
]
for s in staff_data:
    db.add(models.ProgramStaff(**s))

# 5. SCREENINGS (Με επιλεκτικά παραδείγματα συμπληρωμένων πεδίων ανάλογα με το στάδιο)[cite: 9]
screenings_data = [
    {
        "id": 1001, "program_id": 1001, "submitter_id": 1002, "handler_id": None, "state": "SUBMITTED",
        "film_title": "Cosmic Voyage", "film_cast": "Actor A, Actor B", "film_genres": "Sci-Fi", 
        "film_duration": 120, "auditorium_name": "Hall 1"
        # Στάδιο SUBMITTED: Δεν έχει αξιολογήσεις, ώρες ή σημειώσεις ακόμα.
    },
    {
        "id": 1002, "program_id": 1002, "submitter_id": 1002, "handler_id": 1004, "state": "REVIEWED",
        "film_title": "City Lights Echo", "film_cast": "Actor C", "film_genres": "Drama", 
        "film_duration": 95, "auditorium_name": "Hall 2", 
        "review_score": 8.0, "review_comments": "Good pacing."
        # Στάδιο REVIEWED: Έχει βαθμολογία και σχόλια από το Staff, αλλά όχι ώρες/εγκρίσεις.
    },
    {
        "id": 1003, "program_id": 1003, "submitter_id": 1002, "handler_id": 1003, "state": "APPROVED",
        "film_title": "AI Revolution", "film_cast": "Actor D", "film_genres": "Documentary", 
        "film_duration": 110, "auditorium_name": "Hall 3", 
        "review_score": 9.0, "review_comments": "Excellent fit.",
        "approval_notes": "Approved conditionally, need to adjust sound levels." 
        # Στάδιο APPROVED: Έχει επιπλέον σημειώσεις έγκρισης (approval_notes).
    },
    {
        "id": 1004, "program_id": 1004, "submitter_id": 1002, "handler_id": 1004, "state": "SCHEDULED",
        "film_title": "Silent Forest", "film_cast": "Actor F", "film_genres": "Mystery", 
        "film_duration": 85, "auditorium_name": "Hall 1", 
        "review_score": 8.5, "review_comments": "Approved for schedule.",
        "start_time": "2026-12-01 18:00:00", "end_time": "2026-12-01 19:30:00"
        # Στάδιο SCHEDULED: Έχει κανονικά συμπληρωμένες τις ώρες έναρξης και λήξης.
    },
    {
        "id": 1005, "program_id": 1005, "submitter_id": 1002, "handler_id": None, "state": "CREATED",
        "film_title": "Last Laugh", "film_cast": "Actor G", "film_genres": "Comedy", 
        "film_duration": 90, "auditorium_name": "Hall 2"
        # Στάδιο CREATED: Αρχική κατάσταση, όλα τα υπόλοιπα πεδία παραμένουν κενά (NULL).
    }
]
for sc in screenings_data:
    db.add(models.Screening(**sc))

db.commit()
db.close()
print("Επιτυχής καθαρισμός και αρχικοποίηση δεδομένων με επιλεκτικά παραδείγματα!")