from datetime import datetime
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)

class Program(Base):
    __tablename__ = "programs"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=False)
    start_date = Column(String, nullable=False)
    end_date = Column(String, nullable=False)
    state = Column(String, default="CREATED", nullable=False)
    creation_date = Column(DateTime, default=datetime.utcnow)

    # Relationships
    programmers = relationship("ProgramProgrammer", back_populates="program", cascade="all, delete-orphan")
    staff_members = relationship("ProgramStaff", back_populates="program", cascade="all, delete-orphan")
    screenings = relationship("Screening", back_populates="program", cascade="all, delete-orphan")

class ProgramProgrammer(Base):
    __tablename__ = "program_programmers"
    id = Column(Integer, primary_key=True, index=True)
    program_id = Column(Integer, ForeignKey("programs.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    program = relationship("Program", back_populates="programmers")
    user = relationship("User")

class ProgramStaff(Base):
    __tablename__ = "program_staff"
    id = Column(Integer, primary_key=True, index=True)
    program_id = Column(Integer, ForeignKey("programs.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    program = relationship("Program", back_populates="staff_members")
    user = relationship("User")

class Screening(Base):
    __tablename__ = "screenings"
    id = Column(Integer, primary_key=True, index=True)
    program_id = Column(Integer, ForeignKey("programs.id"), nullable=False)
    submitter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    handler_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    state = Column(String, default="CREATED", nullable=False)
    creation_date = Column(DateTime, default=datetime.utcnow)
    
    # Film info
    film_title = Column(String, nullable=False)
    film_cast = Column(String, nullable=False)
    film_genres = Column(String, nullable=False)
    film_duration = Column(Integer, nullable=False) # σε λεπτά
    
    # Auditorium info
    auditorium_name = Column(String, nullable=False)
    
    # Timetable
    start_time = Column(String, nullable=True)
    end_time = Column(String, nullable=True)
    
    # Review & Rejection details
    review_score = Column(Float, nullable=True)
    review_comments = Column(Text, nullable=True)
    approval_notes = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    program = relationship("Program", back_populates="screenings")
    submitter = relationship("User", foreign_keys=[submitter_id])
    handler = relationship("User", foreign_keys=[handler_id])