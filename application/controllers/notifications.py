from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from application.models import db, Notification

notif_bp = Blueprint('notifications', __name__)

@notif_bp.route('/')
@login_required
def index():
    if current_user.is_admin:
        # Admin can view all notifications/sent emails across system
        notifs = Notification.query.order_by(Notification.sent_at.desc()).limit(100).all()
    else:
        notifs = current_user.notifications.order_by(Notification.sent_at.desc()).all()
    
    return render_template('notifications/list.html', notifications=notifs)


@notif_bp.route('/<int:notif_id>/read', methods=['POST'])
@login_required
def mark_read(notif_id):
    notif = Notification.query.get_or_404(notif_id)
    if notif.user_id == current_user.id or current_user.is_admin:
        notif.is_read = True
        db.session.commit()
    return redirect(url_for('notifications.index'))


@notif_bp.route('/mark-all-read', methods=['POST'])
@login_required
def mark_all_read():
    for notif in current_user.notifications.filter_by(is_read=False).all():
        notif.is_read = True
    db.session.commit()
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('notifications.index'))

