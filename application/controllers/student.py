from datetime import datetime, date
from flask import (
    Blueprint, render_template, request, redirect, url_for, 
    flash, abort, Response, current_app
)
from flask_login import login_required, current_user
from application.models import (
    db, Examination, ExaminationSlot, Booking, Course, StudentProfile, User
)
from application.utils.auth_decorators import student_required
from application.utils.email_service import (
    notify_booking_confirmation, notify_booking_cancellation
)
from application.utils.pdf_generator import generate_scorecard_pdf

student_bp = Blueprint('student', __name__)

@student_bp.before_request
@login_required
@student_required
def check_student():
    pass


@student_bp.route('/dashboard')
def dashboard():
    profile = current_user.student_profile
    today = datetime.utcnow().date()

    # 1. Available examinations (student booking open)
    available_exams = Examination.query.filter_by(
        student_booking_open=True, status='Published'
    ).order_by(Examination.exam_date.asc()).all()

    # 2. Student's existing bookings
    all_bookings = profile.bookings.all()
    
    # Existing active booked exam IDs to prevent duplicates and indicate status
    booked_exam_ids = {
        b.exam_id for b in all_bookings 
        if b.status in ['Booked', 'Rescheduled', 'Completed']
    }

    # 3. Upcoming examinations booked by student
    upcoming_bookings = [
        b for b in all_bookings 
        if b.status in ['Booked', 'Rescheduled'] and b.slot.slot_date >= today
    ]
    upcoming_bookings.sort(key=lambda b: (b.slot.slot_date, b.slot.start_time))

    # 4. Booked slots
    active_booked_slots = [
        b for b in all_bookings if b.status in ['Booked', 'Rescheduled']
    ]

    # 5. Published results
    published_results = [
        b for b in all_bookings if b.result_published and b.status == 'Completed'
    ]

    return render_template(
        'student/dashboard.html',
        profile=profile,
        available_exams=available_exams,
        booked_exam_ids=booked_exam_ids,
        upcoming_bookings=upcoming_bookings,
        active_booked_slots=active_booked_slots,
        published_results=published_results
    )


# ---------------- SEARCH & EXPLORE EXAMINATIONS ----------------
@student_bp.route('/examinations')
def examinations():
    search_query = request.args.get('q', '').strip()
    profile = current_user.student_profile

    query = Examination.query.join(Course).filter(Examination.status == 'Published')
    if search_query:
        query = query.filter(
            (Examination.title.ilike(f'%{search_query}%')) |
            (Course.name.ilike(f'%{search_query}%')) |
            (Course.code.ilike(f'%{search_query}%')) |
            (Course.department.ilike(f'%{search_query}%'))
        )
    exams = query.order_by(Examination.exam_date.asc()).all()

    booked_exam_ids = {
        b.exam_id for b in profile.bookings 
        if b.status in ['Booked', 'Rescheduled', 'Completed']
    }

    return render_template(
        'student/examinations.html',
        examinations=exams,
        search_query=search_query,
        booked_exam_ids=booked_exam_ids
    )


# ---------------- BOOKING SLOTS ----------------
@student_bp.route('/examinations/<int:exam_id>/slots')
def exam_slots(exam_id):
    exam = Examination.query.get_or_404(exam_id)
    profile = current_user.student_profile

    # Check if student already has active booking for this exam
    existing_booking = Booking.query.filter(
        Booking.student_id == profile.id,
        Booking.exam_id == exam.id,
        Booking.status.in_(['Booked', 'Rescheduled', 'Completed'])
    ).first()

    # Slots available for this exam
    slots = exam.slots.order_by(ExaminationSlot.slot_date.asc(), ExaminationSlot.start_time.asc()).all()

    return render_template(
        'student/book_slot.html',
        exam=exam,
        slots=slots,
        existing_booking=existing_booking
    )


@student_bp.route('/slots/<int:slot_id>/book', methods=['POST'])
def book_slot(slot_id):
    profile = current_user.student_profile
    slot = ExaminationSlot.query.get_or_404(slot_id)
    exam = slot.examination

    # CORE RULE 1: Students can book slots ONLY during the booking period
    if not exam.student_booking_open:
        flash(f'Slot booking for "{exam.title}" is currently closed by the Administration.', 'danger')
        return redirect(url_for('student.exam_slots', exam_id=exam.id))

    # CORE RULE 2: Prevent duplicate bookings for the same examination
    existing_booking = Booking.query.filter(
        Booking.student_id == profile.id,
        Booking.exam_id == exam.id,
        Booking.status.in_(['Booked', 'Rescheduled', 'Completed'])
    ).first()

    if existing_booking:
        flash(f'You already have an active booking (ID #{existing_booking.id}) for "{exam.title}". Duplicate bookings are not allowed.', 'warning')
        return redirect(url_for('student.exam_slots', exam_id=exam.id))

    # CORE RULE 3: Prevent overbooking beyond slot capacity
    # Refresh active booking count
    slot.update_status()
    if slot.current_bookings >= slot.capacity or slot.status in ['Full', 'Closed']:
        flash('This slot has just reached full capacity. Please choose another slot.', 'danger')
        return redirect(url_for('student.exam_slots', exam_id=exam.id))

    # Create new booking
    booking = Booking(
        student_id=profile.id,
        slot_id=slot.id,
        exam_id=exam.id,
        booking_date=datetime.utcnow(),
        status='Booked'
    )
    db.session.add(booking)
    db.session.flush()

    # Update slot count and automatically close if capacity is reached
    slot.update_status()
    db.session.commit()

    # Send email notification
    notify_booking_confirmation(booking)

    flash(f'Slot booked successfully! An email confirmation has been dispatched. Booking ID: #{booking.id}', 'success')
    return redirect(url_for('student.booking_history'))


# ---------------- CANCEL BOOKING ----------------
@student_bp.route('/bookings/<int:booking_id>/cancel', methods=['POST'])
def cancel_booking(booking_id):
    profile = current_user.student_profile
    booking = Booking.query.get_or_404(booking_id)

    # Security check: Must belong to current student
    if booking.student_id != profile.id:
        abort(403)

    if booking.status != 'Booked' and booking.status != 'Rescheduled':
        flash('Only active bookings can be cancelled.', 'warning')
        return redirect(url_for('student.booking_history'))

    # Check deadline: e.g. before slot start time
    slot = booking.slot
    slot_datetime = datetime.combine(slot.slot_date, slot.start_time)
    if datetime.utcnow() > slot_datetime:
        flash('Booking deadline has passed. Past or ongoing examination slots cannot be cancelled.', 'danger')
        return redirect(url_for('student.booking_history'))

    # CORE RULE: Maintain complete booking history for every student (status -> Cancelled, not deleted!)
    booking.status = 'Cancelled'
    slot.update_status()
    db.session.commit()

    # Send cancellation email notification
    notify_booking_cancellation(booking)

    flash(f'Booking #{booking.id} has been cancelled. Your slot has been released.', 'info')
    return redirect(url_for('student.booking_history'))


# ---------------- BOOKING HISTORY ----------------
@student_bp.route('/history')
def booking_history():
    profile = current_user.student_profile
    # Complete booking history for student (Booked, Cancelled, Completed, Rescheduled)
    bookings = profile.bookings.order_by(Booking.booking_date.desc()).all()
    return render_template('student/booking_history.html', bookings=bookings)


# ---------------- SCHEDULE VIEW ----------------
@student_bp.route('/schedule')
def schedule():
    profile = current_user.student_profile
    bookings = profile.bookings.filter(
        Booking.status.in_(['Booked', 'Rescheduled', 'Completed'])
    ).order_by(Booking.booking_date.asc()).all()

    return render_template('student/schedule.html', bookings=bookings)


# ---------------- SCORECARD & RESULTS ----------------
@student_bp.route('/scorecard/<int:booking_id>')
def view_scorecard(booking_id):
    profile = current_user.student_profile
    booking = Booking.query.get_or_404(booking_id)

    if booking.student_id != profile.id and not current_user.is_admin:
        abort(403)

    if not booking.result_published and not current_user.is_admin:
        flash('Results for this examination have not been published yet.', 'info')
        return redirect(url_for('student.dashboard'))

    return render_template('student/scorecard_view.html', booking=booking)


@student_bp.route('/scorecard/<int:booking_id>/download')
def download_scorecard(booking_id):
    profile = current_user.student_profile
    booking = Booking.query.get_or_404(booking_id)

    if booking.student_id != profile.id and not current_user.is_admin:
        abort(403)

    if not booking.result_published and not current_user.is_admin:
        flash('Scorecard cannot be downloaded until results are published.', 'warning')
        return redirect(url_for('student.dashboard'))

    # Generate pure PDF bytes
    pdf_bytes = generate_scorecard_pdf(booking)
    filename = f"Scorecard_{booking.student.student_id}_{booking.examination.course.code}_{booking.id}.pdf"

    return Response(
        pdf_bytes,
        mimetype='application/pdf',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Type': 'application/pdf'
        }
    )


# ---------------- PROFILE MANAGEMENT ----------------
@student_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    profile = current_user.student_profile
    user = current_user

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        contact = request.form.get('contact', '').strip()
        department = request.form.get('department', '').strip()
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not name or not department:
            flash('Name and Department are required.', 'danger')
            return render_template('student/profile.html', profile=profile)

        profile.name = name
        profile.contact_details = contact
        profile.department = department

        if new_password:
            if len(new_password) < 6:
                flash('New password must be at least 6 characters long.', 'danger')
                return render_template('student/profile.html', profile=profile)
            if new_password != confirm_password:
                flash('Passwords do not match.', 'danger')
                return render_template('student/profile.html', profile=profile)
            user.set_password(new_password)

        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('student.profile'))

    return render_template('student/profile.html', profile=profile)

