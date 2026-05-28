"""
Authentication Blueprint — Login, Register, Logout, Google OAuth
"""

import os
from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from authlib.integrations.flask_client import OAuth
from models import db, User

auth = Blueprint('auth', __name__)

# ─── Google OAuth Setup ───────────────────────────────────────────────────────

oauth = OAuth()


def init_oauth(app):
    """Initialize OAuth with the Flask app."""
    oauth.init_app(app)
    
    google_client_id = os.getenv('GOOGLE_CLIENT_ID', '')
    google_client_secret = os.getenv('GOOGLE_CLIENT_SECRET', '')
    
    if google_client_id and google_client_id != 'your-google-client-id':
        oauth.register(
            name='google',
            client_id=google_client_id,
            client_secret=google_client_secret,
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={
                'scope': 'openid email profile'
            }
        )


# ─── Login ────────────────────────────────────────────────────────────────────

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Please fill in all fields.', 'error')
            return render_template('login.html')

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash('Invalid email or password.', 'error')
            return render_template('login.html')

        if user.provider == 'google':
            flash('This account uses Google login. Please use the "Login with Google" button.', 'error')
            return render_template('login.html')

        login_user(user, remember=True)
        next_page = request.args.get('next')
        return redirect(next_page or url_for('index'))

    return render_template('login.html')


# ─── Register ─────────────────────────────────────────────────────────────────

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validation
        if not name or not email or not password or not confirm_password:
            flash('Please fill in all fields.', 'error')
            return render_template('register.html')

        if not User.validate_email(email):
            flash('Please enter a valid email address.', 'error')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')

        is_valid, msg = User.validate_password(password)
        if not is_valid:
            flash(msg, 'error')
            return render_template('register.html')

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('An account with this email already exists.', 'error')
            return render_template('register.html')

        # Create user
        user = User(name=name, email=email, provider='email')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user, remember=True)
        flash('Account created successfully! Welcome to CVNova.', 'success')
        return redirect(url_for('index'))

    return render_template('register.html')


# ─── Logout ───────────────────────────────────────────────────────────────────

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))


# ─── Google OAuth ─────────────────────────────────────────────────────────────

@auth.route('/login/google')
def google_login():
    google = oauth.create_client('google')
    if not google:
        flash('Google login is not configured. Please use email login.', 'error')
        return redirect(url_for('auth.login'))
    
    # Force the exact redirect URI to avoid mismatch errors during local testing
    # If running locally, Google usually requires exactly http://localhost:8080/...
    # or http://127.0.0.1:8080/... depending on how it was registered in Cloud Console.
    redirect_uri = url_for('auth.google_callback', _external=True)
    if '127.0.0.1' in redirect_uri:
        redirect_uri = redirect_uri.replace('127.0.0.1', 'localhost')
        
    return google.authorize_redirect(redirect_uri)


@auth.route('/auth/google/callback')
def google_callback():
    google = oauth.create_client('google')
    if not google:
        flash('Google login is not configured.', 'error')
        return redirect(url_for('auth.login'))

    try:
        token = google.authorize_access_token()
        user_info = google.parse_id_token(token, nonce=session.get('nonce'))
        if not user_info:
            user_info = google.userinfo()
    except Exception as e:
        flash('Google login failed. Please try again.', 'error')
        return redirect(url_for('auth.login'))

    email = user_info.get('email', '').lower()
    name = user_info.get('name', email.split('@')[0])

    if not email:
        flash('Could not retrieve email from Google.', 'error')
        return redirect(url_for('auth.login'))

    # Find or create user
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(name=name, email=email, provider='google')
        db.session.add(user)
        db.session.commit()

    login_user(user, remember=True)
    return redirect(url_for('index'))
