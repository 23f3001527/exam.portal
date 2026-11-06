from datetime import datetime
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from application.models import (
    db, Course, Examination, ExaminationSlot, Booking, 
    ExaminerProfile, StudentProfile, ExaminationRubric
)
from application.utils.auth_decorators import admin_required
from application.utils.email_service import notify_booking_confirmation, notify_booking_cancellation

api_bp = Blueprint('api', __name__)

@api_bp.route('/examinations', methods=['GET'])
def get_examinations():
    course_id = request.args.get('course_id', type=int)
    status = request.args.get('status')
    
    query = Examination.query
    if course_id:
        query = query.filter_by(course_id=course_id)
    if status:
        query = query.filter_by(status=status)

    exams = query.order_by(Examination.exam_date.asc()).all()
    results = []
    for e in exams:
        results.append({
            'id': e.id,
            'title': e.title,
            'course_code': e.course.code,
            'course_name': e.course.name,
            'exam_type': e.exam_type,
            'total_marks': e.total_marks,
            'exam_date': e.exam_date.strftime('%Y-%m-%d'),
            'duration_minutes': e.duration_minutes,
            'slot_creation_open': e.slot_creation_open,
            'student_booking_open': e.student_booking_open,
            'assigned_examiner': e.assigned_examiner.name if e.assigned_examiner else None,
            'slots_count': e.slots.count(),
            'total_rubric_marks': e.rubric_total()
        })
    return jsonify({'examinations': results, 'count': len(results)})


@api_bp.route('/examinations/<int:exam_id>', methods=['GET'])
def get_examination(exam_id):
    exam = Examination.query.get_or_404(exam_id)
    slots = []
    for s in exam.slots:
        slots.append({
            'id': s.id,
            'examiner_name': s.examiner.name,
            'slot_date': s.slot_date.strftime('%Y-%m-%d'),
            'start_time': s.start_time.strftime('%H:%M'),
            'end_time': s.end_time.strftime('%H:%M'),
            'capacity': s.capacity,
            'current_bookings': s.current_bookings,
            'status': s.status,
            'location_or_link': s.location_or_link
        })

    rubrics = []
    for r in exam.rubrics:
        rubrics.append({
            'id': r.id,
            'criterion_name': r.criterion_name,
            'max_marks': r.max_marks,
            'description': r.description
        })

    return jsonify({
        'id': exam.id,
        'title': exam.title,
        'description': exam.description,
        'course': {
            'id': exam.course.id,
            'code': exam.course.code,
            'name': exam.course.name,
            'department': exam.course.department
        },
        'exam_date': exam.exam_date.strftime('%Y-%m-%d'),
        'total_marks': exam.total_marks,
        'slot_creation_open': exam.slot_creation_open,
        'student_booking_open': exam.student_booking_open,
        'rubrics': rubrics,
        'slots': slots
    })


@api_bp.route('/examiners', methods=['GET'])
def get_examiners():
    status = request.args.get('status', 'Approved')
    query = ExaminerProfile.query
    if status != 'all':
        query = query.filter_by(status=status)
    examiners = query.order_by(ExaminerProfile.name.asc()).all()

    results = []
    for ex in examiners:
        results.append({
            'id': ex.id,
            'examiner_id': ex.examiner_id,
            'name': ex.name,
            'email': ex.user.email,
            'department': ex.department,
            'status': ex.status,
            'slots_created': ex.created_slots.count()
        })
    return jsonify({'examiners': results, 'count': len(results)})


@api_bp.route('/students', methods=['GET'])
@login_required
@admin_required
def get_students():
    students = StudentProfile.query.order_by(StudentProfile.student_id.asc()).all()
    results = []
    for s in students:
        results.append({
            'id': s.id,
            'student_id': s.student_id,
            'name': s.name,
            'email': s.user.email,
            'department': s.department,
            'contact_details': s.contact_details,
            'bookings_count': s.bookings.count()
        })
    return jsonify({'students': results, 'count': len(results)})


@api_bp.route('/bookings', methods=['GET'])
@login_required
def get_bookings():
    if current_user.is_admin:
        bookings = Booking.query.order_by(Booking.booking_date.desc()).all()
    elif current_user.is_student:
        bookings = current_user.student_profile.bookings.order_by(Booking.booking_date.desc()).all()
    elif current_user.is_examiner:
        slot_ids = [s.id for s in current_user.examiner_profile.created_slots]
        bookings = Booking.query.filter(Booking.slot_id.in_(slot_ids)).order_by(Booking.booking_date.desc()).all()
    else:
        return jsonify({'error': 'Unauthorized'}), 403

    results = []
    for b in bookings:
        results.append({
            'id': b.id,
            'student_name': b.student.name,
            'student_id': b.student.student_id,
            'examination': b.examination.title,
            'course_code': b.examination.course.code,
            'slot_date': b.slot.slot_date.strftime('%Y-%m-%d'),
            'slot_time': f"{b.slot.start_time.strftime('%H:%M')} - {b.slot.end_time.strftime('%H:%M')}",
            'examiner_name': b.slot.examiner.name,
            'status': b.status,
            'marks_obtained': b.marks_obtained,
            'percentage': b.percentage,
            'result_published': b.result_published
        })
    return jsonify({'bookings': results, 'count': len(results)})


@api_bp.route('/bookings', methods=['POST'])
@login_required
def create_booking_api():
    if not current_user.is_student:
        return jsonify({'error': 'Only registered students can book slots'}), 403

    profile = current_user.student_profile
    data = request.get_json() or {}
    slot_id = data.get('slot_id')

    if not slot_id:
        return jsonify({'error': 'slot_id is required'}), 400

    slot = ExaminationSlot.query.get(slot_id)
    if not slot:
        return jsonify({'error': 'Slot not found'}), 404

    exam = slot.examination
    if not exam.student_booking_open:
        return jsonify({'error': 'Student booking is closed for this examination'}), 400

    # Duplicate check
    existing = Booking.query.filter(
        Booking.student_id == profile.id,
        Booking.exam_id == exam.id,
        Booking.status.in_(['Booked', 'Rescheduled', 'Completed'])
    ).first()
    if existing:
        return jsonify({'error': f'You already have an active booking (#{existing.id}) for this examination.'}), 400

    # Overbooking check
    slot.update_status()
    if slot.current_bookings >= slot.capacity or slot.status in ['Full', 'Closed']:
        return jsonify({'error': 'Slot is already at full capacity'}), 400

    booking = Booking(
        student_id=profile.id,
        slot_id=slot.id,
        exam_id=exam.id,
        booking_date=datetime.utcnow(),
        status='Booked'
    )
    db.session.add(booking)
    db.session.flush()

    slot.update_status()
    db.session.commit()

    notify_booking_confirmation(booking)

    return jsonify({
        'message': 'Slot booked successfully',
        'booking_id': booking.id,
        'status': booking.status
    }), 201


@api_bp.route('/stats', methods=['GET'])
@login_required
@admin_required
def get_statistics():
    completed = Booking.query.filter_by(status='Completed').count()
    active = Booking.query.filter(Booking.status.in_(['Booked', 'Rescheduled'])).count()
    cancelled = Booking.query.filter_by(status='Cancelled').count()

    examiners = ExaminerProfile.query.filter_by(status='Approved').all()
    workload = []
    for ex in examiners:
        slots_count = ex.created_slots.count()
        bookings_count = sum(s.current_bookings for s in ex.created_slots)
        workload.append({
            'name': ex.name,
            'department': ex.department,
            'slots': slots_count,
            'bookings': bookings_count
        })

    return jsonify({
        'summary': {
            'courses': Course.query.count(),
            'examinations': Examination.query.count(),
            'examiners': ExaminerProfile.query.count(),
            'students': StudentProfile.query.count(),
            'slots': ExaminationSlot.query.count(),
            'bookings': Booking.query.count(),
        },
        'booking_status_distribution': {
            'completed': completed,
            'active': active,
            'cancelled': cancelled
        },
        'examiner_workload': workload
    })

