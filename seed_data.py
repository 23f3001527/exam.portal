import os
from datetime import datetime, date, time, timedelta
from application import create_app
from application.models import (
    db, User, ExaminerProfile, StudentProfile, Course, 
    Examination, ExaminationRubric, ExaminationSlot, Booking, 
    RubricScore, Notification
)

def seed_database():
    app = create_app()
    with app.app_context():
        # Clean existing tables
        db.drop_all()
        db.create_all()

        print("Seeding database...")

        # 1. Admin User (Pre-existing in database, no registration)
        admin = User(
            username="admin",
            email="admin@examportal.edu",
            role="admin"
        )
        admin.set_password("AdminPassword@123")
        db.session.add(admin)

        # 2. Approved Examiners
        examiner_users = [
            ("anita_roy", "anita.roy@faculty.edu", "Dr. Anita Roy", "EXM-001", "Computer Science", "+91 9811122334"),
            ("vikram_mehta", "vikram.mehta@faculty.edu", "Prof. Vikram Mehta", "EXM-002", "Data Science", "+91 9822233445"),
            ("priya_nair", "priya.nair@faculty.edu", "Dr. Priya Nair", "EXM-003", "Software Engineering", "+91 9833344556")
        ]

        examiners = []
        for uname, email, name, ex_id, dept, contact in examiner_users:
            u = User(username=uname, email=email, role="examiner")
            u.set_password("Examiner@123")
            db.session.add(u)
            db.session.flush()

            ep = ExaminerProfile(
                user_id=u.id,
                examiner_id=ex_id,
                name=name,
                department=dept,
                contact_details=contact,
                status="Approved",
                approved_at=datetime.utcnow()
            )
            db.session.add(ep)
            examiners.append(ep)

        # 3. Pending Examiner (to demonstrate admin approval workflow)
        pending_u = User(username="suresh_kumar", email="suresh.kumar@faculty.edu", role="examiner")
        pending_u.set_password("Examiner@123")
        db.session.add(pending_u)
        db.session.flush()

        pending_ep = ExaminerProfile(
            user_id=pending_u.id,
            examiner_id="EXM-004",
            name="Dr. Suresh Kumar",
            department="Artificial Intelligence",
            contact_details="+91 9844455667",
            status="Pending"
        )
        db.session.add(pending_ep)

        # 4. Students
        student_users = [
            ("rahul_s", "rahul.s@student.edu", "Rahul Sharma", "21F1000101", "Data Science & Applications", "+91 9123456780"),
            ("ananya_i", "ananya.i@student.edu", "Ananya Iyer", "21F1000202", "Computer Applications", "+91 9234567891"),
            ("rohit_v", "rohit.v@student.edu", "Rohit Verma", "21F1000303", "Electronic Systems", "+91 9345678902")
        ]

        students = []
        for uname, email, name, s_id, dept, contact in student_users:
            u = User(username=uname, email=email, role="student")
            u.set_password("Student@123")
            db.session.add(u)
            db.session.flush()

            sp = StudentProfile(
                user_id=u.id,
                student_id=s_id,
                name=name,
                department=dept,
                contact_details=contact
            )
            db.session.add(sp)
            students.append(sp)

        # 5. Courses
        c1 = Course(
            code="CS2001",
            name="Modern Application Development I",
            department="Computer Science",
            credits=4,
            description="Web frameworks, MVC architecture, Flask, relational databases, REST APIs, and responsive design."
        )
        c2 = Course(
            code="DS1002",
            name="Machine Learning Foundations",
            department="Data Science",
            credits=4,
            description="Supervised learning, classification, regression, model evaluation, and feature engineering."
        )
        c3 = Course(
            code="CS3001",
            name="Database Management Systems",
            department="Software Engineering",
            credits=4,
            description="Relational calculus, SQL query optimization, transactions, ACID properties, and indexing."
        )
        db.session.add_all([c1, c2, c3])
        db.session.flush()

        # 6. Examinations
        today = date.today()
        exam1 = Examination(
            course_id=c1.id,
            title="MAD-1 End-Term Project Viva",
            description="Comprehensive oral assessment covering MVC patterns, Flask models, routing, authentication, and REST APIs.",
            exam_type="Viva",
            total_marks=100.0,
            exam_date=today + timedelta(days=5),
            duration_minutes=30,
            slot_creation_open=True,
            student_booking_open=True,
            assigned_examiner_id=examiners[0].id,
            status="Published"
        )
        exam2 = Examination(
            course_id=c2.id,
            title="ML Practical viva & Code Review",
            description="Demonstration of model evaluation pipeline, metrics calculation, and confusion matrix explanation.",
            exam_type="Practical",
            total_marks=100.0,
            exam_date=today + timedelta(days=7),
            duration_minutes=30,
            slot_creation_open=True,
            student_booking_open=True,
            assigned_examiner_id=examiners[1].id,
            status="Published"
        )
        exam3 = Examination(
            course_id=c3.id,
            title="DBMS Query & Schema Viva",
            description="Evaluation on normal forms, ER-to-relational mapping, and complex SQL joins.",
            exam_type="Viva",
            total_marks=100.0,
            exam_date=today + timedelta(days=10),
            duration_minutes=30,
            slot_creation_open=False, # Closed to demonstrate control toggle
            student_booking_open=False,
            assigned_examiner_id=examiners[2].id,
            status="Published"
        )
        db.session.add_all([exam1, exam2, exam3])
        db.session.flush()

        # 7. Rubrics for Exam 1 (MAD-1 Viva)
        rubrics_exam1 = [
            ("Architecture & Data Modeling", 30.0, "Understanding of SQLAlchemy entities, relations, and database schema integrity"),
            ("Application Controllers & REST API", 40.0, "Implementation of Flask routes, error handlers, and JSON endpoints"),
            ("Viva Articulation & Q&A", 30.0, "Clarity of explanation and prompt responses during viva")
        ]
        r_objs_e1 = []
        for crit, max_m, desc in rubrics_exam1:
            r = ExaminationRubric(exam_id=exam1.id, criterion_name=crit, max_marks=max_m, description=desc)
            db.session.add(r)
            r_objs_e1.append(r)

        # Rubrics for Exam 2 (ML Practical)
        rubrics_exam2 = [
            ("Feature Pipeline & Preprocessing", 30.0, "Correct handling of missing values, scaling, and encodings"),
            ("Model Selection & Training", 40.0, "Sound justification of chosen estimator and hyperparameter choices"),
            ("Performance Metrics Explanation", 30.0, "Interpreting precision, recall, and ROC-AUC curves")
        ]
        for crit, max_m, desc in rubrics_exam2:
            r = ExaminationRubric(exam_id=exam2.id, criterion_name=crit, max_marks=max_m, description=desc)
            db.session.add(r)

        # Rubrics for Exam 3 (DBMS)
        rubrics_exam3 = [
            ("Schema Normalization (3NF/BCNF)", 40.0, "Ability to decompose anomalies without loss of dependency"),
            ("SQL Query Construction", 40.0, "Writing complex multi-table joins and subqueries"),
            ("Transaction Management", 20.0, "Explaining isolation levels and concurrency control")
        ]
        for crit, max_m, desc in rubrics_exam3:
            r = ExaminationRubric(exam_id=exam3.id, criterion_name=crit, max_marks=max_m, description=desc)
            db.session.add(r)

        db.session.flush()

        # 8. Examination Slots for Exam 1
        slot1 = ExaminationSlot(
            exam_id=exam1.id,
            examiner_id=examiners[0].id,
            slot_date=today + timedelta(days=2),
            start_time=time(10, 0),
            end_time=time(10, 30),
            capacity=1,
            current_bookings=1,
            status="Full",
            location_or_link="Lab 301, Academic Block"
        )
        slot2 = ExaminationSlot(
            exam_id=exam1.id,
            examiner_id=examiners[0].id,
            slot_date=today + timedelta(days=2),
            start_time=time(10, 30),
            end_time=time(11, 0),
            capacity=2,
            current_bookings=1,
            status="Open",
            location_or_link="Lab 301, Academic Block"
        )
        slot3 = ExaminationSlot(
            exam_id=exam1.id,
            examiner_id=examiners[1].id,
            slot_date=today + timedelta(days=3),
            start_time=time(14, 0),
            end_time=time(14, 30),
            capacity=2,
            current_bookings=0,
            status="Open",
            location_or_link="https://meet.google.com/ems-viva-mad1"
        )
        slot4 = ExaminationSlot(
            exam_id=exam2.id,
            examiner_id=examiners[1].id,
            slot_date=today + timedelta(days=4),
            start_time=time(15, 0),
            end_time=time(15, 30),
            capacity=2,
            current_bookings=1,
            status="Open",
            location_or_link="Room 102, Data Science Building"
        )
        db.session.add_all([slot1, slot2, slot3, slot4])
        db.session.flush()

        # 9. Bookings & Evaluated Scorecards
        # Booking 1: Student 0 (Rahul) completed & evaluated by Dr. Anita Roy
        booking1 = Booking(
            student_id=students[0].id,
            slot_id=slot1.id,
            exam_id=exam1.id,
            booking_date=datetime.utcnow() - timedelta(days=3),
            status="Completed",
            marks_obtained=88.0,
            percentage=88.0,
            evaluation_remarks="Excellent architecture diagrams and thorough understanding of MVC separation. Answered all viva questions confidently.",
            evaluated_by=examiners[0].id,
            evaluation_date=datetime.utcnow() - timedelta(days=1),
            result_published=True
        )
        db.session.add(booking1)
        db.session.flush()

        # Rubric scores for booking1
        db.session.add(RubricScore(booking_id=booking1.id, rubric_id=r_objs_e1[0].id, score=27.0, remarks="Clean database schema with proper indexes"))
        db.session.add(RubricScore(booking_id=booking1.id, rubric_id=r_objs_e1[1].id, score=35.0, remarks="Endpoints followed RESTful constraints nicely"))
        db.session.add(RubricScore(booking_id=booking1.id, rubric_id=r_objs_e1[2].id, score=26.0, remarks="Clear and fluent presentation"))

        # Notification for booking1 result
        notif1 = Notification(
            user_id=students[0].user.id,
            email_to=students[0].user.email,
            subject=f"Examination Results Published: {exam1.title} ({c1.code})",
            body=f"Dear {students[0].name},\n\nYour results for {exam1.title} have been evaluated and published.\nScore: 88.0 / 100.0 (88.0% - Distinction)\nRemarks: Excellent architecture diagrams.\n\nYou can download your official examination scorecard from your student dashboard.\n\nRegards,\nEMS Office",
            notification_type="Result Publication",
            sent_at=datetime.utcnow() - timedelta(days=1),
            is_read=False
        )
        db.session.add(notif1)

        # Booking 2: Student 1 (Ananya) active booking in slot 2
        booking2 = Booking(
            student_id=students[1].id,
            slot_id=slot2.id,
            exam_id=exam1.id,
            booking_date=datetime.utcnow() - timedelta(days=1),
            status="Booked"
        )
        db.session.add(booking2)

        notif2 = Notification(
            user_id=students[1].user.id,
            email_to=students[1].user.email,
            subject=f"Booking Confirmation: {exam1.title} ({c1.code})",
            body=f"Dear {students[1].name},\n\nYour examination slot booking has been confirmed.\nDate: {slot2.slot_date.strftime('%A, %d %B %Y')}\nTime: {slot2.start_time.strftime('%I:%M %p')} - {slot2.end_time.strftime('%I:%M %p')}\nExaminer: {slot2.examiner.name}\nVenue: {slot2.location_or_link}\n\nRegards,\nEMS Office",
            notification_type="Booking Confirmation",
            sent_at=datetime.utcnow() - timedelta(days=1),
            is_read=True
        )
        db.session.add(notif2)

        # Booking 3: Student 2 (Rohit) active booking in slot 4 (ML)
        booking3 = Booking(
            student_id=students[2].id,
            slot_id=slot4.id,
            exam_id=exam2.id,
            booking_date=datetime.utcnow() - timedelta(hours=6),
            status="Booked"
        )
        db.session.add(booking3)

        notif3 = Notification(
            user_id=students[2].user.id,
            email_to=students[2].user.email,
            subject=f"Booking Confirmation: {exam2.title} ({c2.code})",
            body=f"Dear {students[2].name},\n\nYour examination slot booking has been confirmed.\nDate: {slot4.slot_date.strftime('%A, %d %B %Y')}\nTime: {slot4.start_time.strftime('%I:%M %p')}\nExaminer: {slot4.examiner.name}\nVenue: {slot4.location_or_link}\n\nRegards,\nEMS Office",
            notification_type="Booking Confirmation",
            sent_at=datetime.utcnow() - timedelta(hours=6),
            is_read=False
        )
        db.session.add(notif3)

        # Booking 4: Cancelled Booking (to demonstrate complete booking history maintenance)
        booking4 = Booking(
            student_id=students[0].id,
            slot_id=slot3.id,
            exam_id=exam1.id,
            booking_date=datetime.utcnow() - timedelta(days=5),
            status="Cancelled"
        )
        db.session.add(booking4)

        db.session.commit()
        print("Database successfully populated with comprehensive sample data!")

if __name__ == "__main__":
    seed_database()

