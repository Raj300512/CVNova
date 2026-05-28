"""
User model for AI Resume Analyzer authentication.
"""

from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import re

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User account model."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=True)   # nullable for Google users
    provider = db.Column(db.String(20), nullable=False, default='email')  # 'email' or 'google'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def set_password(self, password):
        """Hash and store the password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify a password against the stored hash."""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def validate_email(email):
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    @staticmethod
    def validate_password(password):
        """Validate password strength. Returns (is_valid, message)."""
        if len(password) < 8:
            return False, "Password must be at least 8 characters."
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter."
        if not re.search(r'[0-9]', password):
            return False, "Password must contain at least one number."
        return True, "OK"

    def __repr__(self):
        return f'<User {self.email}>'


class JobApplication(db.Model):
    """Job application tracking model for Kanban board."""
    __tablename__ = 'job_applications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    company = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='Applied') # Applied, Interviewing, Offered, Rejected
    applied_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    location = db.Column(db.String(100))
    salary = db.Column(db.String(50))
    job_url = db.Column(db.String(500))
    notes = db.Column(db.Text)
    last_reminded_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', backref=db.backref('applications', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'company': self.company,
            'role': self.role,
            'status': self.status,
            'applied_at': self.applied_at.isoformat() if self.applied_at else None,
            'location': self.location,
            'salary': self.salary,
            'job_url': self.job_url,
            'notes': self.notes
        }

    def __repr__(self):
        return f'<JobApplication {self.company} - {self.role}>'


class ResumeHistory(db.Model):
    """Tracks resume analysis history for analytics."""
    __tablename__ = 'resume_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(100), nullable=False)
    ats_score = db.Column(db.Integer, nullable=False)
    word_count = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', backref=db.backref('resume_history', lazy=True, order_by='ResumeHistory.created_at.desc()'))

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'role': self.role,
            'ats_score': self.ats_score,
            'word_count': self.word_count,
            'created_at': self.created_at.isoformat()
        }

    def __repr__(self):
        return f'<ResumeHistory {self.filename} - {self.ats_score}>'


class ResumeVersion(db.Model):
    """Stores multiple resume versions for comparison (Feature 3)."""
    __tablename__ = 'resume_versions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False, default='Version')
    resume_text = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(100), nullable=False)
    ats_score = db.Column(db.Integer, nullable=False, default=0)
    found_skills = db.Column(db.Text, nullable=True)   # JSON string
    missing_skills = db.Column(db.Text, nullable=True) # JSON string
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', backref=db.backref('resume_versions', lazy=True))

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'name': self.name,
            'role': self.role,
            'ats_score': self.ats_score,
            'found_skills': json.loads(self.found_skills) if self.found_skills else [],
            'missing_skills': json.loads(self.missing_skills) if self.missing_skills else [],
            'resume_text': self.resume_text,
            'created_at': self.created_at.isoformat()
        }

    def __repr__(self):
        return f'<ResumeVersion {self.name} - {self.ats_score}>'


class SkillProgress(db.Model):
    """Tracks which skills user has learned (Feature 7)."""
    __tablename__ = 'skill_progress'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    skill_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(100), nullable=False)
    learned = db.Column(db.Boolean, default=False)
    learned_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', backref=db.backref('skill_progress', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'skill_name': self.skill_name,
            'role': self.role,
            'learned': self.learned,
            'learned_at': self.learned_at.isoformat() if self.learned_at else None,
            'created_at': self.created_at.isoformat()
        }

    def __repr__(self):
        return f'<SkillProgress {self.skill_name} - {self.learned}>'


class InterviewAnswer(db.Model):
    """Saves user's best interview answers (Feature 8)."""
    __tablename__ = 'interview_answers'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='general')  # technical, behavioral, general
    role = db.Column(db.String(100), nullable=True)
    rating = db.Column(db.Integer, nullable=True)  # 1-5 stars
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', backref=db.backref('interview_answers', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'question': self.question,
            'answer': self.answer,
            'category': self.category,
            'role': self.role,
            'rating': self.rating,
            'created_at': self.created_at.isoformat()
        }

    def __repr__(self):
        return f'<InterviewAnswer {self.id}>'


class Notification(db.Model):
    """In-app notifications (Feature 10)."""
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(30), default='info')  # info, warning, success, reminder
    is_read = db.Column(db.Boolean, default=False)
    link = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', backref=db.backref('notifications', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'type': self.type,
            'is_read': self.is_read,
            'link': self.link,
            'created_at': self.created_at.isoformat()
        }

    def __repr__(self):
        return f'<Notification {self.title}>'


class Feedback(db.Model):
    """User feedback/reviews for landing page."""
    __tablename__ = 'feedback'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    review = db.Column(db.Text, nullable=False)
    job_title = db.Column(db.String(100), nullable=True)  # e.g. "Software Engineer @ Google"
    is_approved = db.Column(db.Boolean, default=True)  # show on landing page
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', backref=db.backref('feedbacks', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'user_name': self.user.name,
            'rating': self.rating,
            'review': self.review,
            'job_title': self.job_title or '',
            'created_at': self.created_at.isoformat()
        }

    def __repr__(self):
        return f'<Feedback {self.user.name} - {self.rating}★>'
