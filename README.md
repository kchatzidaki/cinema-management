# Cinema Management System (Backend)

Backend RESTful API developed for managing cinema seasons (programs), film screenings, staff assignments, reviews, approvals, and scheduling, adhering to strict role-based access control (RBAC) and lifecycle workflows.

## Technologies Used
- **Python 3.12+**
- **FastAPI** (RESTful API framework)
- **SQLAlchemy** (ORM & Database management)
- **SQLite / Relational Database**
- **Pytest** (For integration and unit testing)

---

## Project Structure
```text
cinema-management/
│
├── main.py             # FastAPI application, routing, and business logic
├── models.py           # SQLAlchemy database models (Program, Screening, User, etc.)
├── database.py         # Database session and connection setup
├── test.py             # Comprehensive test suite (20 integration tests)
├── requirements.txt    # Project Python dependencies
└── README.md           # Project documentation