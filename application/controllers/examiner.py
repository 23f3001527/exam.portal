from datetime import datetime, date, time
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from application.models import (
    db, Examination, ExaminationSlot, Booking, ExaminationRubric, 
    RubricScore, ExaminerProfile
)
from application.utils.auth_decorators import examiner_required
from application.utils.email_service import notify_result_published

examiner_bp = Blueprint('examiner', __name__)

@examiner_bp.before_request
@login_required
@examiner_required
def check_examiner():
    pass


@examiner_bp.route('/dashboard')
def dashboard():
    profile = current_user.examiner_profile

    # Assigned examinations
    assigned_exams = Examination.query.filter(
        (Examination.assigned_examiner_id == profile.id) | 
        (Examination.status == 'Published')
    ).all()

    # Created examination slots
    created_slots = profile.created_slots.order_by(
        ExaminationSlot.slot_date.desc(), ExaminationSlot.start_time.desc()
    ).all()

    # Total students booked in examiner's slots
    slot_ids = [s.id for s in created_slots]
    booked_students_count = Booking.query.filter(
        Booking.slot_id.in_(slot_ids),
        Booking.status.in_(['Booked', 'Completed', 'Rescheduled'])
    ).count() if slot_ids else 0

    # Pending evaluations
    pending_evaluations = Booking.query.filter(
        Booking.slot_id.in_(slot_ids),
        Booking.status.in_(['Booked', 'Rescheduled']),
        Booking.result_published == False
    ).order_by(Booking.booking_date.asc()).all() if slot_ids else []

    return render_template(
        'examiner/dashboard.html',
        profile=profile,
        assigned_exams=assigned_exams,
        created_slots=created_slots,
        total_slots=len(created_slots),
        booked_students_count=booked_students_count,
        pending_evaluations_count=len(pending_evaluations),
        pending_evaluations=pending_evaluations[:5]
    )


# ---------------- SLOT CREATION & MANAGEMENT ----------------
@examiner_bp.route('/slots')
def slots():
    profile = current_user.examiner_profile
    my_slots = profile.created_slots.order_by(
        ExaminationSlot.slot_date.desc(), ExaminationSlot.start_time.asc()
    ).all()
    
    # Available exams for creating slots (where slot_creation_open is True)
    available_exams = Examination.query.filter_by(slot_creation_open=True, status='Published').all()

    return render_template('examiner/slots.html', slots=my_slots, available_exams=available_exams)


@examiner_bp.route('/slots/new', methods=['GET', 'POST'])
def create_slot():
    profile = current_user.examiner_profile
    
    # Allowed examinations (must have slot_creation_open == True)
    available_exams = Examination.query.filter_by(slot_creation_open=True, status='Published').all()

    if request.method == 'POST':
        exam_id = request.form.get('exam_id', type=int)
        slot_date_str = request.form.get('slot_date')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        capacity_str = request.form.get('capacity', '1')
        location_or_link = request.form.get('location_or_link', '').strip()

        exam = Examination.query.get(exam_id)
        if not exam:
            flash('Selected examination does not exist.', 'danger')
            return redirect(url_for('examiner.create_slot'))

        # CORE RULE: Examiners can create slots only during slot creation period
        if not exam.slot_creation_open:
            flash(f'Slot creation for "{exam.title}" is currently closed by the Administrator.', 'danger')
            return redirect(url_for('examiner.slots'))

        try:
            slot_date = datetime.strptime(slot_date_str, '%Y-%m-%d').date()
            start_time = datetime.strptime(start_time_str, '%H:%M').time()
            end_time = datetime.strptime(end_time_str, '%H:%M').time()
            capacity = int(capacity_str)
        except (ValueError, TypeError):
            flash('Invalid date, time, or capacity entered.', 'danger')
            return render_template('examiner/slot_form.html', action='Create', slot=None, exams=available_exams)

        if start_time >= end_time:
            flash('Slot start time must be before end time.', 'danger')
            return render_template('examiner/slot_form.html', action='Create', slot=None, exams=available_exams)

        if capacity < 1:
            flash('Slot capacity must be at least 1.', 'danger')
            return render_template('examiner/slot_form.html', action='Create', slot=None, exams=available_exams)

        slot = ExaminationSlot(
            exam_id=exam.id,
            examiner_id=profile.id,
            slot_date=slot_date,
            start_time=start_time,
            end_time=end_time,
            capacity=capacity,
            current_bookings=0,
            status='Open',
            location_or_link=location_or_link
        )
        db.session.add(slot)
        db.session.commit()

        flash(f'Examination slot for {slot_date} ({start_time.strftime("%I:%M %p")}) created successfully.', 'success')
        return redirect(url_for('examiner.slots'))

    return render_template('examiner/slot_form.html', action='Create', slot=None, exams=available_exams)


@examiner_bp.route('/slots/<int:slot_id>/edit', methods=['GET', 'POST'])
def edit_slot(slot_id):
    profile = current_user.examiner_profile
    slot = ExaminationSlot.query.get_or_404(slot_id)

    # Security check: Must belong to current examiner
    if slot.examiner_id != profile.id:
        abort(403)

    # Specification: Update slots before booking starts (e.g. if no bookings yet or exam slot creation open)
    active_bookings = slot.bookings.filter(Booking.status.in_(['Booked', 'Completed', 'Rescheduled'])).count()
    if active_bookings > 0:
        flash('This slot already has student bookings and cannot be edited. Please coordinate with Admin if rescheduling is required.', 'warning')
        return redirect(url_for('examiner.slots'))

    available_exams = Examination.query.filter_by(slot_creation_open=True, status='Published').all()

    if request.method == 'POST':
        slot_date_str = request.form.get('slot_date')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        capacity_str = request.form.get('capacity', '1')
        location_or_link = request.form.get('location_or_link', '').strip()

        try:
            slot.slot_date = datetime.strptime(slot_date_str, '%Y-%m-%d').date()
            slot.start_time = datetime.strptime(start_time_str, '%H:%M').time()
            slot.end_time = datetime.strptime(end_time_str, '%H:%M').time()
            slot.capacity = int(capacity_str)
            slot.location_or_link = location_or_link
        except (ValueError, TypeError):
            flash('Invalid date, time, or capacity.', 'danger')
            return render_template('examiner/slot_form.html', action='Edit', slot=slot, exams=available_exams)

        slot.update_status()
        db.session.commit()
        flash('Slot updated successfully.', 'success')
        return redirect(url_for('examiner.slots'))

    return render_template('examiner/slot_form.html', action='Edit', slot=slot, exams=available_exams)


@examiner_bp.route('/slots/<int:slot_id>/delete', methods=['POST'])
def delete_slot(slot_id):
    profile = current_user.examiner_profile
    slot = ExaminationSlot.query.get_or_404(slot_id)

    if slot.examiner_id != profile.id:
        abort(403)

    active_bookings = slot.bookings.filter(Booking.status.in_(['Booked', 'Completed', 'Rescheduled'])).count()
    if active_bookings > 0:
        flash('Cannot delete slot with existing student bookings. Please contact Admin.', 'danger')
        return redirect(url_for('examiner.slots'))

    db.session.delete(slot)
    db.session.commit()
    flash('Examination slot deleted successfully.', 'info')
    return redirect(url_for('examiner.slots'))


# ---------------- BOOKED STUDENTS & EVALUATION ----------------
@examiner_bp.route('/bookings')
def bookings():
    profile = current_user.examiner_profile
    slot_ids = [s.id for s in profile.created_slots.all()]

    status_filter = request.args.get('status', 'all')
    search_query = request.args.get('q', '').strip()

    query = Booking.query.filter(Booking.slot_id.in_(slot_ids)) if slot_ids else Booking.query.filter(False)

    if status_filter != 'all':
        query = query.filter(Booking.status == status_filter)
    
    if search_query:
        query = query.join(Booking.student).filter(
            (Booking.student.has(name=search_query)) |
            (Booking.student.has(student_id=search_query))
        )

    bookings_list = query.order_by(Booking.booking_date.desc()).all()
    return render_template('examiner/bookings.html', bookings=bookings_list, status_filter=status_filter, search_query=search_query)


@examiner_bp.route('/evaluate/<int:booking_id>', methods=['GET', 'POST'])
def evaluate(booking_id):
    profile = current_user.examiner_profile
    booking = Booking.query.get_or_404(booking_id)

    # CORE SPECIFICATION RULE:
    # "Ensure examiners can evaluate only students booked into their own slots."
    if booking.slot.examiner_id != profile.id:
        abort(403)

    exam = booking.examination
    rubrics = exam.rubrics.all()

    # Existing rubric scores dictionary
    existing_scores = {rs.rubric_id: rs for rs in booking.rubric_scores.all()}

    if request.method == 'POST':
        remarks = request.form.get('remarks', '').strip()
        publish_now = 'publish' in request.form

        # Evaluate each rubric criterion
        total_score = 0.0
        for rubric in rubrics:
            field_name = f'rubric_{rubric.id}'
            remarks_field = f'remarks_{rubric.id}'
            score_val_str = request.form.get(field_name, '0').strip()
            crit_remarks = request.form.get(remarks_field, '').strip()

            try:
                score_val = float(score_val_str)
            except ValueError:
                score_val = 0.0

            # Clamp between 0 and max_marks
            score_val = max(0.0, min(score_val, rubric.max_marks))
            total_score += score_val

            if rubric.id in existing_scores:
                rs = existing_scores[rubric.id]
                rs.score = score_val
                rs.remarks = crit_remarks
            else:
                rs = RubricScore(
                    booking_id=booking.id,
                    rubric_id=rubric.id,
                    score=score_val,
                    remarks=crit_remarks
                )
                db.session.add(rs)

        booking.marks_obtained = round(total_score, 2)
        if exam.total_marks > 0:
            booking.percentage = round((total_score / exam.total_marks) * 100, 2)
        else:
            booking.percentage = 0.0

        booking.evaluation_remarks = remarks
        booking.evaluated_by = profile.id
        booking.evaluation_date = datetime.utcnow()
        booking.status = 'Completed'
        booking.result_published = True  # Specification: Submit marks and remarks / publish

        db.session.commit()

        # Send notification to student
        notify_result_published(booking)

        flash(f'Evaluation submitted for {booking.student.name} ({booking.student.student_id}). Total Marks: {booking.marks_obtained}/{exam.total_marks}.', 'success')
        return redirect(url_for('examiner.bookings'))

    return render_template(
        'examiner/evaluate.html',
        booking=booking,
        exam=exam,
        rubrics=rubrics,
        existing_scores=existing_scores
    )

