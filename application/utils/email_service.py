import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from flask import current_app
from application.models import db, Notification

def send_notification(user, subject, body, notification_type='General'):
    """
    Records an email notification in the database for tracking and UI display,
    and attempts to send real email if SMTP credentials are provided.
    """
    if not user:
        return None

    email_to = user.email
    notif = Notification(
        user_id=user.id,
        email_to=email_to,
        subject=subject,
        body=body,
        notification_type=notification_type,
        sent_at=datetime.utcnow()
    )
    db.session.add(notif)
    db.session.commit()

    # Optional real SMTP sending
    mail_server = current_app.config.get('MAIL_SERVER')
    mail_username = current_app.config.get('MAIL_USERNAME')
    mail_password = current_app.config.get('MAIL_PASSWORD')
    
    if mail_server and mail_username and mail_password:
        try:
            port = current_app.config.get('MAIL_PORT', 587)
            sender = current_app.config.get('MAIL_DEFAULT_SENDER', mail_username)
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = sender
            msg['To'] = email_to
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(mail_server, port, timeout=5) as server:
                if current_app.config.get('MAIL_USE_TLS', True):
                    server.starttls()
                server.login(mail_username, mail_password)
                server.send_message(msg)
        except Exception as e:
            # We log or silently pass so local testing is never blocked
            current_app.logger.warning(f"SMTP dispatch note: {e}")

    return notif

def notify_booking_confirmation(booking):
    student_user = booking.student.user
    slot = booking.slot
    exam = booking.examination
    course = exam.course
    examiner_name = slot.examiner.name

    subject = f"Booking Confirmation: {exam.title} ({course.code})"
    body = (
        f"Dear {booking.student.name},\n\n"
        f"Your examination slot booking has been confirmed successfully.\n\n"
        f"--- Examination Details ---\n"
        f"Course: {course.name} ({course.code})\n"
        f"Examination: {exam.title}\n"
        f"Slot Date: {slot.slot_date.strftime('%A, %d %B %Y')}\n"
        f"Time: {slot.start_time.strftime('%I:%M %p')} - {slot.end_time.strftime('%I:%M %p')}\n"
        f"Examiner: {examiner_name} ({slot.examiner.department})\n"
        f"Venue / Link: {slot.location_or_link or 'TBA'}\n"
        f"Booking ID: #{booking.id}\n\n"
        f"Please be present 5 minutes prior to your allocated slot.\n\n"
        f"Regards,\n"
        f"Examination Management System Office"
    )
    return send_notification(student_user, subject, body, 'Booking Confirmation')

def notify_booking_cancellation(booking):
    student_user = booking.student.user
    exam = booking.examination
    course = exam.course

    subject = f"Booking Cancelled: {exam.title} ({course.code})"
    body = (
        f"Dear {booking.student.name},\n\n"
        f"Your booking #{booking.id} for {exam.title} has been cancelled.\n"
        f"If you wish to re-book, you may select another available slot during the open booking window.\n\n"
        f"Regards,\n"
        f"Examination Management System Office"
    )
    return send_notification(student_user, subject, body, 'Booking Cancellation')

def notify_booking_reschedule(booking, old_slot, new_slot):
    student_user = booking.student.user
    exam = booking.examination
    course = exam.course

    subject = f"Booking Rescheduled: {exam.title} ({course.code})"
    body = (
        f"Dear {booking.student.name},\n\n"
        f"An administrator has rescheduled your examination booking #{booking.id}.\n\n"
        f"Previous Slot: {old_slot.slot_date.strftime('%d-%b-%Y')} at {old_slot.start_time.strftime('%I:%M %p')}\n"
        f"NEW Slot Date: {new_slot.slot_date.strftime('%A, %d %B %Y')}\n"
        f"NEW Time: {new_slot.start_time.strftime('%I:%M %p')} - {new_slot.end_time.strftime('%I:%M %p')}\n"
        f"Examiner: {new_slot.examiner.name}\n"
        f"Venue / Link: {new_slot.location_or_link or 'TBA'}\n\n"
        f"Regards,\n"
        f"Examination Management System Office"
    )
    return send_notification(student_user, subject, body, 'Reschedule')

def notify_result_published(booking):
    student_user = booking.student.user
    exam = booking.examination
    course = exam.course

    subject = f"Examination Results Published: {exam.title} ({course.code})"
    body = (
        f"Dear {booking.student.name},\n\n"
        f"Your results for {exam.title} have been evaluated and published.\n\n"
        f"Score Awarded: {booking.marks_obtained} / {exam.total_marks} ({booking.percentage}%)\n"
        f"Evaluator Remarks: {booking.evaluation_remarks or 'No general remarks provided.'}\n\n"
        f"You can log in to your student dashboard to review detailed rubric scoring "
        f"and download your official examination scorecard.\n\n"
        f"Regards,\n"
        f"Examination Management System Office"
    )
    return send_notification(student_user, subject, body, 'Result Publication')

def notify_examiner_approval(examiner, approved=True):
    examiner_user = examiner.user
    status = "Approved" if approved else "Rejected"
    subject = f"Examiner Registration Status: {status}"
    body = (
        f"Dear {examiner.name},\n\n"
        f"Your examiner registration (Examiner ID: {examiner.examiner_id}) has been {status.lower()} by the administrator.\n\n"
    )
    if approved:
        body += "You can now log in, view assigned examinations, create examination slots, and evaluate students.\n"
    else:
        body += "Please reach out to the examination management office for further inquiries.\n"
    body += "\nRegards,\nExamination Management System Administration"
    
    return send_notification(examiner_user, subject, body, 'Registration Status')

