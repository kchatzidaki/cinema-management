from fastapi import FastAPI, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker
from typing import Optional, List
import models, schemas

# --- Database Setup ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./cinema.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Cinema Management Backend", version="1.0.0")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Helper functions for Role & State Checks ---
def get_user_role(db: Session, program_id: int, user_id: int) -> str:
    prog = db.query(models.Program).filter(models.Program.id == program_id).first()
    if not prog:
        return "VISITOR"
    
    is_prog = db.query(models.ProgramProgrammer).filter_by(program_id=program_id, user_id=user_id).first()
    if is_prog:
        return "PROGRAMMER"
        
    is_staff = db.query(models.ProgramStaff).filter_by(program_id=program_id, user_id=user_id).first()
    if is_staff:
        return "STAFF"
        
    is_sub = db.query(models.Screening).filter_by(program_id=program_id, submitter_id=user_id).first()
    if is_sub:
        return "SUBMITTER"
        
    return "USER"

# ==========================================
# --- Program Management Endpoints ---
# ==========================================

@app.post("/programs/", status_code=status.HTTP_201_CREATED)
def create_program(program: schemas.ProgramCreate, user_id: int = Query(...), db: Session = Depends(get_db)):
    existing = db.query(models.Program).filter(models.Program.name == program.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Program name must be unique.")
    
    db_prog = models.Program(**program.dict(), state="CREATED")
    db.add(db_prog)
    db.commit()
    db.refresh(db_prog)
    
    # Ο δημιουργός γίνεται αυτόματα PROGRAMMER στο πρόγραμμα
    prog_link = models.ProgramProgrammer(program_id=db_prog.id, user_id=user_id)
    db.add(prog_link)
    db.commit()
    return {"message": "Program created successfully", "program_id": db_prog.id}

@app.post("/programs/{program_id}/programmers/{target_user_id}")
def add_programmer(program_id: int, target_user_id: int, current_user_id: int = Query(...), db: Session = Depends(get_db)):
    role = get_user_role(db, program_id, current_user_id)
    if role != "PROGRAMMER":
        raise HTTPException(status_code=403, detail="Only a PROGRAMMER can add other programmers.")
    
    exists = db.query(models.ProgramProgrammer).filter_by(program_id=program_id, user_id=target_user_id).first()
    if exists:
        raise HTTPException(status_code=400, detail="User is already a PROGRAMMER for this program.")
        
    db.add(models.ProgramProgrammer(program_id=program_id, user_id=target_user_id))
    db.commit()
    return {"message": "Programmer added successfully."}

@app.post("/programs/{program_id}/staff/{target_user_id}")
def add_staff(program_id: int, target_user_id: int, current_user_id: int = Query(...), db: Session = Depends(get_db)):
    prog = db.query(models.Program).filter_by(id=program_id).first()
    if not prog:
        raise HTTPException(status_code=404, detail="Program not found.")
    
    if prog.state not in ["CREATED", "SUBMISSION"]:
        raise HTTPException(status_code=400, detail="Staff set is frozen after submission phase.")
        
    role = get_user_role(db, program_id, current_user_id)
    if role != "PROGRAMMER":
        raise HTTPException(status_code=403, detail="Only a PROGRAMMER can add staff.")
        
    # --- ΠΡΟΣΘΕΣΕ ΑΥΤΟΝ ΤΟΝ ΕΛΕΓΧΟ ΕΔΩ ---
    existing = db.query(models.ProgramStaff).filter_by(program_id=program_id, user_id=target_user_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="User is already a staff member.")
    # ---------------------------------------

    db.add(models.ProgramStaff(program_id=program_id, user_id=target_user_id))
    db.commit()
    return {"message": "Staff member added successfully."}

@app.patch("/programs/{program_id}/state")
def update_program_state(program_id: int, target_state: str, current_user_id: int = Query(...), db: Session = Depends(get_db)):
    prog = db.query(models.Program).filter_by(id=program_id).first()
    if not prog:
        raise HTTPException(status_code=404, detail="Program not found.")
        
    role = get_user_role(db, program_id, current_user_id)
    if role != "PROGRAMMER":
        raise HTTPException(status_code=403, detail="Unauthorized.")
        
    valid_transitions = {
        "CREATED": "SUBMISSION",
        "SUBMISSION": "ASSIGNMENT",
        "ASSIGNMENT": "REVIEW",
        "REVIEW": "SCHEDULING",
        "SCHEDULING": "FINAL_SUBMISSION",
        "FINAL_SUBMISSION": "DECISION",
        "DECISION": "ANNOUNCED"
    }
    
    if valid_transitions.get(prog.state) != target_state:
        raise HTTPException(status_code=400, detail=f"Invalid state transition from {prog.state} to {target_state}.")
        
    prog.state = target_state
    db.commit()
    return {"message": f"Program state updated to {target_state}."}

# ==========================================
# --- Screening Management Endpoints ---
# ==========================================

@app.post("/screenings/", status_code=status.HTTP_201_CREATED)
def create_screening(screening: schemas.ScreeningCreate, user_id: int = Query(...), db: Session = Depends(get_db)):
    prog = db.query(models.Program).filter_by(id=screening.program_id).first()
    if not prog:
        raise HTTPException(status_code=404, detail="Program not found.")
        
    role = get_user_role(db, screening.program_id, user_id)
    if role == "PROGRAMMER":
        raise HTTPException(status_code=403, detail="Programmers cannot submit screenings in their own program.")
        
    db_screening = models.Screening(**screening.dict(), submitter_id=user_id, state="CREATED")
    db.add(db_screening)
    db.commit()
    db.refresh(db_screening)
    return {"message": "Screening created successfully", "screening_id": db_screening.id}

@app.post("/screenings/{screening_id}/submit")
def submit_screening(screening_id: int, user_id: int = Query(...), db: Session = Depends(get_db)):
    screening = db.query(models.Screening).filter_by(id=screening_id).first()
    if not screening:
        raise HTTPException(status_code=404, detail="Screening not found.")
        
    # --- ΠΡΟΣΘΕΣΕ ΑΥΤΟΝ ΤΟΝ ΕΛΕΓΧΟ ΕΔΩ ---
    if screening.state != "CREATED":
        raise HTTPException(status_code=400, detail="Screening has already been submitted.")
    # ---------------------------------------

    if screening.submitter_id != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized: Only the submitter can submit this screening.")
        
    prog = db.query(models.Program).filter_by(id=screening.program_id).first()
    if not prog:
        raise HTTPException(status_code=404, detail="Program not found.")
        
    if prog.state != "SUBMISSION":
        raise HTTPException(status_code=400, detail="Program is not in SUBMISSION state.")
        
    screening.state = "SUBMITTED"
    db.commit()
    return {"message": "Screening submitted successfully."}

@app.post("/screenings/{screening_id}/assign-handler/{handler_id}")
def assign_handler(screening_id: int, handler_id: int, current_user_id: int = Query(...), db: Session = Depends(get_db)):
    screening = db.query(models.Screening).filter_by(id=screening_id).first()
    if not screening:
        raise HTTPException(status_code=404, detail="Screening not found.")
        
    prog = db.query(models.Program).filter_by(id=screening.program_id).first()
    if not prog:
        raise HTTPException(status_code=404, detail="Program not found.")
    
    if prog.state != "ASSIGNMENT":
        raise HTTPException(status_code=400, detail="Program must be in ASSIGNMENT state.")
        
    if get_user_role(db, prog.id, current_user_id) != "PROGRAMMER":
        raise HTTPException(status_code=403, detail="Only programmers can assign handlers.")
        
    screening.handler_id = handler_id
    db.commit()
    return {"message": "Handler assigned successfully."}

@app.post("/screenings/{screening_id}/review")
def review_screening(screening_id: int, review: schemas.ScreeningReview, user_id: int = Query(...), db: Session = Depends(get_db)):
    # Έλεγχος εγκυρότητας βαθμολογίας (0 έως 10)
    if not (0 <= review.score <= 10):
        raise HTTPException(status_code=400, detail="Score must be between 0 and 10.")

    screening = db.query(models.Screening).filter_by(id=screening_id).first()
    if not screening:
        raise HTTPException(status_code=404, detail="Screening not found.")
        
    prog = db.query(models.Program).filter_by(id=screening.program_id).first()
    if not prog:
        raise HTTPException(status_code=404, detail="Program not found.")
    
    if prog.state != "REVIEW":
        raise HTTPException(status_code=400, detail="Program must be in REVIEW state.")
    if screening.handler_id != user_id:
        raise HTTPException(status_code=403, detail="Only the assigned staff handler can review this screening.")
        
    screening.review_score = review.score
    screening.review_comments = review.comments
    screening.state = "REVIEWED"
    db.commit()
    return {"message": "Screening reviewed successfully."}

@app.post("/screenings/{screening_id}/approve")
def approve_screening(screening_id: int, approval: schemas.ScreeningApproval, user_id: int = Query(...), db: Session = Depends(get_db)):
    screening = db.query(models.Screening).filter_by(id=screening_id).first()
    if not screening:
        raise HTTPException(status_code=404, detail="Screening not found.")
        
    prog = db.query(models.Program).filter_by(id=screening.program_id).first()
    if not prog:
        raise HTTPException(status_code=404, detail="Program not found.")
    
    if prog.state != "SCHEDULING":
        raise HTTPException(status_code=400, detail="Program must be in SCHEDULING state.")
    if screening.submitter_id != user_id:
        raise HTTPException(status_code=403, detail="Only the submitter can approve their screening.")
        
    screening.state = "APPROVED"
    screening.approval_notes = approval.conditional_notes
    db.commit()
    return {"message": "Screening approved successfully."}

@app.post("/screenings/{screening_id}/reject")
def reject_screening(screening_id: int, reason: str = Query(...), user_id: int = Query(...), db: Session = Depends(get_db)):
    screening = db.query(models.Screening).filter_by(id=screening_id).first()
    if not screening:
        raise HTTPException(status_code=404, detail="Screening not found.")
        
    prog = db.query(models.Program).filter_by(id=screening.program_id).first()
    if not prog:
        raise HTTPException(status_code=404, detail="Program not found.")
    
    if prog.state not in ["SCHEDULING", "DECISION"]:
        raise HTTPException(status_code=400, detail="Invalid program state for rejection.")
        
    role = get_user_role(db, prog.id, user_id)
    if role != "PROGRAMMER":
        raise HTTPException(status_code=403, detail="Only a programmer can reject screenings.")
        
    screening.state = "REJECTED"
    screening.rejection_reason = reason
    db.commit()
    return {"message": "Screening rejected successfully."}

from datetime import datetime  # Βεβαιώσου ότι το έχεις κάνει import στην αρχή του main.py

@app.post("/screenings/{screening_id}/schedule")
def schedule_screening(screening_id: int, start_time: str, end_time: str, user_id: int = Query(...), db: Session = Depends(get_db)):
    screening = db.query(models.Screening).filter_by(id=screening_id).first()
    if not screening:
        raise HTTPException(status_code=404, detail="Screening not found.")
        
    prog = db.query(models.Program).filter_by(id=screening.program_id).first()
    if not prog:
        raise HTTPException(status_code=404, detail="Program not found.")
    
    if prog.state != "DECISION":
        raise HTTPException(status_code=400, detail="Program must be in DECISION state for final scheduling.")
    if get_user_role(db, prog.id, user_id) != "PROGRAMMER":
        raise HTTPException(status_code=403, detail="Only a programmer can accept/schedule screenings.")
    if screening.state != "APPROVED":
        raise HTTPException(status_code=400, detail="Screening must be APPROVED to be scheduled.")
        
    # --- ΠΡΟΣΘΕΣΕ ΑΥΤΟΝ ΤΟΝ ΕΛΕΓΧΟ ΕΔΩ ---
    if datetime.fromisoformat(start_time) >= datetime.fromisoformat(end_time):
        raise HTTPException(status_code=400, detail="Start time must be before end time.")
    # ---------------------------------------

    screening.state = "SCHEDULED"
    screening.start_time = start_time
    screening.end_time = end_time
    db.commit()
    return {"message": "Screening scheduled successfully."}

# ==========================================
# --- Search Endpoints ---
# ==========================================

@app.get("/programs/search")
def search_programs(
    name: Optional[str] = None,
    description: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    film_title: Optional[str] = None,
    auditorium: Optional[str] = None,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Program)
    filters = []
    
    if name:
        filters.append(models.Program.name.ilike(f"%{name}%"))
    if description:
        filters.append(models.Program.description.ilike(f"%{description}%"))
    if start_date:
        filters.append(models.Program.start_date == start_date)
    if end_date:
        filters.append(models.Program.end_date == end_date)
        
    if film_title or auditorium:
        query = query.join(models.Screening)
        if film_title:
            filters.append(models.Screening.film_title.ilike(f"%{film_title}%"))
        if auditorium:
            filters.append(models.Screening.auditorium_name.ilike(f"%{auditorium}%"))
            
    if filters:
        query = query.filter(and_(*filters)) # AND semantics
        
    programs = query.order_by(models.Program.start_date, models.Program.name).all()
    
    results = []
    for p in programs:
        role = get_user_role(db, p.id, user_id) if user_id else "VISITOR"
        # Redaction: Visitors see only announced programs
        if role == "VISITOR" and p.state != "ANNOUNCED":
            continue
            
        results.append({
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "start_date": p.start_date,
            "end_date": p.end_date,
            "state": p.state
        })
        
    return results