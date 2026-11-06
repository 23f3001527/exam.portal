from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from application.models import (
    db, User, Course, Examination, ExaminationRubric, ExaminationSlot, 
    Booking, ExaminerProfile, StudentProfile, Notification, SystemSetting
)
from application.utils.auth_decorators import admin_required
from application.utils.email_service import (
    notify_examiner_approval, notify_booking_reschedule
)

admin_bp = Blueprint('admin', __name__)

@admin_bp.before_request
@login_required
@admin_required
def check_admin():
    pass


@admin_bp.route('/dashboard')
def dashboard():
    # Admin metrics
    total_courses = Course.query.count()
    total_examinations = Examination.query.count()
    total_examiners = ExaminerProfile.query.count()
    total_students = StudentProfile.query.count()
    total_slots = ExaminationSlot.query.count()
    total_bookings = Booking.query.count()
    
    pending_examiners_count = ExaminerProfile.query.filter_by(status='Pending').count()
    recent_bookings = Booking.query.order_by(Booking.booking_date.desc()).limit(8).all()
    upcoming_slots = ExaminationSlot.query.filter(ExaminationSlot.slot_date >= datetime.utcnow().date()).order_by(ExaminationSlot.slot_date.asc(), ExaminationSlot.start_time.asc()).limit(6).all()

    # Chart data calculations
    # 1. Examination completion status
    completed_bookings = Booking.query.filter_by(status='Completed').count()
    active_bookings = Booking.query.filter(Booking.status.in_(['Booked', 'Rescheduled'])).count()
    cancelled_bookings = Booking.query.filter_by(status='Cancelled').count()

    # 2. Examiner workload (slots and bookings per examiner)
    examiners = ExaminerProfile.query.filter_by(status='Approved').limit(10).all()
    examiner_names = [e.name for e in examiners]
    examiner_slot_counts = [e.created_slots.count() for e in examiners]
    examiner_booking_counts = [
        sum(slot.current_bookings for slot in e.created_slots) for e in examiners
    ]

    return render_template(
        'admin/dashboard.html',
        total_courses=total_courses,
        total_examinations=total_examinations,
        total_examiners=total_examiners,
        total_students=total_students,
        total_slots=total_slots,
        total_bookings=total_bookings,
        pending_examiners_count=pending_examiners_count,
        recent_bookings=recent_bookings,
        upcoming_slots=upcoming_slots,
        chart_data={
            'completed': completed_bookings,
            'active': active_bookings,
            'cancelled': cancelled_bookings,
            'examiner_names': examiner_names,
            'examiner_slots': examiner_slot_counts,
            'examiner_bookings': examiner_booking_counts,
        }
    )


# ---------------- COURSE MANAGEMENT ----------------
@admin_bp.route('/courses')
def courses():
    search_query = request.args.get('q', '').strip()
    if search_query:
        course_list = Course.query.filter(
            (Course.name.ilike(f'%{search_query}%')) | 
            (Course.code.ilike(f'%{search_query}%')) |
            (Course.department.ilike(f'%{search_query}%'))
        ).order_by(Course.code.asc()).all()
    else:
        course_list = Course.query.order_by(Course.code.asc()).all()
    return render_template('admin/courses.html', courses=course_list, search_query=search_query)


@admin_bp.route('/courses/new', methods=['GET', 'POST'])
def create_course():
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        name = request.form.get('name', '').strip()
        department = request.form.get('department', '').strip()
        credits_str = request.form.get('credits', '4').strip()
        description = request.form.get('description', '').strip()

        if not code or not name or not department:
            flash('Course Code, Name, and Department are required.', 'danger')
            return render_template('admin/course_form.html', action='Create', course=None)

        if Course.query.filter_by(code=code).first():
            flash(f'Course with code "{code}" already exists.', 'danger')
            return render_template('admin/course_form.html', action='Create', course=None)

        course = Course(
            code=code,
            name=name,
            department=department,
            credits=int(credits_str) if credits_str.isdigit() else 4,
            description=description
        )
        db.session.add(course)
        db.session.commit()
        flash(f'Course "{code}: {name}" created successfully.', 'success')
        return redirect(url_for('admin.courses'))

    return render_template('admin/course_form.html', action='Create', course=None)


@admin_bp.route('/courses/<int:course_id>/edit', methods=['GET', 'POST'])
def edit_course(course_id):
    course = Course.query.get_or_404(course_id)
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        name = request.form.get('name', '').strip()
        department = request.form.get('department', '').strip()
        credits_str = request.form.get('credits', '4').strip()
        description = request.form.get('description', '').strip()

        if not code or not name or not department:
            flash('Course Code, Name, and Department are required.', 'danger')
            return render_template('admin/course_form.html', action='Edit', course=course)

        existing = Course.query.filter_by(code=code).first()
        if existing and existing.id != course.id:
            flash(f'Another course with code "{code}" already exists.', 'danger')
            return render_template('admin/course_form.html', action='Edit', course=course)

        course.code = code
        course.name = name
        course.department = department
        course.credits = int(credits_str) if credits_str.isdigit() else course.credits
        course.description = description
        db.session.commit()

        flash(f'Course "{course.code}" updated successfully.', 'success')
        return redirect(url_for('admin.courses'))

    return render_template('admin/course_form.html', action='Edit', course=course)


@admin_bp.route('/courses/<int:course_id>/delete', methods=['POST'])
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    name = course.name
    code = course.code
    db.session.delete(course)
    db.session.commit()
    flash(f'Course {code} ({name}) deleted successfully.', 'info')
    return redirect(url_for('admin.courses'))


# ---------------- EXAMINATION MANAGEMENT ----------------
@admin_bp.route('/examinations')
def examinations():
    search_query = request.args.get('q', '').strip()
    query = Examination.query.join(Course)
    if search_query:
        query = query.filter(
            (Examination.title.ilike(f'%{search_query}%')) |
            (Course.name.ilike(f'%{search_query}%')) |
            (Course.code.ilike(f'%{search_query}%'))
        )
    exams = query.order_by(Examination.exam_date.desc()).all()
    return render_template('admin/examinations.html', examinations=exams, search_query=search_query)


@admin_bp.route('/examinations/new', methods=['GET', 'POST'])
def create_examination():
    courses = Course.query.order_by(Course.code.asc()).all()
    examiners = ExaminerProfile.query.filter_by(status='Approved').order_by(ExaminerProfile.name.asc()).all()

    if request.method == 'POST':
        course_id = request.form.get('course_id')
        title = request.form.get('title', '').strip()
        exam_type = request.form.get('exam_type', 'Viva')
        total_marks = request.form.get('total_marks', 100)
        exam_date_str = request.form.get('exam_date')
        duration = request.form.get('duration_minutes', 30)
        description = request.form.get('description', '').strip()
        assigned_examiner_id = request.form.get('assigned_examiner_id') or None
        slot_creation_open = 'slot_creation_open' in request.form
        student_booking_open = 'student_booking_open' in request.form

        if not course_id or not title or not exam_date_str:
            flash('Course, Title, and Examination Date are required.', 'danger')
            return render_template('admin/examination_form.html', action='Create', exam=None, courses=courses, examiners=examiners)

        try:
            exam_date = datetime.strptime(exam_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format.', 'danger')
            return render_template('admin/examination_form.html', action='Create', exam=None, courses=courses, examiners=examiners)

        exam = Examination(
            course_id=int(course_id),
            title=title,
            description=description,
            exam_type=exam_type,
            total_marks=float(total_marks),
            exam_date=exam_date,
            duration_minutes=int(duration),
            slot_creation_open=slot_creation_open,
            student_booking_open=student_booking_open,
            assigned_examiner_id=int(assigned_examiner_id) if assigned_examiner_id else None,
            status='Published'
        )
        db.session.add(exam)
        db.session.commit()

        # Add a default rubric for convenience
        default_rubrics = [
            ("Conceptual Understanding", exam.total_marks * 0.4, "Grasp of foundational concepts and principles"),
            ("Implementation & Practical Skill", exam.total_marks * 0.4, "Demonstration of practical coding/problem-solving"),
            ("Communication & Q&A", exam.total_marks * 0.2, "Clarity of response and viva articulation")
        ]
        for c_name, c_marks, c_desc in default_rubrics:
            rubric = ExaminationRubric(
                exam_id=exam.id,
                criterion_name=c_name,
                max_marks=c_marks,
                description=c_desc
            )
            db.session.add(rubric)
        db.session.commit()

        flash(f'Examination "{title}" created with default rubrics.', 'success')
        return redirect(url_for('admin.examination_rubrics', exam_id=exam.id))

    return render_template('admin/examination_form.html', action='Create', exam=None, courses=courses, examiners=examiners)


@admin_bp.route('/examinations/<int:exam_id>/edit', methods=['GET', 'POST'])
def edit_examination(exam_id):
    exam = Examination.query.get_or_404(exam_id)
    courses = Course.query.order_by(Course.code.asc()).all()
    examiners = ExaminerProfile.query.filter_by(status='Approved').order_by(ExaminerProfile.name.asc()).all()

    if request.method == 'POST':
        course_id = request.form.get('course_id')
        title = request.form.get('title', '').strip()
        exam_type = request.form.get('exam_type', 'Viva')
        total_marks = request.form.get('total_marks', 100)
        exam_date_str = request.form.get('exam_date')
        duration = request.form.get('duration_minutes', 30)
        description = request.form.get('description', '').strip()
        assigned_examiner_id = request.form.get('assigned_examiner_id') or None
        slot_creation_open = 'slot_creation_open' in request.form
        student_booking_open = 'student_booking_open' in request.form
        status = request.form.get('status', 'Published')

        if not course_id or not title or not exam_date_str:
            flash('Course, Title, and Examination Date are required.', 'danger')
            return render_template('admin/examination_form.html', action='Edit', exam=exam, courses=courses, examiners=examiners)

        try:
            exam.exam_date = datetime.strptime(exam_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format.', 'danger')
            return render_template('admin/examination_form.html', action='Edit', exam=exam, courses=courses, examiners=examiners)

        exam.course_id = int(course_id)
        exam.title = title
        exam.description = description
        exam.exam_type = exam_type
        exam.total_marks = float(total_marks)
        exam.duration_minutes = int(duration)
        exam.slot_creation_open = slot_creation_open
        exam.student_booking_open = student_booking_open
        exam.assigned_examiner_id = int(assigned_examiner_id) if assigned_examiner_id else None
        exam.status = status

        db.session.commit()
        flash(f'Examination "{exam.title}" updated successfully.', 'success')
        return redirect(url_for('admin.examinations'))

    return render_template('admin/examination_form.html', action='Edit', exam=exam, courses=courses, examiners=examiners)


@admin_bp.route('/examinations/<int:exam_id>/delete', methods=['POST'])
def delete_examination(exam_id):
    exam = Examination.query.get_or_404(exam_id)
    title = exam.title
    db.session.delete(exam)
    db.session.commit()
    flash(f'Examination "{title}" deleted successfully.', 'info')
    return redirect(url_for('admin.examinations'))


# ---------------- OPEN / CLOSE TOGGLES (CORE FEATURE) ----------------
@admin_bp.route('/examinations/<int:exam_id>/toggle-slot-creation', methods=['POST'])
def toggle_slot_creation(exam_id):
    exam = Examination.query.get_or_404(exam_id)
    exam.slot_creation_open = not exam.slot_creation_open
    db.session.commit()
    state = "OPENED" if exam.slot_creation_open else "CLOSED"
    flash(f'Slot creation for "{exam.title}" is now {state}.', 'info')
    return redirect(request.referrer or url_for('admin.examinations'))


@admin_bp.route('/examinations/<int:exam_id>/toggle-student-booking', methods=['POST'])
def toggle_student_booking(exam_id):
    exam = Examination.query.get_or_404(exam_id)
    exam.student_booking_open = not exam.student_booking_open
    db.session.commit()
    state = "OPENED" if exam.student_booking_open else "CLOSED"
    flash(f'Student slot booking for "{exam.title}" is now {state}.', 'info')
    return redirect(request.referrer or url_for('admin.examinations'))


# ---------------- RUBRICS MANAGEMENT ----------------
@admin_bp.route('/examinations/<int:exam_id>/rubrics', methods=['GET', 'POST'])
def examination_rubrics(exam_id):
    exam = Examination.query.get_or_404(exam_id)
    
    if request.method == 'POST':
        criterion_name = request.form.get('criterion_name', '').strip()
        max_marks_str = request.form.get('max_marks', '0').strip()
        description = request.form.get('description', '').strip()

        if not criterion_name or not max_marks_str:
            flash('Criterion name and maximum marks are required.', 'danger')
        else:
            try:
                max_marks = float(max_marks_str)
                rubric = ExaminationRubric(
                    exam_id=exam.id,
                    criterion_name=criterion_name,
                    max_marks=max_marks,
                    description=description
                )
                db.session.add(rubric)
                db.session.commit()
                flash(f'Rubric criterion "{criterion_name}" added.', 'success')
            except ValueError:
                flash('Invalid number for maximum marks.', 'danger')
        return redirect(url_for('admin.examination_rubrics', exam_id=exam.id))

    rubrics = exam.rubrics.all()
    total_rubric_marks = sum(r.max_marks for r in rubrics)
    return render_template('admin/rubrics.html', exam=exam, rubrics=rubrics, total_rubric_marks=total_rubric_marks)


@admin_bp.route('/rubrics/<int:rubric_id>/edit', methods=['POST'])
def edit_rubric(rubric_id):
    rubric = ExaminationRubric.query.get_or_404(rubric_id)
    exam_id = rubric.exam_id
    rubric.criterion_name = request.form.get('criterion_name', rubric.criterion_name).strip()
    try:
        rubric.max_marks = float(request.form.get('max_marks', rubric.max_marks))
    except ValueError:
        flash('Invalid value for maximum marks.', 'danger')
        return redirect(url_for('admin.examination_rubrics', exam_id=exam_id))
    rubric.description = request.form.get('description', rubric.description).strip()
    db.session.commit()
    flash('Rubric criterion updated successfully.', 'success')
    return redirect(url_for('admin.examination_rubrics', exam_id=exam_id))


@admin_bp.route('/rubrics/<int:rubric_id>/delete', methods=['POST'])
def delete_rubric(rubric_id):
    rubric = ExaminationRubric.query.get_or_404(rubric_id)
    exam_id = rubric.exam_id
    db.session.delete(rubric)
    db.session.commit()
    flash('Rubric criterion deleted successfully.', 'info')
    return redirect(url_for('admin.examination_rubrics', exam_id=exam_id))


# ---------------- EXAMINER APPROVAL & MANAGEMENT ----------------
@admin_bp.route('/examiners')
def examiners():
    status_filter = request.args.get('status', 'all')
    search_query = request.args.get('q', '').strip()

    query = ExaminerProfile.query.join(User)
    if status_filter != 'all':
        query = query.filter(ExaminerProfile.status == status_filter)
    if search_query:
        query = query.filter(
            (ExaminerProfile.name.ilike(f'%{search_query}%')) |
            (ExaminerProfile.examiner_id.ilike(f'%{search_query}%')) |
            (ExaminerProfile.department.ilike(f'%{search_query}%')) |
            (User.email.ilike(f'%{search_query}%'))
        )
    examiner_list = query.order_by(ExaminerProfile.id.desc()).all()
    pending_count = ExaminerProfile.query.filter_by(status='Pending').count()

    return render_template(
        'admin/examiners.html',
        examiners=examiner_list,
        status_filter=status_filter,
        search_query=search_query,
        pending_count=pending_count
    )


@admin_bp.route('/examiners/<int:examiner_id>/approve', methods=['POST'])
def approve_examiner(examiner_id):
    examiner = ExaminerProfile.query.get_or_404(examiner_id)
    examiner.status = 'Approved'
    examiner.approved_at = datetime.utcnow()
    db.session.commit()
    notify_examiner_approval(examiner, approved=True)
    flash(f'Examiner {examiner.name} ({examiner.examiner_id}) has been Approved.', 'success')
    return redirect(url_for('admin.examiners'))


@admin_bp.route('/examiners/<int:examiner_id>/reject', methods=['POST'])
def reject_examiner(examiner_id):
    examiner = ExaminerProfile.query.get_or_404(examiner_id)
    examiner.status = 'Rejected'
    db.session.commit()
    notify_examiner_approval(examiner, approved=False)
    flash(f'Examiner {examiner.name} has been Rejected.', 'warning')
    return redirect(url_for('admin.examiners'))


# ---------------- STUDENTS MANAGEMENT & SEARCH ----------------
@admin_bp.route('/students')
def students():
    search_query = request.args.get('q', '').strip()
    query = StudentProfile.query.join(User)
    if search_query:
        query = query.filter(
            (StudentProfile.name.ilike(f'%{search_query}%')) |
            (StudentProfile.student_id.ilike(f'%{search_query}%')) |
            (StudentProfile.department.ilike(f'%{search_query}%')) |
            (User.email.ilike(f'%{search_query}%'))
        )
    student_list = query.order_by(StudentProfile.student_id.asc()).all()
    return render_template('admin/students.html', students=student_list, search_query=search_query)


# ---------------- SLOTS VIEW & ASSIGNMENT CHANGE ----------------
@admin_bp.route('/slots')
def slots():
    exam_filter = request.args.get('exam_id', type=int)
    examiner_filter = request.args.get('examiner_id', type=int)
    
    query = ExaminationSlot.query
    if exam_filter:
        query = query.filter_by(exam_id=exam_filter)
    if examiner_filter:
        query = query.filter_by(examiner_id=examiner_filter)
        
    slots_list = query.order_by(ExaminationSlot.slot_date.desc(), ExaminationSlot.start_time.asc()).all()
    examinations = Examination.query.order_by(Examination.title.asc()).all()
    approved_examiners = ExaminerProfile.query.filter_by(status='Approved').all()

    return render_template(
        'admin/slots.html',
        slots=slots_list,
        examinations=examinations,
        examiners=approved_examiners,
        selected_exam_id=exam_filter,
        selected_examiner_id=examiner_filter
    )


@admin_bp.route('/slots/<int:slot_id>/change-examiner', methods=['POST'])
def change_slot_examiner(slot_id):
    """
    Specification: Admin can change examiner assignment if required.
    """
    slot = ExaminationSlot.query.get_or_404(slot_id)
    new_examiner_id = request.form.get('new_examiner_id', type=int)
    new_examiner = ExaminerProfile.query.get_or_404(new_examiner_id)

    old_examiner_name = slot.examiner.name
    slot.examiner_id = new_examiner.id
    db.session.commit()
    flash(f'Slot on {slot.slot_date} reassigned from {old_examiner_name} to {new_examiner.name}.', 'success')
    return redirect(url_for('admin.slots'))


# ---------------- BOOKINGS VIEW & RESCHEDULING ----------------
@admin_bp.route('/bookings')
def bookings():
    status_filter = request.args.get('status', 'all')
    search_query = request.args.get('q', '').strip()

    query = Booking.query.join(StudentProfile).join(Examination)
    if status_filter != 'all':
        query = query.filter(Booking.status == status_filter)
    if search_query:
        query = query.filter(
            (StudentProfile.name.ilike(f'%{search_query}%')) |
            (StudentProfile.student_id.ilike(f'%{search_query}%')) |
            (Examination.title.ilike(f'%{search_query}%'))
        )
    bookings_list = query.order_by(Booking.booking_date.desc()).all()
    return render_template('admin/bookings.html', bookings=bookings_list, status_filter=status_filter, search_query=search_query)


@admin_bp.route('/bookings/<int:booking_id>/reschedule', methods=['GET', 'POST'])
def reschedule_booking(booking_id):
    """
    Specification: Admin can reschedule examination bookings.
    """
    booking = Booking.query.get_or_404(booking_id)
    current_slot = booking.slot
    exam = booking.examination

    # Available alternative slots for this examination that have free capacity
    available_slots = ExaminationSlot.query.filter(
        ExaminationSlot.exam_id == exam.id,
        ExaminationSlot.id != current_slot.id,
        ExaminationSlot.status == 'Open'
    ).all()
    # Filter only slots with remaining capacity
    available_slots = [s for s in available_slots if s.current_bookings < s.capacity]

    if request.method == 'POST':
        new_slot_id = request.form.get('new_slot_id', type=int)
        if not new_slot_id:
            flash('Please select an available slot to reschedule.', 'danger')
            return redirect(url_for('admin.reschedule_booking', booking_id=booking.id))

        new_slot = ExaminationSlot.query.get_or_404(new_slot_id)
        if new_slot.current_bookings >= new_slot.capacity:
            flash('The selected slot has reached maximum capacity.', 'danger')
            return redirect(url_for('admin.reschedule_booking', booking_id=booking.id))

        old_slot = current_slot
        
        # Move booking to new slot
        booking.slot_id = new_slot.id
        booking.status = 'Rescheduled'
        
        # Update capacities
        old_slot.update_status()
        new_slot.update_status()
        db.session.commit()

        # Send reschedule notification
        notify_booking_reschedule(booking, old_slot, new_slot)

        flash(f'Booking #{booking.id} for {booking.student.name} rescheduled successfully to {new_slot.slot_date} {new_slot.start_time}.', 'success')
        return redirect(url_for('admin.bookings'))

    return render_template('admin/reschedule.html', booking=booking, current_slot=current_slot, available_slots=available_slots)


# ---------------- HISTORICAL EXAMINATION DATA ----------------
@admin_bp.route('/historical')
def historical():
    """
    Specification: Allow Admin to view all historical examination data.
    """
    past_exams = Examination.query.order_by(Examination.exam_date.desc()).all()
    completed_bookings = Booking.query.filter(Booking.status.in_(['Completed', 'Booked'])).order_by(Booking.booking_date.desc()).all()
    cancelled_bookings = Booking.query.filter_by(status='Cancelled').all()

    avg_marks = 0.0
    evaluated = [b for b in completed_bookings if b.marks_obtained is not None]
    if evaluated:
        avg_marks = round(sum(b.marks_obtained for b in evaluated) / len(evaluated), 2)

    return render_template(
        'admin/historical.html',
        examinations=past_exams,
        completed_bookings=completed_bookings,
        cancelled_bookings=cancelled_bookings,
        evaluated_count=len(evaluated),
        avg_marks=avg_marks
    )

