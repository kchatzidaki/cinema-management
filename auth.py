from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from database import get_db
import models

security = HTTPBasic()

# Συνάρτηση για την ανάκτηρη του τρέχοντος authenticated χρήστη μέσω HTTP Basic
def get_current_user(credentials: HTTPBasicCredentials = Depends(security), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == credentials.username).first()
    if not user or user.password != credentials.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Εσφαλμένα στοιχεία σύνδεσης (username ή password).",
            headers={"WWW-Authenticate": "Basic"},
        )
    return user

# Βοηθητική συνάρτηση για έλεγχο ρόλου ανά πρόγραμμα
def check_program_role(user_id: int, program_id: int, required_role: str, db: Session):
    role_entry = db.query(models.ProgramRole).filter(
        models.ProgramRole.user_id == user_id,
        models.ProgramRole.program_id == program_id,
        models.ProgramRole.role == required_role
    ).first()
    return role_entry is not None