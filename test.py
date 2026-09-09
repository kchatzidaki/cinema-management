from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

from main import app, get_db
import models

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_cinema.db"
engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    models.Base.metadata.create_all(bind=engine)
    yield
    models.Base.metadata.drop_all(bind=engine)

def test_create_program():
    response = client.post(
        "/programs/?user_id=1",
        json={
            "name": "Athens Film Festival 2026",
            "description": "A celebration of independent cinema",
            "start_date": "2026-09-01",
            "end_date": "2026-09-10"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["message"] == "Program created successfully"
    assert "program_id" in data

def test_program_unique_name():
    payload = {
        "name": "Unique Fest",
        "description": "Test desc",
        "start_date": "2026-10-01",
        "end_date": "2026-10-05"
    }
    res1 = client.post("/programs/?user_id=1", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/programs/?user_id=2", json=payload)
    assert res2.status_code == 400
    assert res2.json()["detail"] == "Program name must be unique."

def test_program_state_transition_flow():
    res = client.post("/programs/?user_id=1", json={
        "name": "Workflow Fest",
        "description": "Flow test",
        "start_date": "2026-11-01",
        "end_date": "2026-11-05"
    })
    prog_id = res.json()["program_id"]

    res_trans = client.patch(f"/programs/{prog_id}/state?target_state=SUBMISSION&current_user_id=1")
    assert res_trans.status_code == 200

    res_invalid = client.patch(f"/programs/{prog_id}/state?target_state=CREATED&current_user_id=1")
    assert res_invalid.status_code == 400

def test_staff_freeze_constraint():
    res = client.post("/programs/?user_id=1", json={
        "name": "Staff Fest",
        "description": "Staff test",
        "start_date": "2026-12-01",
        "end_date": "2026-12-05"
    })
    prog_id = res.json()["program_id"]

    res_staff = client.post(f"/programs/{prog_id}/staff/5?current_user_id=1")
    assert res_staff.status_code == 200

    client.patch(f"/programs/{prog_id}/state?target_state=SUBMISSION&current_user_id=1")
    client.patch(f"/programs/{prog_id}/state?target_state=ASSIGNMENT&current_user_id=1")

    res_staff_fail = client.post(f"/programs/{prog_id}/staff/6?current_user_id=1")
    assert res_staff_fail.status_code == 400

def test_full_screening_lifecycle_and_workflow():
    prog_res = client.post("/programs/?user_id=1", json={
        "name": "CineMaster Fest",
        "description": "Full lifecycle test",
        "start_date": "2026-06-01",
        "end_date": "2026-06-10"
    })
    prog_id = prog_res.json()["program_id"]

    client.post(f"/programs/{prog_id}/staff/3?current_user_id=1")
    client.patch(f"/programs/{prog_id}/state?target_state=SUBMISSION&current_user_id=1")

    screening_payload = {
        "program_id": prog_id,
        "film_title": "Sci-Fi Odyssey",
        "film_cast": "Actor A",
        "film_genres": "Sci-Fi",
        "film_duration": 110,
        "auditorium_name": "Main Hall"
    }
    scr_res = client.post("/screenings/?user_id=2", json=screening_payload)
    assert scr_res.status_code == 201
    scr_id = scr_res.json()["screening_id"]

    sub_res = client.post(f"/screenings/{scr_id}/submit?user_id=2")
    assert sub_res.status_code == 200

    client.patch(f"/programs/{prog_id}/state?target_state=ASSIGNMENT&current_user_id=1")

    assign_res = client.post(f"/screenings/{scr_id}/assign-handler/3?current_user_id=1")
    assert assign_res.status_code == 200

    client.patch(f"/programs/{prog_id}/state?target_state=REVIEW&current_user_id=1")

    review_res = client.post(f"/screenings/{scr_id}/review?user_id=3", json={
        "score": 9.5,
        "comments": "Masterpiece cinematography."
    })
    assert review_res.status_code == 200

    client.patch(f"/programs/{prog_id}/state?target_state=SCHEDULING&current_user_id=1")

    appr_res = client.post(f"/screenings/{scr_id}/approve?user_id=2", json={
        "conditional_notes": "Will fix audio."
    })
    assert appr_res.status_code == 200

    client.patch(f"/programs/{prog_id}/state?target_state=FINAL_SUBMISSION&current_user_id=1")
    client.patch(f"/programs/{prog_id}/state?target_state=DECISION&current_user_id=1")

    schedule_res = client.post(f"/screenings/{scr_id}/schedule?start_time=2026-06-02T18:00:00&end_time=2026-06-02T20:00:00&user_id=1")
    assert schedule_res.status_code == 200

def test_unauthorized_state_change_forbidden():
    res = client.post("/programs/?user_id=1", json={
        "name": "Security Fest",
        "description": "Permission test",
        "start_date": "2026-07-01",
        "end_date": "2026-07-05"
    })
    prog_id = res.json()["program_id"]

    res_forbidden = client.patch(f"/programs/{prog_id}/state?target_state=SUBMISSION&current_user_id=99")
    assert res_forbidden.status_code == 403
    assert res_forbidden.json()["detail"] == "Unauthorized."

def test_search_and_redaction_logic():
    res = client.post("/programs/?user_id=1", json={
        "name": "Hidden Indie Showcase",
        "description": "Secret films",
        "start_date": "2026-08-01",
        "end_date": "2026-08-03"
    })
    prog_id = res.json()["program_id"]

    search_visitor = client.get("/programs/search?name=Hidden")
    assert search_visitor.status_code == 200
    assert len(search_visitor.json()) == 0

    search_programmer = client.get("/programs/search?name=Hidden&user_id=1")
    assert search_programmer.status_code == 200
    assert len(search_programmer.json()) == 1
    assert search_programmer.json()[0]["name"] == "Hidden Indie Showcase"

def test_invalid_review_score_out_of_bounds():
    prog_res = client.post("/programs/?user_id=1", json={
        "name": "Score Fest",
        "description": "Score test",
        "start_date": "2026-10-01",
        "end_date": "2026-10-05"
    })
    prog_id = prog_res.json()["program_id"]

    client.post(f"/programs/{prog_id}/staff/3?current_user_id=1")
    client.patch(f"/programs/{prog_id}/state?target_state=SUBMISSION&current_user_id=1")

    scr_res = client.post("/screenings/?user_id=2", json={
        "program_id": prog_id,
        "film_title": "Bad Score Movie",
        "film_cast": "Actor X",
        "film_genres": "Drama",
        "film_duration": 90,
        "auditorium_name": "Hall 2"
    })
    scr_id = scr_res.json()["screening_id"]
    client.post(f"/screenings/{scr_id}/submit?user_id=2")
    
    client.patch(f"/programs/{prog_id}/state?target_state=ASSIGNMENT&current_user_id=1")
    client.post(f"/screenings/{scr_id}/assign-handler/3?current_user_id=1")
    client.patch(f"/programs/{prog_id}/state?target_state=REVIEW&current_user_id=1")

    bad_review = client.post(f"/screenings/{scr_id}/review?user_id=3", json={
        "score": 12.0,
        "comments": "Out of bounds score."
    })
    assert bad_review.status_code == 400

def test_screening_double_submission():
    prog_res = client.post("/programs/?user_id=1", json={
        "name": "Double Sub Fest",
        "description": "Double sub test",
        "start_date": "2026-11-01",
        "end_date": "2026-11-05"
    })
    prog_id = prog_res.json()["program_id"]
    client.patch(f"/programs/{prog_id}/state?target_state=SUBMISSION&current_user_id=1")

    scr_res = client.post("/screenings/?user_id=2", json={
        "program_id": prog_id,
        "film_title": "Double Film",
        "film_cast": "Actor Y",
        "film_genres": "Action",
        "film_duration": 100,
        "auditorium_name": "Hall 1"
    })
    scr_id = scr_res.json()["screening_id"]

    first_sub = client.post(f"/screenings/{scr_id}/submit?user_id=2")
    assert first_sub.status_code == 200

    second_sub = client.post(f"/screenings/{scr_id}/submit?user_id=2")
    assert second_sub.status_code == 400

def test_unauthorized_screening_approval():
    prog_res = client.post("/programs/?user_id=1", json={
        "name": "Approval Fest",
        "description": "Approval test",
        "start_date": "2026-12-01",
        "end_date": "2026-12-05"
    })
    prog_id = prog_res.json()["program_id"]
    client.post(f"/programs/{prog_id}/staff/3?current_user_id=1")
    client.patch(f"/programs/{prog_id}/state?target_state=SUBMISSION&current_user_id=1")

    scr_res = client.post("/screenings/?user_id=2", json={
        "program_id": prog_id,
        "film_title": "Approval Film",
        "film_cast": "Actor Z",
        "film_genres": "Comedy",
        "film_duration": 95,
        "auditorium_name": "Hall 3"
    })
    scr_id = scr_res.json()["screening_id"]
    client.post(f"/screenings/{scr_id}/submit?user_id=2")

    client.patch(f"/programs/{prog_id}/state?target_state=ASSIGNMENT&current_user_id=1")
    client.post(f"/screenings/{scr_id}/assign-handler/3?current_user_id=1")
    client.patch(f"/programs/{prog_id}/state?target_state=REVIEW&current_user_id=1")
    client.post(f"/screenings/{scr_id}/review?user_id=3", json={"score": 8.0, "comments": "Good"})
    client.patch(f"/programs/{prog_id}/state?target_state=SCHEDULING&current_user_id=1")

    unauthorized_appr = client.post(f"/screenings/{scr_id}/approve?user_id=99", json={"conditional_notes": "None"})
    assert unauthorized_appr.status_code == 403

def test_illegal_program_state_jump():
    prog_res = client.post("/programs/?user_id=1", json={
        "name": "Jump Fest",
        "description": "Illegal jump test",
        "start_date": "2027-01-01",
        "end_date": "2027-01-05"
    })
    prog_id = prog_res.json()["program_id"]

    jump_res = client.patch(f"/programs/{prog_id}/state?target_state=SCHEDULING&current_user_id=1")
    assert jump_res.status_code == 400

def test_invalid_schedule_time_window():
    prog_res = client.post("/programs/?user_id=1", json={
        "name": "Time Fest",
        "description": "Invalid time window test",
        "start_date": "2027-02-01",
        "end_date": "2027-02-05"
    })
    prog_id = prog_res.json()["program_id"]

    client.post(f"/programs/{prog_id}/staff/3?current_user_id=1")
    client.patch(f"/programs/{prog_id}/state?target_state=SUBMISSION&current_user_id=1")

    scr_res = client.post("/screenings/?user_id=2", json={
        "program_id": prog_id,
        "film_title": "Time Paradox",
        "film_cast": "Actor W",
        "film_genres": "Sci-Fi",
        "film_duration": 90,
        "auditorium_name": "Hall 4"
    })
    scr_id = scr_res.json()["screening_id"]
    client.post(f"/screenings/{scr_id}/submit?user_id=2")

    client.patch(f"/programs/{prog_id}/state?target_state=ASSIGNMENT&current_user_id=1")
    client.post(f"/screenings/{scr_id}/assign-handler/3?current_user_id=1")
    client.patch(f"/programs/{prog_id}/state?target_state=REVIEW&current_user_id=1")
    client.post(f"/screenings/{scr_id}/review?user_id=3", json={"score": 9.0, "comments": "Great"})
    client.patch(f"/programs/{prog_id}/state?target_state=SCHEDULING&current_user_id=1")
    client.post(f"/screenings/{scr_id}/approve?user_id=2", json={"conditional_notes": "None"})
    client.patch(f"/programs/{prog_id}/state?target_state=FINAL_SUBMISSION&current_user_id=1")
    client.patch(f"/programs/{prog_id}/state?target_state=DECISION&current_user_id=1")

    bad_schedule = client.post(f"/screenings/{scr_id}/schedule?start_time=2027-02-02T22:00:00&end_time=2027-02-02T20:00:00&user_id=1")
    assert bad_schedule.status_code == 400

# --- 8 ΝΕΑ ΠΡΟΣΘΕΤΑ ΤΕΣΤ ΓΙΑ ΤΑ 20/20 ---

def test_duplicate_staff_assignment():
    prog_res = client.post("/programs/?user_id=1", json={
        "name": "Staff Dup Fest", "description": "Desc", "start_date": "2027-03-01", "end_date": "2027-03-05"
    })
    prog_id = prog_res.json()["program_id"]
    
    res1 = client.post(f"/programs/{prog_id}/staff/10?current_user_id=1")
    assert res1.status_code == 200
    
    res2 = client.post(f"/programs/{prog_id}/staff/10?current_user_id=1")
    assert res2.status_code == 400

def test_unauthorized_staff_assignment():
    prog_res = client.post("/programs/?user_id=1", json={
        "name": "Unauthorized Staff Fest", "description": "Desc", "start_date": "2027-04-01", "end_date": "2027-04-05"
    })
    prog_id = prog_res.json()["program_id"]
    
    res = client.post(f"/programs/{prog_id}/staff/10?current_user_id=99")
    assert res.status_code == 403

def test_screening_creation_invalid_program_state():
    prog_res = client.post("/programs/?user_id=1", json={
        "name": "Wrong State Fest", "description": "Desc", "start_date": "2027-05-01", "end_date": "2027-05-05"
    })
    prog_id = prog_res.json()["program_id"]
    
    scr_res = client.post("/screenings/?user_id=2", json={
        "program_id": prog_id, "film_title": "Early Film", "film_cast": "Cast", "film_genres": "Drama", "film_duration": 90, "auditorium_name": "Hall 1"
    })
    # Ανάλογα με την υλοποίηση, δημιουργία επιτρέπεται ή όχι εκτός submission. Εδώ τσεκάρουμε αν αποτυγχάνει ή αν περνάει. 
    # Εφόσον το API σου ίσως επιτρέπει δημιουργία σε CREATED, αλλά όχι submit, ας δοκιμάσουμε το submit σε CREATED:
    sub_res = client.post(f"/screenings/{scr_res.json()['screening_id']}/submit?user_id=2")
    assert sub_res.status_code == 400

def test_review_by_unassigned_staff():
    prog_res = client.post("/programs/?user_id=1", json={
        "name": "Reviewer Fest", "description": "Desc", "start_date": "2027-06-01", "end_date": "2027-06-05"
    })
    prog_id = prog_res.json()["program_id"]
    client.post(f"/programs/{prog_id}/staff/3?current_user_id=1")
    client.patch(f"/programs/{prog_id}/state?target_state=SUBMISSION&current_user_id=1")

    scr_res = client.post("/screenings/?user_id=2", json={
        "program_id": prog_id, "film_title": "Film Review", "film_cast": "C", "film_genres": "Action", "film_duration": 100, "auditorium_name": "H1"
    })
    scr_id = scr_res.json()["screening_id"]
    client.post(f"/screenings/{scr_id}/submit?user_id=2")
    client.patch(f"/programs/{prog_id}/state?target_state=ASSIGNMENT&current_user_id=1")
    client.post(f"/screenings/{scr_id}/assign-handler/3?current_user_id=1")
    client.patch(f"/programs/{prog_id}/state?target_state=REVIEW&current_user_id=1")

    # Χρήστης 4 είναι staff αλλά ΔΕΝ είναι ο handler της προβολής
    bad_review = client.post(f"/screenings/{scr_id}/review?user_id=4", json={"score": 8.0, "comments": "Nice"})
    assert bad_review.status_code in [400, 403]

def test_review_by_non_staff_user():
    prog_res = client.post("/programs/?user_id=1", json={
        "name": "Non Staff Review Fest", "description": "Desc", "start_date": "2027-07-01", "end_date": "2027-07-05"
    })
    prog_id = prog_res.json()["program_id"]
    client.patch(f"/programs/{prog_id}/state?target_state=SUBMISSION&current_user_id=1")

    scr_res = client.post("/screenings/?user_id=2", json={
        "program_id": prog_id, "film_title": "Film X", "film_cast": "C", "film_genres": "Drama", "film_duration": 90, "auditorium_name": "H1"
    })
    scr_id = scr_res.json()["screening_id"]
    client.post(f"/screenings/{scr_id}/submit?user_id=2")
    client.patch(f"/programs/{prog_id}/state?target_state=ASSIGNMENT&current_user_id=1")
    client.patch(f"/programs/{prog_id}/state?target_state=REVIEW&current_user_id=1")

    review_res = client.post(f"/screenings/{scr_id}/review?user_id=99", json={"score": 7.0, "comments": "Okay"})
    assert review_res.status_code in [400, 403]

def test_approval_by_unassigned_handler():
    prog_res = client.post("/programs/?user_id=1", json={
        "name": "Approval Guard Fest", "description": "Desc", "start_date": "2027-08-01", "end_date": "2027-08-05"
    })
    prog_id = prog_res.json()["program_id"]
    client.post(f"/programs/{prog_id}/staff/3?current_user_id=1")
    client.patch(f"/programs/{prog_id}/state?target_state=SUBMISSION&current_user_id=1")

    scr_res = client.post("/screenings/?user_id=2", json={
        "program_id": prog_id, "film_title": "Film Appr", "film_cast": "C", "film_genres": "Drama", "film_duration": 90, "auditorium_name": "H1"
    })
    scr_id = scr_res.json()["screening_id"]
    client.post(f"/screenings/{scr_id}/submit?user_id=2")
    client.patch(f"/programs/{prog_id}/state?target_state=ASSIGNMENT&current_user_id=1")
    client.post(f"/screenings/{scr_id}/assign-handler/3?current_user_id=1")
    client.patch(f"/programs/{prog_id}/state?target_state=REVIEW&current_user_id=1")
    client.post(f"/screenings/{scr_id}/review?user_id=3", json={"score": 9.0, "comments": "Good"})
    client.patch(f"/programs/{prog_id}/state?target_state=SCHEDULING&current_user_id=1")

    # Χρήστης 3 είναι ο handler αλλά η έγκριση ίσως απαιτεί Programmer (χρήστης 1). Αν δοκιμάσει ο 3, πρέπει να αποτύχει ή να επιτρέπεται βάσει ρόλου.
    appr = client.post(f"/screenings/{scr_id}/approve?user_id=3", json={"conditional_notes": "None"})
    assert appr.status_code in [400, 403]

def test_schedule_screening_not_approved():
    prog_res = client.post("/programs/?user_id=1", json={
        "name": "Schedule Guard Fest", "description": "Desc", "start_date": "2027-09-01", "end_date": "2027-09-05"
    })
    prog_id = prog_res.json()["program_id"]
    client.patch(f"/programs/{prog_id}/state?target_state=SUBMISSION&current_user_id=1")

    scr_res = client.post("/screenings/?user_id=2", json={
        "program_id": prog_id, "film_title": "Unapproved Film", "film_cast": "C", "film_genres": "Drama", "film_duration": 90, "auditorium_name": "H1"
    })
    scr_id = scr_res.json()["screening_id"]
    client.post(f"/screenings/{scr_id}/submit?user_id=2")
    
    client.patch(f"/programs/{prog_id}/state?target_state=ASSIGNMENT&current_user_id=1")
    client.patch(f"/programs/{prog_id}/state?target_state=REVIEW&current_user_id=1")
    client.patch(f"/programs/{prog_id}/state?target_state=SCHEDULING&current_user_id=1")
    client.patch(f"/programs/{prog_id}/state?target_state=FINAL_SUBMISSION&current_user_id=1")
    client.patch(f"/programs/{prog_id}/state?target_state=DECISION&current_user_id=1")

    # Προσπάθεια scheduling χωρίς να έχει γίνει APPROVED
    sched = client.post(f"/screenings/{scr_id}/schedule?start_time=2027-09-02T18:00:00&end_time=2027-09-02T20:00:00&user_id=1")
    assert sched.status_code == 400

def test_program_state_rollback_forbidden():
    prog_res = client.post("/programs/?user_id=1", json={
        "name": "Rollback Fest", "description": "Desc", "start_date": "2027-10-01", "end_date": "2027-10-05"
    })
    prog_id = prog_res.json()["program_id"]
    client.patch(f"/programs/{prog_id}/state?target_state=SUBMISSION&current_user_id=1")
    client.patch(f"/programs/{prog_id}/state?target_state=ASSIGNMENT&current_user_id=1")

    # Προσπάθεια επαναφοράς σε προηγούμενη κατάσταση (SUBMISSION αντί για REVIEW)
    rollback = client.patch(f"/programs/{prog_id}/state?target_state=SUBMISSION&current_user_id=1")
    assert rollback.status_code == 400