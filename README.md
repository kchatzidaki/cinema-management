# Cinema Management System (Backend)

Backend RESTful API developed in Python using FastAPI for managing cinema seasons (programs), film screenings, staff assignments, reviews, approvals, and scheduling, adhering to strict role-based access control (RBAC) and lifecycle workflows.

## Technologies Used

* **Python 3.12+**
* **FastAPI** (RESTful API framework)
* **SQLAlchemy** (ORM & Database management)
* **Pydantic** (Data validation & settings)
* **SQLite** (Relational Database)
* **Pytest** (For integration and unit testing)

## Project Structure

```text```
cinema-management/
│
├── main.py             # FastAPI application, routing, and endpoints
├── models.py           # SQLAlchemy database models (User, Program, Screening, etc.)
├── schemas.py          # Pydantic validation and serialization schemas
├── auth.py             # Authentication, password hashing, and JWT/RBAC logic
├── database.py         # Database session and connection setup
├── test.py             # Comprehensive test suite (integration & unit tests)
├── requirements.txt    # Project Python dependencies
└── README.md           # Project documentation

## Key Features

* **Role-Based Access Control (RBAC):** Distinct permissions for Visitors, Artists, Staff, and Organizers.
* **Lifecycle Workflows:** Dynamic management of program states and film screening approvals.
* **Secure Authentication:** Token-based security and password hashing implemented in `auth.py`.
* **Automated Testing:** Robust testing framework using `pytest` to ensure API reliability.