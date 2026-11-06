from functools import wraps
from flask import flash, redirect, url_for, abort, request, jsonify
from flask_login import current_user

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required'}), 401
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        if not current_user.is_admin:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Admin privilege required'}), 403
            flash('Unauthorized access: Administrator role required.', 'danger')
            return redirect(url_for('auth.index'))
        return f(*args, **kwargs)
    return decorated_function

def examiner_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required'}), 401
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        if not current_user.is_examiner:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Examiner privilege required'}), 403
            flash('Unauthorized access: Examiner role required.', 'danger')
            return redirect(url_for('auth.index'))
        if not current_user.examiner_profile or current_user.examiner_profile.status != 'Approved':
            status = current_user.examiner_profile.status if current_user.examiner_profile else 'Unknown'
            if request.path.startswith('/api/'):
                return jsonify({'error': f'Examiner account is {status}. Admin approval required.'}), 403
            flash(f'Your examiner account status is "{status}". You will be able to access the dashboard once an administrator approves your registration.', 'info')
            return redirect(url_for('auth.pending_approval'))
        return f(*args, **kwargs)
    return decorated_function

def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required'}), 401
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        if not current_user.is_student:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Student privilege required'}), 403
            flash('Unauthorized access: Student role required.', 'danger')
            return redirect(url_for('auth.index'))
        return f(*args, **kwargs)
    return decorated_function

