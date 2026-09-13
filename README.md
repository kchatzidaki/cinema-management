# Cinema Management System (Backend)

Backend RESTful API developed in Python using FastAPI for managing cinema programs (seasons), film screenings, staff assignments, reviews, approvals, and scheduling, adhering to strict role-based access control (RBAC) and lifecycle workflows.

## Technologies Used

* **Python 3.12+**
* **FastAPI** (RESTful API framework)
* **SQLAlchemy** (ORM & Database management)
* **Pydantic** (Data validation & settings)
* **SQLite** (Relational Database)
* **Pytest** (For integration and unit testing)

## Project Structure

```text
cinema-management/
│
├── main.py             # FastAPI application, routing, and endpoints
├── models.py           # SQLAlchemy database models (User, Program, Screening, etc.)
├── schemas.py          # Pydantic validation and serialization schemas
├── auth.py             # Authentication, password hashing, and JWT/RBAC logic
├── database.py         # Database session and connection setup
├── data.py             # Data handling and initial seed/operations logic
├── test.py             # Comprehensive test suite (integration & unit tests)
├── cinema.db           # SQLite main database file
├── test_cinema.db      # SQLite test database file
├── docs/               # Documentation and system diagrams
│   ├── Activity Diagrams/
│   │   ├── AD - Assign Handler.png
│   │   ├── AD - Create Program.png
│   │   ├── AD - Review Screening.png
│   │   └── AD - Submit Screening.png
│   ├── Context Diagrams/
│   ├── Sequence Diagrams/
│   │   ├── SD - Authentication.png
│   │   ├── SD - Reject Screening.png
│   │   ├── SD - Search & View Screening.png
│   │   └── SD - User Log In.png
│   ├── Use Case Diagrams/
│   │   ├── Use Case Diagram - 1.png
│   │   ├── Use Case Diagram - 2.png
│   │   └── Use Case Diagram - 3.png
│   ├── Component Diagram.png
│   ├── ER Diagram.png
│   ├── Relational Model.png
│   └── 321202039_report.pdf
└── README.md           # Project documentation
```

## Key Features

* **Role-Based Access Control (RBAC):** Distinct permissions for Visitors, Users, Programmers, Staff, and Submitters.
* **Lifecycle Workflows:** Dynamic management of program states and film screening approvals.
* **Secure Authentication:** Token-based security and password hashing implemented in `auth.py`.
* **Automated Testing:** Robust testing framework using `pytest` to ensure API reliability.