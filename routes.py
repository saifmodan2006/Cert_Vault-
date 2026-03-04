import os
import uuid
from datetime import datetime
from functools import wraps
from flask import (
    render_template, redirect, url_for, flash, request,
    abort, send_from_directory, current_app, jsonify
)
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.utils import secure_filename
from extensions import db, bcrypt
from models import User, Certificate, ActivityLog


ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def log_activity(user_id, action):
    log = ActivityLog(user_id=user_id, action=action)
    db.session.add(log)
    db.session.commit()


def register_routes(app):

    # ─── Landing Page ──────────────────────────────────────
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('index.html')

    # ─── Auth Routes ───────────────────────────────────────
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            confirm = request.form.get('confirm_password', '')

            if not name or not email or not password:
                flash('All fields are required.', 'danger')
                return redirect(url_for('register'))
            if password != confirm:
                flash('Passwords do not match.', 'danger')
                return redirect(url_for('register'))
            if len(password) < 6:
                flash('Password must be at least 6 characters.', 'danger')
                return redirect(url_for('register'))
            if User.query.filter_by(email=email).first():
                flash('Email already registered.', 'danger')
                return redirect(url_for('register'))

            hashed = bcrypt.generate_password_hash(password).decode('utf-8')
            user = User(name=name, email=email, password=hashed)
            db.session.add(user)
            db.session.commit()
            log_activity(user.id, 'Registered account')
            flash('Account created! Please log in.', 'success')
            return redirect(url_for('login'))
        return render_template('register.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            user = User.query.filter_by(email=email).first()
            if user and bcrypt.check_password_hash(user.password, password):
                login_user(user, remember=request.form.get('remember'))
                log_activity(user.id, 'Logged in')
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard'))
            flash('Invalid email or password.', 'danger')
        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        log_activity(current_user.id, 'Logged out')
        logout_user()
        flash('You have been logged out.', 'info')
        return redirect(url_for('index'))

    # ─── Dashboard ─────────────────────────────────────────
    @app.route('/dashboard')
    @login_required
    def dashboard():
        search = request.args.get('q', '').strip()
        tag_filter = request.args.get('tag', '').strip()
        sort = request.args.get('sort', 'newest')

        query = Certificate.query.filter_by(user_id=current_user.id)

        if search:
            query = query.filter(
                (Certificate.title.ilike(f'%{search}%')) |
                (Certificate.issuer.ilike(f'%{search}%'))
            )
        if tag_filter:
            query = query.filter(Certificate.tags.ilike(f'%{tag_filter}%'))

        if sort == 'oldest':
            query = query.order_by(Certificate.issue_date.asc())
        elif sort == 'title':
            query = query.order_by(Certificate.title.asc())
        elif sort == 'expiry':
            query = query.order_by(Certificate.expiry_date.asc().nullslast())
        else:
            query = query.order_by(Certificate.uploaded_at.desc())

        certificates = query.all()

        # Collect all unique tags
        all_tags = set()
        for cert in Certificate.query.filter_by(user_id=current_user.id).all():
            if cert.tags:
                for t in cert.tags.split(','):
                    t = t.strip()
                    if t:
                        all_tags.add(t)

        stats = {
            'total': Certificate.query.filter_by(user_id=current_user.id).count(),
            'expiring_soon': 0,
            'expired': 0,
        }
        today = datetime.utcnow().date()
        for cert in Certificate.query.filter_by(user_id=current_user.id).all():
            if cert.expiry_date:
                if cert.expiry_date < today:
                    stats['expired'] += 1
                elif (cert.expiry_date - today).days <= 30:
                    stats['expiring_soon'] += 1

        return render_template('dashboard.html',
                               certificates=certificates,
                               stats=stats,
                               all_tags=sorted(all_tags),
                               search=search,
                               tag_filter=tag_filter,
                               sort=sort,
                               today=today)

    # ─── Upload Certificate ────────────────────────────────
    @app.route('/upload', methods=['GET', 'POST'])
    @login_required
    def upload():
        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            issuer = request.form.get('issuer', '').strip()
            description = request.form.get('description', '').strip()
            issue_date_str = request.form.get('issue_date', '')
            expiry_date_str = request.form.get('expiry_date', '')
            tags = request.form.get('tags', '').strip()
            file = request.files.get('file')

            if not title or not issuer or not issue_date_str or not file:
                flash('Title, issuer, issue date and file are required.', 'danger')
                return redirect(url_for('upload'))

            if not allowed_file(file.filename):
                flash('Invalid file type. Allowed: PDF, PNG, JPG, GIF, WEBP.', 'danger')
                return redirect(url_for('upload'))

            try:
                issue_date = datetime.strptime(issue_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid issue date format.', 'danger')
                return redirect(url_for('upload'))

            expiry_date = None
            if expiry_date_str:
                try:
                    expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
                except ValueError:
                    flash('Invalid expiry date format.', 'danger')
                    return redirect(url_for('upload'))

            # Save file
            original_filename = secure_filename(file.filename)
            unique_name = f"{uuid.uuid4().hex}_{original_filename}"
            user_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], str(current_user.id))
            os.makedirs(user_folder, exist_ok=True)
            filepath = os.path.join(user_folder, unique_name)
            file.save(filepath)

            cert = Certificate(
                title=title,
                issuer=issuer,
                description=description,
                issue_date=issue_date,
                expiry_date=expiry_date,
                tags=tags,
                file_path=f"{current_user.id}/{unique_name}",
                original_filename=original_filename,
                user_id=current_user.id
            )
            db.session.add(cert)
            db.session.commit()
            log_activity(current_user.id, f'Uploaded certificate: {title}')
            flash('Certificate uploaded successfully!', 'success')
            return redirect(url_for('dashboard'))
        return render_template('upload.html')

    # ─── View Certificate ──────────────────────────────────
    @app.route('/certificate/<int:cert_id>')
    @login_required
    def view_certificate(cert_id):
        cert = Certificate.query.get_or_404(cert_id)
        if cert.user_id != current_user.id:
            abort(403)
        return render_template('view_certificate.html', cert=cert)

    # ─── Edit Certificate ──────────────────────────────────
    @app.route('/certificate/<int:cert_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_certificate(cert_id):
        cert = Certificate.query.get_or_404(cert_id)
        if cert.user_id != current_user.id:
            abort(403)
        if request.method == 'POST':
            cert.title = request.form.get('title', cert.title).strip()
            cert.issuer = request.form.get('issuer', cert.issuer).strip()
            cert.description = request.form.get('description', '').strip()
            issue_str = request.form.get('issue_date', '')
            expiry_str = request.form.get('expiry_date', '')
            cert.tags = request.form.get('tags', '').strip()

            if issue_str:
                try:
                    cert.issue_date = datetime.strptime(issue_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
            if expiry_str:
                try:
                    cert.expiry_date = datetime.strptime(expiry_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
            else:
                cert.expiry_date = None

            # Handle optional file replacement
            file = request.files.get('file')
            if file and file.filename and allowed_file(file.filename):
                # Delete old file
                old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], cert.file_path)
                if os.path.exists(old_path):
                    os.remove(old_path)
                original_filename = secure_filename(file.filename)
                unique_name = f"{uuid.uuid4().hex}_{original_filename}"
                user_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], str(current_user.id))
                os.makedirs(user_folder, exist_ok=True)
                filepath = os.path.join(user_folder, unique_name)
                file.save(filepath)
                cert.file_path = f"{current_user.id}/{unique_name}"
                cert.original_filename = original_filename

            db.session.commit()
            log_activity(current_user.id, f'Edited certificate: {cert.title}')
            flash('Certificate updated!', 'success')
            return redirect(url_for('view_certificate', cert_id=cert.id))
        return render_template('edit_certificate.html', cert=cert)

    # ─── Delete Certificate ────────────────────────────────
    @app.route('/certificate/<int:cert_id>/delete', methods=['POST'])
    @login_required
    def delete_certificate(cert_id):
        cert = Certificate.query.get_or_404(cert_id)
        if cert.user_id != current_user.id:
            abort(403)
        # Delete file from disk
        file_full = os.path.join(current_app.config['UPLOAD_FOLDER'], cert.file_path)
        if os.path.exists(file_full):
            os.remove(file_full)
        title = cert.title
        db.session.delete(cert)
        db.session.commit()
        log_activity(current_user.id, f'Deleted certificate: {title}')
        flash('Certificate deleted.', 'info')
        return redirect(url_for('dashboard'))

    # ─── Download Certificate ──────────────────────────────
    @app.route('/certificate/<int:cert_id>/download')
    @login_required
    def download_certificate(cert_id):
        cert = Certificate.query.get_or_404(cert_id)
        if cert.user_id != current_user.id:
            abort(403)
        directory = os.path.join(current_app.config['UPLOAD_FOLDER'], str(current_user.id))
        filename = os.path.basename(cert.file_path)
        return send_from_directory(directory, filename, as_attachment=True,
                                   download_name=cert.original_filename)

    # ─── Serve Certificate File (for preview) ─────────────
    @app.route('/uploads/<path:filepath>')
    @login_required
    def serve_upload(filepath):
        # Only allow owners to view their files
        parts = filepath.split('/')
        if len(parts) >= 1 and parts[0] != str(current_user.id):
            abort(403)
        return send_from_directory(current_app.config['UPLOAD_FOLDER'], filepath)

    # ─── Toggle Sharing ───────────────────────────────────
    @app.route('/certificate/<int:cert_id>/toggle-share', methods=['POST'])
    @login_required
    def toggle_share(cert_id):
        cert = Certificate.query.get_or_404(cert_id)
        if cert.user_id != current_user.id:
            abort(403)
        cert.is_public = not cert.is_public
        db.session.commit()
        state = 'enabled' if cert.is_public else 'disabled'
        log_activity(current_user.id, f'Sharing {state} for: {cert.title}')
        flash(f'Sharing {state} for "{cert.title}".', 'success')
        return redirect(url_for('view_certificate', cert_id=cert.id))

    # ─── Public Shared View ───────────────────────────────
    @app.route('/shared/<shareable_id>')
    def shared_certificate(shareable_id):
        cert = Certificate.query.filter_by(shareable_id=shareable_id).first_or_404()
        if not cert.is_public:
            abort(404)
        return render_template('shared_certificate.html', cert=cert)

    # ─── Serve shared file ────────────────────────────────
    @app.route('/shared-file/<shareable_id>')
    def serve_shared_file(shareable_id):
        cert = Certificate.query.filter_by(shareable_id=shareable_id).first_or_404()
        if not cert.is_public:
            abort(404)
        directory = os.path.dirname(os.path.join(current_app.config['UPLOAD_FOLDER'], cert.file_path))
        filename = os.path.basename(cert.file_path)
        return send_from_directory(directory, filename)

    # ─── Activity Log ─────────────────────────────────────
    @app.route('/activity')
    @login_required
    def activity():
        logs = ActivityLog.query.filter_by(user_id=current_user.id)\
            .order_by(ActivityLog.timestamp.desc()).limit(50).all()
        return render_template('activity.html', logs=logs)

    # ─── Profile ──────────────────────────────────────────
    @app.route('/profile', methods=['GET', 'POST'])
    @login_required
    def profile():
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')

            if name:
                current_user.name = name

            if current_password and new_password:
                if bcrypt.check_password_hash(current_user.password, current_password):
                    if len(new_password) >= 6:
                        current_user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
                        flash('Password updated.', 'success')
                    else:
                        flash('New password must be at least 6 characters.', 'danger')
                else:
                    flash('Current password is incorrect.', 'danger')

            db.session.commit()
            log_activity(current_user.id, 'Updated profile')
            flash('Profile updated.', 'success')
            return redirect(url_for('profile'))
        return render_template('profile.html')

    # ─── Error Handlers ───────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(500)
    def server_error(e):
        return render_template('errors/500.html'), 500
