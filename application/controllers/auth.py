from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from application.models import db, User, ExaminerProfile, StudentProfile
from application.utils.email_service import send_notification

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        elif current_user.is_examiner:
            if current_user.examiner_profile and current_user.examiner_profile.status == 'Approved':
                return redirect(url_for('examiner.dashboard'))
            else:
                return redirect(url_for('auth.pending_approval'))
        elif current_user.is_student:
            return redirect(url_for('student.dashboard'))
    return render_template('auth/index.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        # Backend validation
        if not identifier or not password:
            flash('Both username/email and password are required.', 'danger')
            return render_template('auth/login.html', identifier=identifier)

        # Look up by username or email
        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()

        if not user or not user.check_password(password):
            flash('Invalid username/email or password.', 'danger')
            return render_template('auth/login.html', identifier=identifier)

        login_user(user, remember=remember)
        flash(f'Welcome back, {user.username}!', 'success')

        # Role-based redirection
        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            return redirect(next_page)

        if user.is_admin:
            return redirect(url_for('admin.dashboard'))
        elif user.is_examiner:
            if user.examiner_profile and user.examiner_profile.status == 'Approved':
                return redirect(url_for('examiner.dashboard'))
            else:
                return redirect(url_for('auth.pending_approval'))
        elif user.is_student:
            return redirect(url_for('student.dashboard'))
        
        return redirect(url_for('auth.index'))

    return render_template('auth/login.html')


@auth_bp.route('/register/student', methods=['GET', 'POST'])
def register_student():
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))

    if request.method == 'POST':
        student_id = request.form.get('student_id', '').strip()
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        contact = request.form.get('contact', '').strip()
        department = request.form.get('department', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Backend validations
        if not all([student_id, name, email, department, username, password]):
            flash('All required fields must be filled out.', 'danger')
            return render_template('auth/register_student.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register_student.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('auth/register_student.html')

        if User.query.filter_by(username=username).first():
            flash('Username is already taken. Please choose another.', 'danger')
            return render_template('auth/register_student.html')

        if User.query.filter_by(email=email).first():
            flash('An account with this email already exists.', 'danger')
            return render_template('auth/register_student.html')

        if StudentProfile.query.filter_by(student_id=student_id).first():
            flash('A student with this Student ID / Roll No is already registered.', 'danger')
            return render_template('auth/register_student.html')

        # Create student user and profile
        user = User(
            username=username,
            email=email,
            role='student'
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        student_profile = StudentProfile(
            user_id=user.id,
            student_id=student_id,
            name=name,
            contact_details=contact,
            department=department
        )
        db.session.add(student_profile)
        db.session.commit()

        # Send welcome notification
        send_notification(
            user,
            "Welcome to Examination Management System",
            f"Dear {name},\n\nYour student account ({student_id}) has been created successfully. "
            f"You can now log in to view and book examination slots.\n\nRegards,\nEMS Administration",
            "Welcome"
        )

        login_user(user)
        flash('Registration successful! Welcome to the student portal.', 'success')
        return redirect(url_for('student.dashboard'))

    return render_template('auth/register_student.html')


@auth_bp.route('/register/examiner', methods=['GET', 'POST'])
def register_examiner():
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))

    if request.method == 'POST':
        examiner_id = request.form.get('examiner_id', '').strip()
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        contact = request.form.get('contact', '').strip()
        department = request.form.get('department', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Backend validations
        if not all([examiner_id, name, email, department, username, password]):
            flash('All required fields must be completed.', 'danger')
            return render_template('auth/register_examiner.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register_examiner.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('auth/register_examiner.html')

        if User.query.filter_by(username=username).first():
            flash('Username is already taken. Please choose another.', 'danger')
            return render_template('auth/register_examiner.html')

        if User.query.filter_by(email=email).first():
            flash('An account with this email already exists.', 'danger')
            return render_template('auth/register_examiner.html')

        if ExaminerProfile.query.filter_by(examiner_id=examiner_id).first():
            flash('An examiner with this Examiner ID is already registered.', 'danger')
            return render_template('auth/register_examiner.html')

        # Create examiner user and profile with status='Pending'
        user = User(
            username=username,
            email=email,
            role='examiner'
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        examiner_profile = ExaminerProfile(
            user_id=user.id,
            examiner_id=examiner_id,
            name=name,
            contact_details=contact,
            department=department,
            status='Pending'
        )
        db.session.add(examiner_profile)
        db.session.commit()

        # Welcome notification
        send_notification(
            user,
            "Examiner Registration Submitted",
            f"Dear {name},\n\nYour examiner registration (ID: {examiner_id}) has been submitted. "
            f"An administrator will review and approve your account shortly.\n\nRegards,\nEMS Administration",
            "Registration"
        )

        login_user(user)
        flash('Registration submitted successfully! Your account is awaiting Administrator approval.', 'info')
        return redirect(url_for('auth.pending_approval'))

    return render_template('auth/register_examiner.html')


@auth_bp.route('/pending-approval')
@login_required
def pending_approval():
    if not current_user.is_examiner:
        return redirect(url_for('auth.index'))
    if current_user.examiner_profile and current_user.examiner_profile.status == 'Approved':
        return redirect(url_for('examiner.dashboard'))
    return render_template('auth/pending_approval.html', profile=current_user.examiner_profile)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out securely.', 'info')
    return redirect(url_for('auth.login'))

