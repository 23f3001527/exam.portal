from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin', 'examiner', 'student'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    examiner_profile = db.relationship('ExaminerProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    student_profile = db.relationship('StudentProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_examiner(self):
        return self.role == 'examiner'

    @property
    def is_student(self):
        return self.role == 'student'

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class ExaminerProfile(db.Model):
    __tablename__ = 'examiner_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    examiner_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    contact_details = db.Column(db.String(150), nullable=True)  # Phone number, office
    department = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='Pending')  # 'Pending', 'Approved', 'Rejected'
    approved_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    assigned_examinations = db.relationship('Examination', backref='assigned_examiner', foreign_keys='Examination.assigned_examiner_id')
    created_slots = db.relationship('ExaminationSlot', backref='examiner', lazy='dynamic', cascade='all, delete-orphan')

    def is_approved(self):
        return self.status == 'Approved'

    def __repr__(self):
        return f"<Examiner {self.examiner_id} - {self.name} ({self.status})>"


class StudentProfile(db.Model):
    __tablename__ = 'student_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    student_id = db.Column(db.String(50), unique=True, nullable=False, index=True)  # Roll number
    name = db.Column(db.String(120), nullable=False)
    contact_details = db.Column(db.String(150), nullable=True)  # Phone number
    department = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    bookings = db.relationship('Booking', backref='student', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Student {self.student_id} - {self.name}>"


class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    department = db.Column(db.String(100), nullable=False)
    credits = db.Column(db.Integer, default=4)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    examinations = db.relationship('Examination', backref='course', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Course {self.code}: {self.name}>"


class Examination(db.Model):
    __tablename__ = 'examinations'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    exam_type = db.Column(db.String(50), default='Viva')  # 'Viva', 'Practical', 'Theory', 'Project'
    total_marks = db.Column(db.Float, default=100.0)
    exam_date = db.Column(db.Date, nullable=False)
    duration_minutes = db.Column(db.Integer, default=30)
    
    # Global switches / windows controlled by Admin
    slot_creation_open = db.Column(db.Boolean, default=True)
    student_booking_open = db.Column(db.Boolean, default=True)
    
    # Optional assigned primary examiner
    assigned_examiner_id = db.Column(db.Integer, db.ForeignKey('examiner_profiles.id', ondelete='SET NULL'), nullable=True)

    status = db.Column(db.String(20), default='Published')  # 'Draft', 'Published', 'Completed'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    rubrics = db.relationship('ExaminationRubric', backref='examination', lazy='dynamic', cascade='all, delete-orphan')
    slots = db.relationship('ExaminationSlot', backref='examination', lazy='dynamic', cascade='all, delete-orphan')
    bookings = db.relationship('Booking', backref='examination', lazy='dynamic', cascade='all, delete-orphan')

    def rubric_total(self):
        return sum(r.max_marks for r in self.rubrics)

    def total_capacity(self):
        return sum(s.capacity for s in self.slots)

    def booked_count(self):
        return self.bookings.filter(Booking.status != 'Cancelled').count()

    def __repr__(self):
        return f"<Examination {self.title} (Course: {self.course_id})>"


class ExaminationRubric(db.Model):
    __tablename__ = 'examination_rubrics'

    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('examinations.id', ondelete='CASCADE'), nullable=False)
    criterion_name = db.Column(db.String(150), nullable=False)
    max_marks = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)

    # Relationship to scores
    scores = db.relationship('RubricScore', backref='rubric', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Rubric {self.criterion_name} ({self.max_marks} marks)>"


class ExaminationSlot(db.Model):
    __tablename__ = 'examination_slots'

    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('examinations.id', ondelete='CASCADE'), nullable=False)
    examiner_id = db.Column(db.Integer, db.ForeignKey('examiner_profiles.id', ondelete='CASCADE'), nullable=False)
    slot_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    capacity = db.Column(db.Integer, default=1, nullable=False)
    current_bookings = db.Column(db.Integer, default=0, nullable=False)
    status = db.Column(db.String(20), default='Open')  # 'Open', 'Closed', 'Full', 'Cancelled'
    location_or_link = db.Column(db.String(255), nullable=True)  # Room number or meeting URL
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    bookings = db.relationship('Booking', backref='slot', lazy='dynamic', cascade='all, delete-orphan')

    def is_available(self):
        return self.status == 'Open' and self.current_bookings < self.capacity

    def update_status(self):
        active_bookings = self.bookings.filter(Booking.status.in_(['Booked', 'Completed', 'Rescheduled'])).count()
        self.current_bookings = active_bookings
        if self.current_bookings >= self.capacity:
            self.status = 'Full'
        elif self.status == 'Full' and self.current_bookings < self.capacity:
            self.status = 'Open'

    def __repr__(self):
        return f"<Slot {self.slot_date} {self.start_time}-{self.end_time} [{self.current_bookings}/{self.capacity}]>"


class Booking(db.Model):
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student_profiles.id', ondelete='CASCADE'), nullable=False)
    slot_id = db.Column(db.Integer, db.ForeignKey('examination_slots.id', ondelete='CASCADE'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('examinations.id', ondelete='CASCADE'), nullable=False)
    booking_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Booked')  # 'Booked', 'Cancelled', 'Completed', 'Rescheduled'
    
    # Evaluation and Scorecard
    marks_obtained = db.Column(db.Float, nullable=True)
    percentage = db.Column(db.Float, nullable=True)
    evaluation_remarks = db.Column(db.Text, nullable=True)
    evaluated_by = db.Column(db.Integer, db.ForeignKey('examiner_profiles.id', ondelete='SET NULL'), nullable=True)
    evaluation_date = db.Column(db.DateTime, nullable=True)
    result_published = db.Column(db.Boolean, default=False)
    
    # Extra fields
    notes = db.Column(db.Text, nullable=True)

    # Relationships
    evaluator = db.relationship('ExaminerProfile', foreign_keys=[evaluated_by])
    rubric_scores = db.relationship('RubricScore', backref='booking', lazy='dynamic', cascade='all, delete-orphan')

    def calculate_totals(self):
        scores = self.rubric_scores.all()
        if scores:
            self.marks_obtained = sum(s.score for s in scores)
            if self.examination and self.examination.total_marks > 0:
                self.percentage = round((self.marks_obtained / self.examination.total_marks) * 100, 2)
            else:
                self.percentage = 0.0

    def __repr__(self):
        return f"<Booking {self.id}: Student {self.student_id} Exam {self.exam_id} ({self.status})>"


class RubricScore(db.Model):
    __tablename__ = 'rubric_scores'

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id', ondelete='CASCADE'), nullable=False)
    rubric_id = db.Column(db.Integer, db.ForeignKey('examination_rubrics.id', ondelete='CASCADE'), nullable=False)
    score = db.Column(db.Float, default=0.0, nullable=False)
    remarks = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<RubricScore Booking:{self.booking_id} Rubric:{self.rubric_id} Score:{self.score}>"


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    email_to = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), default='General')  # 'Booking Confirmation', 'Result Publication', 'Reschedule', 'Status Update'
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<Notification to {self.email_to}: {self.subject}>"


class SystemSetting(db.Model):
    __tablename__ = 'system_settings'

    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255), nullable=True)

    @classmethod
    def get_setting(cls, key, default=None):
        setting = cls.query.filter_by(key=key).first()
        return setting.value if setting else default

    @classmethod
    def set_setting(cls, key, value, description=None):
        setting = cls.query.filter_by(key=key).first()
        if setting:
            setting.value = str(value)
            if description:
                setting.description = description
        else:
            setting = cls(key=key, value=str(value), description=description)
            db.session.add(setting)
        db.session.commit()

