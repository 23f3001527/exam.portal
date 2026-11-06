import unittest
from datetime import datetime, date, time, timedelta
from application import create_app
from application.models import (
    db, User, ExaminerProfile, StudentProfile, Course, 
    Examination, ExaminationRubric, ExaminationSlot, Booking, 
    RubricScore, Notification
)

class TestExaminationManagementSystem(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

        with self.app.app_context():
            db.drop_all()
            db.create_all()

            # Pre-existing Admin (created or retrieved)
            self.admin = User.query.filter_by(role='admin').first()
            if not self.admin:
                self.admin = User(username='admin', email='admin@ems.edu', role='admin')
                self.admin.set_password('AdminPassword@123')
                db.session.add(self.admin)
            else:
                self.admin.set_password('AdminPassword@123')

            # Approved Examiner
            self.ex_user = User(username='examiner1', email='ex1@ems.edu', role='examiner')
            self.ex_user.set_password('Examiner@123')
            db.session.add(self.ex_user)
            db.session.flush()

            self.examiner = ExaminerProfile(
                user_id=self.ex_user.id,
                examiner_id='EXM-TEST-1',
                name='Dr. Test Examiner',
                department='Computer Science',
                status='Approved'
            )
            db.session.add(self.examiner)

            # Student
            self.stu_user = User(username='student1', email='stu1@ems.edu', role='student')
            self.stu_user.set_password('Student@123')
            db.session.add(self.stu_user)
            db.session.flush()

            self.student = StudentProfile(
                user_id=self.stu_user.id,
                student_id='STU-TEST-1',
                name='Test Student',
                department='Data Science'
            )
            db.session.add(self.student)

            # Course
            self.course = Course(
                code='CS101',
                name='Introduction to Programming',
                department='Computer Science',
                credits=4
            )
            db.session.add(self.course)
            db.session.flush()

            # Examination
            self.exam = Examination(
                course_id=self.course.id,
                title='Python Lab Viva',
                exam_type='Viva',
                total_marks=100.0,
                exam_date=date.today() + timedelta(days=7),
                duration_minutes=30,
                slot_creation_open=True,
                student_booking_open=True,
                assigned_examiner_id=self.examiner.id,
                status='Published'
            )
            db.session.add(self.exam)
            db.session.flush()

            # Rubrics
            r1 = ExaminationRubric(exam_id=self.exam.id, criterion_name='Syntax & Logic', max_marks=50.0)
            r2 = ExaminationRubric(exam_id=self.exam.id, criterion_name='Q&A Viva', max_marks=50.0)
            db.session.add_all([r1, r2])
            db.session.flush()

            # Slot
            self.slot = ExaminationSlot(
                exam_id=self.exam.id,
                examiner_id=self.examiner.id,
                slot_date=date.today() + timedelta(days=2),
                start_time=time(10, 0),
                end_time=time(10, 30),
                capacity=1,
                current_bookings=0,
                status='Open'
            )
            db.session.add(self.slot)
            db.session.commit()

            self.admin_id = self.admin.id
            self.examiner_id = self.examiner.id
            self.student_id = self.student.id
            self.exam_id = self.exam.id
            self.slot_id = self.slot.id
            self.r1_id = r1.id
            self.r2_id = r2.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def login(self, username, password):
        self.logout()
        return self.client.post('/login', data={
            'identifier': username,
            'password': password
        }, follow_redirects=True)

    def logout(self):
        return self.client.get('/logout', follow_redirects=True)

    # ---------------- 1. AUTHENTICATION TESTS ----------------
    def test_admin_login(self):
        res = self.login('admin', 'AdminPassword@123')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Admin Management Console', res.data)

    def test_student_registration_and_login(self):
        self.logout()
        res = self.client.post('/register/student', data={
            'student_id': 'STU-NEW-99',
            'name': 'New Student',
            'email': 'newstu@ems.edu',
            'contact': '+91 9999999999',
            'department': 'Electrical',
            'username': 'newstu',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Student Portal', res.data)

    def test_examiner_self_registration_pending_and_approval(self):
        self.logout()
        # Register as examiner
        res = self.client.post('/register/examiner', data={
            'examiner_id': 'EXM-NEW-88',
            'name': 'New Examiner',
            'email': 'newex@faculty.edu',
            'contact': '+91 8888888888',
            'department': 'Mechanical',
            'username': 'newex',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Registration Under Review', res.data)

        # Pending examiner tries to access examiner slots -> blocked
        res_slots = self.client.get('/examiner/slots', follow_redirects=True)
        self.assertIn(b'Pending', res_slots.data)

        # Log out examiner before logging in as Admin
        self.logout()

        # Admin logs in and approves examiner
        self.login('admin', 'AdminPassword@123')
        with self.app.app_context():
            new_ex = ExaminerProfile.query.filter_by(examiner_id='EXM-NEW-88').first()
            ex_db_id = new_ex.id

        res_appr = self.client.post(f'/admin/examiners/{ex_db_id}/approve', follow_redirects=True)
        self.assertIn(b'Approved', res_appr.data)
        self.logout()

        # Approved examiner logs in -> access granted
        self.login('newex', 'password123')
        res_dash = self.client.get('/examiner/dashboard')
        self.assertEqual(res_dash.status_code, 200)
        self.assertIn(b'Examiner Portal', res_dash.data)

    # ---------------- 2. ADMIN FUNCTIONALITIES TESTS ----------------
    def test_admin_course_management(self):
        self.login('admin', 'AdminPassword@123')
        # Create course
        res_create = self.client.post('/admin/courses/new', data={
            'code': 'CS202',
            'name': 'Data Structures',
            'department': 'Computer Science',
            'credits': 4,
            'description': 'Arrays, Trees, Graphs'
        }, follow_redirects=True)
        self.assertEqual(res_create.status_code, 200)
        self.assertIn(b'CS202', res_create.data)

    def test_admin_toggle_slot_creation_and_booking(self):
        self.login('admin', 'AdminPassword@123')
        # Toggle slot creation closed
        res1 = self.client.post(f'/admin/examinations/{self.exam_id}/toggle-slot-creation', follow_redirects=True)
        self.assertEqual(res1.status_code, 200)
        with self.app.app_context():
            exam = db.session.get(Examination, self.exam_id)
            self.assertFalse(exam.slot_creation_open)

        # Toggle student booking closed
        res2 = self.client.post(f'/admin/examinations/{self.exam_id}/toggle-student-booking', follow_redirects=True)
        self.assertEqual(res2.status_code, 200)
        with self.app.app_context():
            exam = db.session.get(Examination, self.exam_id)
            self.assertFalse(exam.student_booking_open)

    # ---------------- 3. EXAMINER FUNCTIONALITIES TESTS ----------------
    def test_examiner_create_slot_respects_window(self):
        self.login('examiner1', 'Examiner@123')
        # Slot creation is open -> success
        res = self.client.post('/examiner/slots/new', data={
            'exam_id': self.exam_id,
            'slot_date': (date.today() + timedelta(days=3)).strftime('%Y-%m-%d'),
            'start_time': '14:00',
            'end_time': '14:30',
            'capacity': 2,
            'location_or_link': 'Room 101'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'created successfully', res.data)

        # Close slot creation from admin
        self.logout()
        self.login('admin', 'AdminPassword@123')
        self.client.post(f'/admin/examinations/{self.exam_id}/toggle-slot-creation', follow_redirects=True)
        self.logout()

        # Examiner tries to create slot when closed -> rejected
        self.login('examiner1', 'Examiner@123')
        res_fail = self.client.post('/examiner/slots/new', data={
            'exam_id': self.exam_id,
            'slot_date': (date.today() + timedelta(days=4)).strftime('%Y-%m-%d'),
            'start_time': '15:00',
            'end_time': '15:30',
            'capacity': 1
        }, follow_redirects=True)
        self.assertIn(b'closed', res_fail.data)

    # ---------------- 4. STUDENT FUNCTIONALITIES & CORE RULES ----------------
    def test_student_booking_duplicate_prevention_and_overbooking(self):
        # 1. Student books slot
        self.login('student1', 'Student@123')
        res_book = self.client.post(f'/student/slots/{self.slot_id}/book', follow_redirects=True)
        self.assertEqual(res_book.status_code, 200)
        self.assertIn(b'Slot booked successfully', res_book.data)

        # 2. Rule: Prevent duplicate bookings for same examination
        res_dup = self.client.post(f'/student/slots/{self.slot_id}/book', follow_redirects=True)
        self.assertIn(b'already have an active booking', res_dup.data)

        # 3. Rule: Prevent overbooking beyond slot capacity
        self.logout()
        # Register a second student
        self.client.post('/register/student', data={
            'student_id': 'STU-SECOND-2',
            'name': 'Second Student',
            'email': 'second@ems.edu',
            'contact': '+91 7777777777',
            'department': 'CS',
            'username': 'secondstu',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)

        res_overbook = self.client.post(f'/student/slots/{self.slot_id}/book', follow_redirects=True)
        self.assertIn(b'full capacity', res_overbook.data)

    def test_rubric_evaluation_and_pdf_scorecard_download(self):
        # Book a slot first
        self.login('student1', 'Student@123')
        self.client.post(f'/student/slots/{self.slot_id}/book', follow_redirects=True)
        self.logout()

        with self.app.app_context():
            booking = Booking.query.filter_by(student_id=self.student_id, exam_id=self.exam_id).first()
            booking_id = booking.id

        # Examiner evaluates booking with rubrics
        self.login('examiner1', 'Examiner@123')
        res_eval = self.client.post(f'/examiner/evaluate/{booking_id}', data={
            f'rubric_{self.r1_id}': '45',
            f'remarks_{self.r1_id}': 'Excellent understanding of syntax',
            f'rubric_{self.r2_id}': '45',
            f'remarks_{self.r2_id}': 'Clear answers in viva',
            'remarks': 'Outstanding demonstration and code knowledge.',
            'publish': 'true'
        }, follow_redirects=True)
        self.assertEqual(res_eval.status_code, 200)
        self.assertIn(b'Evaluation submitted', res_eval.data)
        self.logout()

        # Student logs in, views scorecard, and downloads PDF
        self.login('student1', 'Student@123')
        res_view = self.client.get(f'/student/scorecard/{booking_id}')
        self.assertEqual(res_view.status_code, 200)
        self.assertIn(b'Official Candidate Scorecard', res_view.data)
        self.assertIn(b'90.0', res_view.data)

        # Download PDF scorecard
        res_pdf = self.client.get(f'/student/scorecard/{booking_id}/download')
        self.assertEqual(res_pdf.status_code, 200)
        self.assertEqual(res_pdf.mimetype, 'application/pdf')
        self.assertTrue(res_pdf.data.startswith(b'%PDF-1.4'))

    # ---------------- 5. RESTFUL API TESTS ----------------
    def test_json_api_endpoints(self):
        # Public examinations API
        res = self.client.get('/api/v1/examinations')
        self.assertEqual(res.status_code, 200)
        json_data = res.get_json()
        self.assertIn('examinations', json_data)
        self.assertGreaterEqual(json_data['count'], 1)

        # Admin stats API
        self.login('admin', 'AdminPassword@123')
        res_stats = self.client.get('/api/v1/stats')
        self.assertEqual(res_stats.status_code, 200)
        stats_json = res_stats.get_json()
        self.assertIn('summary', stats_json)
        self.assertIn('booking_status_distribution', stats_json)

if __name__ == '__main__':
    unittest.main()
