# Examination Management System (EMS)

A comprehensive web application for managing academic examinations, viva voce assessments, dynamic examiner slot scheduling, rubric-based evaluations, and automated scorecard generation.

Built strictly in compliance with the **Modern Application Development 1 (MAD-1)** Project Specification.

---

## 🔑 Quick Login Credentials (For Testing & Evaluation)

You can log in to the system at **[http://127.0.0.1:5000/login](http://127.0.0.1:5000/login)** using either **Username or Email** with the following accounts:

| Role | Name / ID | Username | Email | Password | Status & Testing Notes |
|---|---|---|---|---|---|
| **Administrator** | System Admin | `admin` | `admin@examportal.edu` | `AdminPassword@123` | **Pre-existing**. Full system access: courses, exams, rubrics, open/close toggles, examiner approval, rescheduling, and analytics charts. |
| **Examiner** | Dr. Anita Roy (`EXM-001`) | `anita_roy` | `anita.roy@faculty.edu` | `Examiner@123` | **Approved**. CS Faculty. Has created slots and completed rubric evaluations. |
| **Examiner** | Prof. Vikram Mehta (`EXM-002`) | `vikram_mehta` | `vikram.mehta@faculty.edu` | `Examiner@123` | **Approved**. Data Science Faculty. Has created slots open for student booking. |
| **Examiner** | Dr. Priya Nair (`EXM-003`) | `priya_nair` | `priya.nair@faculty.edu` | `Examiner@123` | **Approved**. Software Engineering Faculty. Available to create new slots. |
| **Examiner** | Dr. Suresh Kumar (`EXM-004`) | `suresh_kumar` | `suresh.kumar@faculty.edu` | `Examiner@123` | **Pending Approval**. Shows "Registration Under Review" screen to test Admin approval workflow. |
| **Student** | Rahul Sharma (`21F1000101`) | `rahul_s` | `rahul.s@student.edu` | `Student@123` | **Completed Exam**. Has published results and rubric remarks; can **view and download official PDF scorecard**. |
| **Student** | Ananya Iyer (`21F1000202`) | `ananya_i` | `ananya.i@student.edu` | `Student@123` | **Active Booking**. Has a confirmed slot; test booking schedule and cancellation before deadline. |
| **Student** | Rohit Verma (`21F1000303`) | `rohit_v` | `rohit.v@student.edu` | `Student@123` | **Active Booking**. Booked for ML Practical viva; test duplicate booking prevention. |

---

## 🌟 Key Features Implemented

### 1. Authentication & Role-Based Access Control (RBAC)
- **Unified Login System**: Single sign-in portal supporting Admin, Examiner, and Student accounts.
- **Admin Pre-existence**: Pre-configured in the database (no Admin registration permitted).
- **Self-Registration**:
  - **Students**: Self-register and immediately browse and book available slots.
  - **Examiners**: Self-register with Examiner ID and Department; account remains in `Pending` status until approved by an Administrator.
- **Access Guard**: Flask-Login role decorators (`@admin_required`, `@examiner_required`, `@student_required`) protect all controllers and REST endpoints.

### 2. Admin Functionalities
- **Comprehensive Dashboard**:
  - Displays total courses, total examinations, total examiners, total students, total slots, and total bookings.
  - Visual analytics with Chart.js:
    - *Booking Status & Completion Rate* (Doughnut chart)
    - *Examiner Workload: Slots vs Bookings* (Grouped Bar chart)
  - Quick overview of recent bookings and upcoming exam slots.
- **Course Management**: Full CRUD (Create, Read, Update, Delete) for academic courses and credits.
- **Examination Management**:
  - Create and configure exams (viva, practical, project presentation), duration, total marks, and date.
  - Assign or reassign primary examiners.
  - **Slot Creation Toggle**: Open or close examiner slot creation with a single click.
  - **Student Booking Toggle**: Open or close student slot booking with a single click.
- **Rubrics Management**: Add, edit, or delete multi-criteria assessment rubrics with real-time total marks validation.
- **Examiner Approvals**: Approve or reject pending examiner self-registrations with one click.
- **Slots & Assignment Control**: View all scheduled slots across all examinations and reassign slots to different approved examiners.
- **Bookings & Rescheduling**:
  - View all student bookings with status filtering.
  - Reschedule any student's booking to another available slot with remaining capacity.
- **Search System**: Live and query-based search for students, examiners, and examinations.
- **Historical Examination Archives**: Longitudinal audit view of past exams, evaluated scores, average performance, and scorecard records.

### 3. Examiner Functionalities
- **Examiner Portal**:
  - Displays assigned examinations, created examination slots, number of students booked, and pending evaluations.
- **Slot Creation**:
  - Examiners can create examination slots **only during open slot creation periods**.
  - Configure date, start/end time, maximum student capacity, and physical/virtual venue.
- **Update Slots Before Booking Starts**:
  - Examiners can edit or delete their slots before students book them (capacity/time adjustments). Once booked, slots are locked for student consistency.
- **Booked Students**: View the list of all candidates scheduled into their slots.
- **Rubric-Based Evaluation**:
  - Strict rule enforced: Examiners can evaluate **only students booked into their own slots**.
  - Multi-criterion scoring with maximum score bounds, criteria comments, and overall examiner qualitative feedback.
- **Submit Marks & Result Publication**: Instant calculation of total marks and percentage, with email notification dispatch to the student.

### 4. Student Functionalities
- **Student Dashboard**:
  - View available examinations, upcoming bookings, active booked slots, and published results.
- **Search & Browse Examinations**: Catalog search by course code, title, or department.
- **Slot Booking**:
  - Book slots during open booking windows.
  - **Duplicate Booking Prevention**: Disallows multiple bookings for the same examination.
  - **Anti-Overbooking**: Enforces slot capacity and automatically closes slots once full.
- **Cancel Booking Before Deadline**:
  - Cancel active bookings before slot start time; automatically releases capacity back to the slot.
- **Complete Booking History**:
  - Permanent audit record maintained for every student (Booked, Cancelled, Completed, Rescheduled).
- **Examination Schedule**: Visual timeline of all upcoming confirmed examination appointments.
- **View Evaluation Remarks & Scorecard**:
  - Review detailed rubric marks breakdown and examiner feedback.
- **Downloadable Examination Scorecard**:
  - Official digitally formatted PDF scorecard (`%PDF-1.4`) with student details, rubric marks table, totals, grade, and verification seal.
- **Edit Profile**: Update student name, department, contact number, and password.

### 5. Notifications & RESTful APIs
- **Email Notifications**:
  - Automated dispatch for booking confirmations, cancellations, administrative rescheduling, and results publication.
  - In-app Notification Center / Email Dispatch Center allows users to review all sent notices.
- **RESTful JSON API**:
  - `GET /api/v1/examinations`: List examinations and details.
  - `GET /api/v1/examinations/<id>`: Single exam with rubrics and slots.
  - `GET /api/v1/examiners`: Approved examiners.
  - `GET /api/v1/students`: Student directory (Admin).
  - `GET /api/v1/bookings`: Role-filtered bookings.
  - `POST /api/v1/bookings`: Book slot via JSON.
  - `GET /api/v1/stats`: Summary statistics for charts.

---

## 🏗️ Architecture & Technology Stack

- **Backend**: Python 3.12, Flask, Flask-SQLAlchemy, Flask-Login, Werkzeug
- **Database**: SQLite3 (`instance/ems.sqlite3`)
- **Frontend**: Clean and responsive UI using **Bootstrap 5.3** (strictly no other CSS framework) & Bootstrap Icons
- **Visualizations**: Chart.js for statistics
- **PDF Generation**: Native standard PDF 1.4 scorecard builder (pure Python standard library, zero external binary dependency)

---

## 📁 Project Structure

```
MAD_1 project/
├── application/
│   ├── __init__.py           # Flask App Factory & extension setup
│   ├── config.py             # App configurations
│   ├── models.py             # Database models (User, Examiner, Student, Course, Exam, Rubric, Slot, Booking)
│   ├── controllers/
│   │   ├── auth.py           # Authentication & Registration
│   │   ├── admin.py          # Admin management, CRUD, approvals, toggles, reschedule
│   │   ├── examiner.py       # Examiner portal, slots, rubric evaluations
│   │   ├── student.py        # Student portal, booking, cancellations, scorecards
│   │   ├── api.py            # RESTful JSON APIs
│   │   └── notifications.py  # Notification center
│   ├── utils/
│   │   ├── auth_decorators.py# Role-based access control (@admin_required, etc.)
│   │   ├── email_service.py  # Email dispatch & Notification logger
│   │   └── pdf_generator.py  # Standard PDF 1.4 scorecard engine
│   ├── templates/            # Bootstrap 5 templates
│   │   ├── base.html
│   │   ├── auth/
│   │   ├── admin/
│   │   ├── examiner/
│   │   ├── student/
│   │   └── notifications/
│   └── static/
│       ├── css/style.css
│       └── js/
│           ├── main.js       # HTML5 form validation & client search
│           └── charts.js     # Chart.js visualizations
├── instance/                 # SQLite database storage
├── app.py                    # Application runner
├── seed_data.py              # Initial database population script
├── test_system.py            # Automated test suite (9 test cases)
├── requirements.txt          # Python dependencies
└── README.md
```

---

## 🚀 How to Run the Project

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Populate Database with Initial Data
```bash
python seed_data.py
```

### 3. Run the Application
```bash
python app.py
```
Open your web browser and navigate to:
**http://127.0.0.1:5000**

---

## 🔑 Default Login Credentials

| Role | Name / ID | Username | Email | Password | Role Description & Testing Capabilities |
|---|---|---|---|---|---|
| **Admin** | System Admin | `admin` | `admin@examportal.edu` | `AdminPassword@123` | **Pre-existing**. Full system access: courses, exams, rubrics, open/close toggles, examiner approval, rescheduling, and analytics charts. |
| **Examiner** | Dr. Anita Roy (`EXM-001`) | `anita_roy` | `anita.roy@faculty.edu` | `Examiner@123` | **Approved**. CS Faculty. Has created slots and completed rubric evaluations. |
| **Examiner** | Prof. Vikram Mehta (`EXM-002`) | `vikram_mehta` | `vikram.mehta@faculty.edu` | `Examiner@123` | **Approved**. Data Science Faculty. Has created slots open for student booking. |
| **Examiner** | Dr. Priya Nair (`EXM-003`) | `priya_nair` | `priya.nair@faculty.edu` | `Examiner@123` | **Approved**. Software Engineering Faculty. Available to create new slots. |
| **Examiner** | Dr. Suresh Kumar (`EXM-004`) | `suresh_kumar` | `suresh.kumar@faculty.edu` | `Examiner@123` | **Pending Approval**. Shows "Registration Under Review" screen to test Admin approval workflow. |
| **Student** | Rahul Sharma (`21F1000101`) | `rahul_s` | `rahul.s@student.edu` | `Student@123` | **Completed Exam**. Has published results and rubric remarks; can **view and download official PDF scorecard**. |
| **Student** | Ananya Iyer (`21F1000202`) | `ananya_i` | `ananya.i@student.edu` | `Student@123` | **Active Booking**. Has a confirmed slot; test booking schedule and cancellation before deadline. |
| **Student** | Rohit Verma (`21F1000303`) | `rohit_v` | `rohit.v@student.edu` | `Student@123` | **Active Booking**. Booked for ML Practical viva; test duplicate booking prevention. |

---

## 🧪 Running Automated Tests
```bash
python -m unittest test_system.py
```
All 9 unit tests cover authentication, role boundaries, open/close window enforcement, duplicate prevention, overbooking prevention, rubric evaluation, PDF generation, and RESTful APIs.

