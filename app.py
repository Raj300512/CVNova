"""
CVNova — Optimization Backend
"""

import os
import io
import json
import hashlib
import tempfile
import secrets
from datetime import datetime, timezone
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for, g
from flask_login import LoginManager, login_required, current_user
from werkzeug.utils import secure_filename
from functools import wraps
from collections import defaultdict
import time

import pdfplumber
from docx import Document
import google.generativeai as genai
import urllib.parse
import re

from models import db, User, JobApplication, ResumeHistory, ResumeVersion, SkillProgress, InterviewAnswer, Notification, Feedback
from analyzer import analyze_resume, get_available_roles
from pdf_generator import generate_resume_pdf
from auth import auth, init_oauth
from flask_mail import Mail
from scheduler import init_scheduler

# ─── Load Environment Variables ───────────────────────────────────────────────
load_dotenv()

# ─── App Setup ────────────────────────────────────────────────────────────────
app = Flask(__name__)

# SECRET_KEY: production mein env var se aana chahiye, fallback sirf dev ke liye
_secret_key = os.getenv('SECRET_KEY')
if not _secret_key:
    if os.getenv('FLASK_ENV') == 'production':
        raise RuntimeError("SECRET_KEY environment variable must be set in production!")
    _secret_key = secrets.token_hex(32)  # random key for local dev
app.config['SECRET_KEY'] = _secret_key

app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///users.db').replace('postgres://', 'postgresql://')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True, "pool_recycle": 300}

# ─── Session Cookie Security ──────────────────────────────────────────────────
app.config['SESSION_COOKIE_HTTPONLY'] = True   # JS se cookie access nahi hogi
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
# HTTPS pe deploy hone ke baad True karo:
app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') == 'production'

# ─── Simple In-Memory Rate Limiter ───────────────────────────────────────────
_rate_limit_store = defaultdict(list)  # ip -> [timestamps]

def rate_limit(max_requests=30, window_seconds=60):
    """Decorator: max_requests per window_seconds per IP."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            ip = request.headers.get('X-Forwarded-For', request.remote_addr or 'unknown').split(',')[0].strip()
            now = time.time()
            key = f"{f.__name__}:{ip}"
            # Remove old timestamps outside the window
            _rate_limit_store[key] = [t for t in _rate_limit_store[key] if now - t < window_seconds]
            if len(_rate_limit_store[key]) >= max_requests:
                return jsonify({"error": "Too many requests. Please slow down."}), 429
            _rate_limit_store[key].append(now)
            return f(*args, **kwargs)
        return wrapped
    return decorator

# ─── Mail Configuration ───────────────────────────────────────────────────────
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'localhost')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 2525))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'False').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@cvnova.ai')
app.config['MAIL_SUPPRESS_SEND'] = not bool(app.config['MAIL_USERNAME']) # Suppress if no creds

mail = Mail(app)

import requests

# Initialize AI Clients
azure_api_key = os.getenv('AZURE_OPENAI_API_KEY')
azure_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
azure_configured = bool(azure_api_key and azure_endpoint)
azure_bing_key = os.getenv('AZURE_BING_SEARCH_API_KEY')
jsearch_api_key = os.getenv('JSEARCH_API_KEY')

github_token = os.getenv('GITHUB_TOKEN')
github_configured = bool(github_token)

gemini_configured = False
gemini_api_key = os.getenv('GEMINI_API_KEY')
print(f"DEBUG: GEMINI_API_KEY present: {bool(gemini_api_key)}, Azure configured: {azure_configured}")
if gemini_api_key:
    try:
        genai.configure(api_key=gemini_api_key)
        gemini_configured = True
        print("DEBUG: Gemini SDK configured successfully.")
    except Exception as e:
        print(f"DEBUG: Gemini SDK configuration FAILED: {e}")
        pass
ALLOWED_EXTENSIONS = {'pdf', 'docx'}

# ─── SHA256 Result Cache ──────────────────────────────────────────────────────
_result_cache = {}

# ─── Initialize Extensions ───────────────────────────────────────────────────
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'error'

# Register auth blueprint
app.register_blueprint(auth)

# Initialize Google OAuth
google_oauth_configured = bool(os.getenv('GOOGLE_CLIENT_ID', '')) and os.getenv('GOOGLE_CLIENT_ID', '') != 'your-google-client-id'
init_oauth(app)

@app.context_processor
def inject_google_oauth():
    return dict(google_oauth_configured=google_oauth_configured)

# Create database tables
with app.app_context():
    db.create_all()

# Initialize Background Scheduler
init_scheduler(app, mail)

# ─── Security Headers (har response ke saath) ────────────────────────────────
@app.after_request
def add_security_headers(response):
    # Clickjacking se bachao
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    # MIME sniffing band karo
    response.headers['X-Content-Type-Options'] = 'nosniff'
    # XSS filter (older browsers ke liye)
    response.headers['X-XSS-Protection'] = '1; mode=block'
    # Referrer info limit karo
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    # Content Security Policy — inline scripts allowed (builder.js ke liye), external CDNs allowed
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https:;"
    )
    # HTTPS enforce karo (sirf production pe)
    if os.getenv('FLASK_ENV') == 'production':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ─── Helpers ──────────────────────────────────────────────────────────────────

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text_from_pdf(filepath):
    """Extract text from PDF using pdfplumber."""
    text = ""
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    full_text = text.strip()
    # Clean PDF artifacts like (cid:127)
    import re
    full_text = re.sub(r'\(cid:\d+\)', '', full_text)
    return full_text.strip()


def extract_text_from_docx(filepath):
    """Extract text from DOCX using python-docx."""
    doc = Document(filepath)
    text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
    return text.strip()


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def home():
    """Landing page for guests, analyzer for logged-in users."""
    if current_user.is_authenticated:
        roles = get_available_roles()
        return render_template('index.html', roles=roles)
    return render_template('landing.html')

@app.route('/landing')
def landing():
    """Landing page - always show regardless of login status."""
    return render_template('landing.html')

@app.route('/analyzer')
@login_required
def index():
    roles = get_available_roles()
    return render_template('index.html', roles=roles)


@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')


@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"}), 200


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(e):
    return render_template('404.html'), 500


@app.route('/api/roles', methods=['GET'])
@login_required
def api_roles():
    return jsonify(get_available_roles())


@app.route('/api/upload', methods=['POST'])
@login_required
@rate_limit(max_requests=10, window_seconds=60)  # 10 uploads per minute per IP
def upload_resume():
    # Validate file
    if 'resume' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['resume']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Only PDF and DOCX are supported."}), 400

    # Get parameters
    job_role = request.form.get('job_role', 'software_engineer')
    job_description = request.form.get('job_description', '')
    custom_role = request.form.get('custom_role', '')

    # Save and extract text
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        ext = filename.rsplit('.', 1)[1].lower()
        if ext == 'pdf':
            text = extract_text_from_pdf(filepath)
        elif ext == 'docx':
            text = extract_text_from_docx(filepath)
        else:
            return jsonify({"error": "Unsupported file format"}), 400

        if not text or len(text.strip()) < 50:
            return jsonify({"error": "Could not extract enough text from the file. Ensure it's not a scanned/image-based PDF."}), 400

        # SHA256 cache: same resume + same role = identical results
        cache_key = hashlib.sha256((text + job_role + custom_role).encode('utf-8')).hexdigest()
        if cache_key in _result_cache:
            cached = _result_cache[cache_key].copy()
            cached['filename'] = filename
            cached['resume_text'] = text  # Always include resume_text
            cached['cached'] = True
            return jsonify(cached)

        # Run analysis
        results = analyze_resume(text, job_role, job_description, custom_role)
        results['filename'] = filename
        results['resume_text'] = text  # Store for Save Version feature

        # Store in cache
        _result_cache[cache_key] = results.copy()

        # Store in DB for analytics
        if current_user.is_authenticated:
            new_history = ResumeHistory(
                user_id=current_user.id,
                filename=filename,
                role=results['role'],
                ats_score=results.get('ats_score', {}).get('total', 0),
                word_count=results.get('word_count', 0)
            )
            db.session.add(new_history)
            db.session.commit()

        return jsonify(results)

    except Exception as e:
        return jsonify({"error": f"Error processing file: {str(e)}"}), 500

    finally:
        # Clean up uploaded file
        if os.path.exists(filepath):
            os.remove(filepath)


@app.route('/api/analytics', methods=['GET'])
@login_required
def get_analytics():
    """Endpoint to fetch resume analysis history."""
    try:
        history = ResumeHistory.query.filter_by(user_id=current_user.id).order_by(ResumeHistory.created_at.asc()).all()
        return jsonify([h.to_dict() for h in history])
    except Exception as e:
        return jsonify({"error": f"Failed to fetch analytics: {str(e)}"}), 500


@app.route('/api/test-reminders', methods=['POST'])
@login_required
def test_reminders():
    """Manually trigger the reminder scheduler for testing."""
    from scheduler import check_and_send_reminders
    try:
        check_and_send_reminders(app, mail)
        return jsonify({"message": "Reminders job triggered successfully. Check logs."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/download-pdf', methods=['POST'])
@login_required
def download_pdf():
    """Endpoint to generate and download analysis PDF."""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        pdf_bytes = generate_resume_pdf(data)
        
        raw_name = data.get('filename', 'Resume_Analysis_Report.pdf')
        # Strip any existing .pdf extension, then add _report.pdf cleanly
        base = raw_name[:-4] if raw_name.lower().endswith('.pdf') else raw_name
        # Remove trailing _report if already present to avoid double-append
        if base.lower().endswith('_report'):
            base = base[:-7]
        filename = f"{base}_report.pdf"

        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({"error": f"Failed to generate PDF: {str(e)}"}), 500


@app.route('/api/chat', methods=['POST'])
@login_required
@rate_limit(max_requests=20, window_seconds=60)  # 20 chat messages per minute per IP
def chat():
    data = request.json
    if not data or 'message' not in data:
        return jsonify({"error": "No message provided"}), 400
    
    user_msg = data['message']
    print(f"DEBUG: Incoming /api/chat message: {user_msg}")
    context = data.get('context', {})
    
    # Extract context data for smarter responses
    role = context.get('role', 'your target role')
    ats = context.get('ats_score', {})
    total_score = ats.get('total', 'N/A')
    missing_skills = context.get('missing_skills', [])
    found_skills = context.get('found_skills', [])
    weaknesses = context.get('weaknesses', [])
    strengths = context.get('strengths', [])
    roadmap = context.get('roadmap', {}).get('steps', [])
    interviews = context.get('interview_questions', {}).get('technical', [])
    jd_match = context.get('jd_match', {})
    
    # Check if AI is configured
    if github_configured or azure_configured or gemini_configured:
        try:
            print(f"DEBUG: AI calling with prompt: {user_msg}")
            # Build a powerful system prompt for Bunny
            system_prompt = f"""You are Bunny 🐰, an intelligent, friendly, and highly capable AI Resume Companion.
            
            YOUR PERSONALITY:
            - Friendly, supportive, and conversational.
            - Feel like a real AI mentor, not a rigid bot.
            - Use emojis thoughtfully but not excessively.
            - Keep responses concise (2-3 paragraphs max) unless generating specific resume content.
            
            YOUR CAPABILITIES:
            - Understand conversation context and memory.
            - Handle short intents naturally. If the user says "yes", "sure", or "please", execute the action you previously suggested.
            - If the user says "no" or "not now", acknowledge gracefully (e.g., "No problem! Let me know if you want to look at something else.")
            - Proactively offer specific help based on their resume data.
            - Do NOT repeat the exact same response or phrasing if the user asks a similar question.
            
            CANDIDATE'S RESUME CONTEXT:
            - Target Role: {role}
            - ATS Score: {total_score}/100
            - Key Strengths: {', '.join([s.get('title', '') for s in strengths[:3]])}
            - Weaknesses to Fix: {', '.join([w.get('title', '') for w in weaknesses[:3]])}
            - Missing Skills: {', '.join(missing_skills[:10]) if missing_skills else 'None detected!'}
            - Known Skills: {', '.join(found_skills[:15])}
            
            INSTRUCTIONS FOR RESPONDING:
            1. Integrate the candidate's actual resume data into your advice to make it deeply personalized.
            2. If they ask to improve their resume, generate specific strong bullet points or suggest exactly where to add missing skills.
            3. Always offer a clear next step or suggestion at the end of your response to keep the conversation dynamic.
            """

            # If GitHub is configured, prefer it for Bunny chat
            if github_configured:
                print("DEBUG: Routing chat to GitHub Models.")
                messages = [{"role": "system", "content": system_prompt}]
                
                # Format history
                history = data.get('history', [])
                for msg in history[-10:]:
                    if msg.get('content'):
                        in_role = msg.get('role')
                        msg_role = 'assistant' if in_role == 'assistant' else 'user'
                        messages.append({"role": msg_role, "content": msg['content']})
                
                if not messages or messages[-1].get('content') != user_msg or messages[-1].get('role') != 'user':
                    messages.append({"role": "user", "content": user_msg})
                    
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {github_token}"
                }
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": messages,
                    "temperature": 0.4,
                    "max_tokens": 500,
                    "top_p": 0.9
                }
                
                resp = requests.post("https://models.inference.ai.azure.com/chat/completions", headers=headers, json=payload, timeout=20)
                resp.raise_for_status()
                ai_response = resp.json()['choices'][0]['message']['content']
                print(f"DEBUG: GitHub Models successfully responded: {ai_response[:100]}...")
                return jsonify({"response": ai_response})

            # Else if Azure is configured
            elif azure_configured:
                print("DEBUG: Routing chat to Azure OpenAI.")
                messages = [{"role": "system", "content": system_prompt}]
                
                # Format history for Azure
                history = data.get('history', [])
                for msg in history[-10:]:
                    if msg.get('content'):
                        in_role = msg.get('role')
                        msg_role = 'assistant' if in_role == 'assistant' else 'user'
                        messages.append({"role": msg_role, "content": msg['content']})
                
                # Make sure the current user message is always the last one if not already in history
                if not messages or messages[-1].get('content') != user_msg or messages[-1].get('role') != 'user':
                    messages.append({"role": "user", "content": user_msg})
                    
                headers = {
                    "Content-Type": "application/json",
                    "api-key": azure_api_key
                }
                payload = {
                    "messages": messages,
                    "temperature": 0.4,
                    "max_tokens": 500,
                    "top_p": 0.9
                }
                
                resp = requests.post(azure_endpoint, headers=headers, json=payload, timeout=20)
                resp.raise_for_status()
                ai_response = resp.json()['choices'][0]['message']['content']
                print(f"DEBUG: Azure successfully responded: {ai_response[:100]}...")
                return jsonify({"response": ai_response})
            else:
                model = genai.GenerativeModel(
                    model_name="gemini-1.5-flash",
                    system_instruction=system_prompt,
                    generation_config=genai.GenerationConfig(
                        temperature=0.4,
                        top_p=0.9,
                        max_output_tokens=500,
                    )
                )

                # history from frontend already includes the current user message as the last item
                history = data.get('history', [])
                print(f"DEBUG: History length: {len(history)}")
                
                gemini_history = []
                for msg in history[-10:]:
                    if msg.get('content'):
                        role_map = {'user': 'user', 'assistant': 'model'}
                        g_role = role_map.get(msg.get('role'))
                        if g_role:
                            gemini_history.append({"role": g_role, "parts": [msg['content']]})

                latest_user_message = user_msg
                if gemini_history and gemini_history[-1]['role'] == 'user':
                    latest_user_message = gemini_history[-1]['parts'][0]
                    gemini_history = gemini_history[:-1]

                print(f"DEBUG: gemini_history size: {len(gemini_history)}")
                print(f"DEBUG: latest_user_message: {latest_user_message}")

                chat_session = model.start_chat(history=gemini_history)
                print("DEBUG: Sending message to Gemini...")
                response = chat_session.send_message(latest_user_message)
                
                ai_response = response.text
                print(f"DEBUG: Gemini successfully responded: {ai_response[:100]}...")
                return jsonify({"response": ai_response})
            
        except Exception as e:
            error_str = str(e)
            print(f"DEBUG ERROR in /api/chat: {error_str}")
            if "quota" in error_str.lower() or "401" in error_str:
                return jsonify({
                    "response": f"I'd love to chat more, but there's a problem with my API Key or quota! 🐰\n\nI can still see your ATS score is **{total_score}**."
                })
            elif "429" in error_str or "too many requests" in error_str.lower():
                return jsonify({
                    "response": f"Whoops, we're talking a bit too fast and hit a rate limit! (Too Many Requests). 🐰\n\nPlease wait a few seconds and try asking again!"
                })
            return jsonify({"error": f"AI service temporarily unavailable. ({error_str})"}), 503
            
    # Fallback if AI is not configured
    return jsonify({
        "response": f"I'm currently running in offline mode because my API key isn't configured. 🐰\n\nI can still tell you that your ATS score is **{total_score}** and you are targeting a **{role}** role. Connect my API to unlock full conversation capabilities!"
    })


@app.route('/jobs')
@login_required
def jobs():
    return render_template('jobs.html')


@app.route('/api/jobs', methods=['GET'])
@login_required
def api_jobs():
    query = request.args.get('q', '')
    job_type = request.args.get('type', '')
    location = request.args.get('location', '')
    skills = request.args.get('skills', '')
    date_posted = request.args.get('date_posted', 'all')
    remote_only = request.args.get('remote_only', 'false') == 'true'
    page = request.args.get('page', '1')

    if not query:
        return jsonify({"error": "Query parameter 'q' is required"}), 400

    # ─── JSearch API (Primary) ────────────────────────────────────────────
    if jsearch_api_key:
        print(f"DEBUG: Using JSearch API for query: {query}")

        # Map UI job type to JSearch employment_types
        employment_type_map = {
            'Internship': 'INTERN',
            'Full-time': 'FULLTIME',
            'Part-time': 'PARTTIME',
            'Contract': 'CONTRACTOR',
        }

        # Build the search query with location baked in
        search_query = query
        if location:
            search_query += f" in {location}"

        headers = {
            "x-rapidapi-host": "jsearch.p.rapidapi.com",
            "x-rapidapi-key": jsearch_api_key
        }
        params = {
            "query": search_query,
            "page": page,
            "num_pages": "1",
            "date_posted": date_posted,
        }

        # Add employment type filter if selected
        if job_type and job_type in employment_type_map:
            params["employment_types"] = employment_type_map[job_type]

        if remote_only:
            params["remote_jobs_only"] = "true"

        try:
            resp = requests.get(
                "https://jsearch.p.rapidapi.com/search",
                headers=headers, params=params, timeout=15
            )
            resp.raise_for_status()
            result = resp.json()

            jobs = []
            for item in result.get('data', []):
                # Parse salary info
                salary = ""
                min_sal = item.get('job_min_salary')
                max_sal = item.get('job_max_salary')
                sal_currency = item.get('job_salary_currency', 'USD')
                sal_period = item.get('job_salary_period', '')
                if min_sal and max_sal:
                    salary = f"{sal_currency} {int(min_sal):,} – {int(max_sal):,}"
                    if sal_period:
                        salary += f" / {sal_period.lower()}"
                elif min_sal:
                    salary = f"{sal_currency} {int(min_sal):,}+"
                    if sal_period:
                        salary += f" / {sal_period.lower()}"

                # Parse location
                city = item.get('job_city', '')
                state = item.get('job_state', '')
                country = item.get('job_country', '')
                job_location = ', '.join(filter(None, [city, state, country]))
                if item.get('job_is_remote'):
                    job_location = f"🌐 Remote" + (f" ({job_location})" if job_location else "")
                elif not job_location:
                    job_location = 'Not specified'

                # Parse employment type for display
                emp_type = item.get('job_employment_type', '')
                emp_display = {
                    'FULLTIME': 'Full-time', 'PARTTIME': 'Part-time',
                    'CONTRACTOR': 'Contract', 'INTERN': 'Internship',
                    'TEMPORARY': 'Temporary'
                }.get(emp_type, emp_type.capitalize() if emp_type else '')

                # Extract highlights
                highlights = item.get('job_highlights', {})
                qualifications = []
                responsibilities = []
                benefits = []
                if isinstance(highlights, dict):
                    for h in highlights.get('Qualifications', []):
                        qualifications.append(h)
                    for h in highlights.get('Responsibilities', []):
                        responsibilities.append(h)
                    for h in highlights.get('Benefits', []):
                        benefits.append(h)

                # Calculate days ago
                posted_at = item.get('job_posted_at_datetime_utc', '')
                days_ago = ''
                if posted_at:
                    try:
                        from datetime import datetime, timezone
                        posted_dt = datetime.fromisoformat(posted_at.replace('Z', '+00:00'))
                        diff = datetime.now(timezone.utc) - posted_dt
                        d = diff.days
                        if d == 0:
                            days_ago = 'Today'
                        elif d == 1:
                            days_ago = '1 day ago'
                        else:
                            days_ago = f'{d} days ago'
                    except Exception:
                        days_ago = ''

                # Build description snippet
                snippet = item.get('job_description', '')[:250]
                if len(item.get('job_description', '')) > 250:
                    snippet += '...'

                jobs.append({
                    "title": item.get('job_title', 'Untitled'),
                    "company": item.get('employer_name', ''),
                    "company_logo": item.get('employer_logo', ''),
                    "location": job_location,
                    "snippet": snippet,
                    "url": item.get('job_apply_link') or item.get('job_google_link', '#'),
                    "source": item.get('job_publisher', 'JSearch'),
                    "employment_type": emp_display,
                    "salary": salary,
                    "posted": days_ago,
                    "is_remote": item.get('job_is_remote', False),
                    "qualifications": qualifications[:5],
                    "responsibilities": responsibilities[:5],
                    "benefits": benefits[:5],
                    "ai_recommended": bool(skills)
                })

            print(f"DEBUG: JSearch returned {len(jobs)} jobs")
            return jsonify({"jobs": jobs})

        except Exception as e:
            print(f"DEBUG Error calling JSearch API: {str(e)}")
            return jsonify({"error": f"Failed to fetch jobs from JSearch: {str(e)}"}), 500

    # ─── Fallback: Mock Data ──────────────────────────────────────────────
    print("DEBUG: No job search API key found. Using mock data.")
    mock_jobs = [
        {
            "title": f"[Mock] {query}",
            "company": "Example Corp",
            "company_logo": "",
            "location": location or "Remote",
            "snippet": "Configure your JSEARCH_API_KEY in .env to see real job results from LinkedIn, Indeed, Glassdoor and more.",
            "url": "https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch",
            "source": "System",
            "employment_type": job_type or "Full-time",
            "salary": "",
            "posted": "Today",
            "is_remote": False,
            "qualifications": [],
            "responsibilities": [],
            "benefits": [],
            "ai_recommended": False
        }
    ]
    return jsonify({"jobs": mock_jobs})


@app.route('/tracker')
@login_required
def tracker():
    return render_template('tracker.html')


@app.route('/api/applications', methods=['GET'])
@login_required
def get_applications():
    apps = JobApplication.query.filter_by(user_id=current_user.id).order_by(JobApplication.applied_at.desc()).all()
    return jsonify([a.to_dict() for a in apps])


@app.route('/api/applications', methods=['POST'])
@login_required
def add_application():
    data = request.json
    if not data or 'company' not in data or 'role' not in data:
        return jsonify({"error": "Company and Role are required"}), 400
    
    new_app = JobApplication(
        user_id=current_user.id,
        company=data['company'],
        role=data['role'],
        status=data.get('status', 'Applied'),
        location=data.get('location'),
        salary=data.get('salary'),
        job_url=data.get('job_url'),
        notes=data.get('notes')
    )
    db.session.add(new_app)
    db.session.commit()
    return jsonify(new_app.to_dict()), 201


@app.route('/api/applications/<int:app_id>', methods=['PUT'])
@login_required
def update_application(app_id):
    app_record = JobApplication.query.get_or_404(app_id)
    if app_record.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    
    data = request.json
    if 'status' in data:
        app_record.status = data['status']
    if 'notes' in data:
        app_record.notes = data['notes']
    if 'company' in data:
        app_record.company = data['company']
    if 'role' in data:
        app_record.role = data['role']
        
    db.session.commit()
    return jsonify(app_record.to_dict())


@app.route('/api/applications/<int:app_id>', methods=['DELETE'])
@login_required
def delete_application(app_id):
    app_record = JobApplication.query.get_or_404(app_id)
    if app_record.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    
    db.session.delete(app_record)
    db.session.commit()
    return jsonify({"success": True})


# ─── Cover Letter Generator ───────────────────────────────────────────────

@app.route('/coverletter')
@login_required
def coverletter():
    return render_template('coverletter.html')


@app.route('/api/generate-cover-letter', methods=['POST'])
@login_required
@rate_limit(max_requests=10, window_seconds=60)  # 10 cover letters per minute
def generate_cover_letter():
    """Generate a tailored cover letter using AI."""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    job_description = data.get('job_description', '')
    resume_text = data.get('resume_text', '')
    company_name = data.get('company_name', 'the company')
    role_title = data.get('role_title', 'the position')

    if not job_description:
        return jsonify({"error": "Job description is required"}), 400
    if not resume_text:
        return jsonify({"error": "Resume text is required"}), 400

    system_prompt = f"""You are a professional cover letter writer. Your task is to write a compelling, tailored cover letter.

INSTRUCTIONS:
- Write a 3-4 paragraph professional cover letter
- The letter should be addressed to the Hiring Manager at {company_name} for the role of {role_title}
- Reference specific skills and experiences from the candidate's resume that match the job requirements
- Use a confident, professional but warm tone
- Include measurable achievements from the resume when possible
- Align the candidate's background specifically to the job description requirements
- Keep it concise (250-400 words)
- Do NOT include placeholder brackets like [Your Name] — use natural, clean formatting
- Start with a proper greeting and end with a professional closing
- Format: Greeting, Opening paragraph (hook + role), Body paragraphs (skills alignment), Closing paragraph (call to action)

CANDIDATE'S RESUME:
{resume_text[:3000]}

JOB DESCRIPTION:
{job_description[:3000]}

Write the cover letter now. Output ONLY the cover letter text, no extra commentary."""

    user_message = f"Write a professional cover letter for the {role_title} position at {company_name}."

    if not (github_configured or azure_configured or gemini_configured):
        return jsonify({"error": "No AI service is configured. Please add an API key in your .env file."}), 503

    try:
        if github_configured:
            print("DEBUG: Cover letter via GitHub Models.")
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {github_token}"
            }
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                "temperature": 0.5,
                "max_tokens": 800,
                "top_p": 0.9
            }
            resp = requests.post("https://models.inference.ai.azure.com/chat/completions", headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            cover_letter = resp.json()['choices'][0]['message']['content']

        elif azure_configured:
            print("DEBUG: Cover letter via Azure OpenAI.")
            headers = {
                "Content-Type": "application/json",
                "api-key": azure_api_key
            }
            payload = {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                "temperature": 0.5,
                "max_tokens": 800,
                "top_p": 0.9
            }
            resp = requests.post(azure_endpoint, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            cover_letter = resp.json()['choices'][0]['message']['content']

        else:
            print("DEBUG: Cover letter via Gemini.")
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=system_prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.5,
                    top_p=0.9,
                    max_output_tokens=800,
                )
            )
            response = model.generate_content(user_message)
            cover_letter = response.text

        print(f"DEBUG: Cover letter generated successfully ({len(cover_letter)} chars)")
        return jsonify({"cover_letter": cover_letter.strip()})

    except Exception as e:
        error_str = str(e)
        print(f"DEBUG ERROR in /api/generate-cover-letter: {error_str}")
        if "quota" in error_str.lower() or "401" in error_str:
            return jsonify({"error": "API key issue or quota exceeded. Please check your configuration."}), 503
        if "429" in error_str or "too many requests" in error_str.lower():
            return jsonify({"error": "Rate limit hit. Please wait a moment and try again."}), 429
        return jsonify({"error": f"AI service error: {error_str}"}), 503


@app.route('/api/download-cover-letter-pdf', methods=['POST'])
@login_required
def download_cover_letter_pdf():
    """Generate and download cover letter as PDF."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_LEFT
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.units import inch

        data = request.json
        if not data or 'cover_letter' not in data:
            return jsonify({"error": "No cover letter content provided"}), 400

        cover_letter_text = data['cover_letter']
        company_name = data.get('company_name', 'Company')
        role_title = data.get('role_title', 'Position')

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            rightMargin=72, leftMargin=72,
            topMargin=60, bottomMargin=60
        )

        styles = getSampleStyleSheet()
        body_style = ParagraphStyle(
            'CoverLetterBody',
            parent=styles['Normal'],
            fontSize=11,
            leading=18,
            spaceAfter=14,
            fontName='Helvetica'
        )
        header_style = ParagraphStyle(
            'CoverLetterHeader',
            parent=styles['Normal'],
            fontSize=13,
            leading=18,
            spaceAfter=6,
            fontName='Helvetica-Bold'
        )

        content = []

        # Title
        content.append(Paragraph(f"Cover Letter — {role_title} at {company_name}", header_style))
        content.append(Spacer(1, 0.3 * inch))

        # Body paragraphs
        paragraphs = cover_letter_text.split('\n\n')
        for para in paragraphs:
            clean = para.replace('\n', '<br/>').strip()
            if clean:
                content.append(Paragraph(clean, body_style))

        doc.build(content)
        pdf_bytes = buffer.getvalue()

        filename = f"Cover_Letter_{company_name.replace(' ', '_')}.pdf"

        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({"error": f"Failed to generate PDF: {str(e)}"}), 500


# ─── Mock Interview Simulator ─────────────────────────────────────────────

@app.route('/interview')
@login_required
def interview():
    return render_template('interview.html')


@app.route('/api/mock-interview', methods=['POST'])
@login_required
def mock_interview():
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    history = data.get('history', [])
    resume_text = data.get('resume_text', '')
    role = data.get('role', 'the position')
    interview_type = data.get('interview_type', 'technical')
    turn_count = data.get('turn_count', 0)
    max_turns = data.get('max_turns', 4)

    is_finished = turn_count >= max_turns
    
    # System prompt shaping
    system_prompt = f"""You are an expert {interview_type} interviewer conducting a mock interview for the role of {role}.
    
INSTRUCTIONS:
- You will ask one question at a time.
- Based on the user's previous answer, provide brief, constructive feedback using the exact format: "**Feedback:** [your feedback]".
- Then ask the next question using the format: "**Next Question:** [your question]".
- Tailor your questions based on the candidate's resume: {resume_text[:2000]}...
- Keep your feedback and questions concise (under 150 words total per reply).
- If this is the final turn ({turn_count} of {max_turns}), instead of asking another question, provide a final overall assessment and rating out of 10.
- If this is the FIRST turn (no user messages yet), just introduce yourself and ask the FIRST question.
"""

    if not (github_configured or azure_configured or gemini_configured):
        return jsonify({"error": "No AI service is configured. Please add an API key in your .env file."}), 503

    try:
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            messages.append({"role": msg.get('role'), "content": msg.get('content')})

        if github_configured:
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {github_token}"}
            payload = {
                "model": "gpt-4o-mini",
                "messages": messages,
                "temperature": 0.6,
                "max_tokens": 500
            }
            resp = requests.post("https://models.inference.ai.azure.com/chat/completions", headers=headers, json=payload, timeout=25)
            resp.raise_for_status()
            reply = resp.json()['choices'][0]['message']['content']
        elif azure_configured:
            headers = {"Content-Type": "application/json", "api-key": azure_api_key}
            payload = {
                "messages": messages,
                "temperature": 0.6,
                "max_tokens": 500
            }
            resp = requests.post(azure_endpoint, headers=headers, json=payload, timeout=25)
            resp.raise_for_status()
            reply = resp.json()['choices'][0]['message']['content']
        else:
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=system_prompt,
                generation_config=genai.GenerationConfig(temperature=0.6, max_output_tokens=500)
            )
            # Format history for Gemini
            gemini_history = []
            # Skip system prompt for history, we use system_instruction
            for msg in history[:-1]: # exclude last message to use as prompt
                if msg.get('role') == 'user':
                    gemini_history.append({"role": "user", "parts": [msg.get('content')]})
                else:
                    gemini_history.append({"role": "model", "parts": [msg.get('content')]})
            
            chat_session = model.start_chat(history=gemini_history)
            
            latest_msg = "Hello, I am ready to start the interview."
            if history and history[-1].get('role') == 'user':
                latest_msg = history[-1].get('content')
                
            response = chat_session.send_message(latest_msg)
            reply = response.text

        return jsonify({
            "reply": reply.strip(),
            "is_finished": is_finished
        })

    except Exception as e:
        print(f"DEBUG ERROR in mock-interview: {str(e)}")
        return jsonify({"error": f"AI service error: {str(e)}"}), 503


# ─── Live Resume Builder & LinkedIn Sync ────────────────────────────────

@app.route('/builder')
@login_required
def builder():
    roles = get_available_roles()
    return render_template('builder.html', roles=roles)

@app.route('/api/analyze-live', methods=['POST'])
@login_required
def analyze_live():
    data = request.json
    text = data.get('text', '')
    job_role = data.get('job_role', 'software_engineer')
    job_description = data.get('job_description', '')
    custom_role = data.get('custom_role', '')

    if not text or len(text) < 50:
        return jsonify({"error": "Not enough text"}), 400

    try:
        cache_key = hashlib.sha256((text + job_role + custom_role).encode('utf-8')).hexdigest()
        if cache_key in _result_cache:
            cached = _result_cache[cache_key].copy()
            cached['cached'] = True
            return jsonify(cached)

        results = analyze_resume(text, job_role, job_description, custom_role)
        _result_cache[cache_key] = results.copy()
        
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": f"Error analyzing text: {str(e)}"}), 500

@app.route('/api/import-linkedin', methods=['POST'])
@login_required
def import_linkedin():
    if 'pdf' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['pdf']
    if not file.filename.endswith('.pdf'):
        return jsonify({"error": "Only PDF files are supported"}), 400

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
    file.save(filepath)

    try:
        text = extract_text_from_pdf(filepath)
        if not text or len(text.strip()) < 50:
            return jsonify({"error": "Could not extract text from PDF."}), 400

        system_prompt = """You are an expert resume formatter. I will provide you with raw text extracted from a LinkedIn profile PDF.
Your task is to convert this text into a clean, well-formatted plain-text resume.

Format strictly using standard markdown headings and bullet points:
# Name
## Summary
## Experience
- Company | Title | Dates
  - Bullet points...
## Education
## Skills

Output ONLY the formatted resume text. Do not include any extra commentary.
"""
        user_message = text[:15000] # Safe limit

        if not (github_configured or azure_configured or gemini_configured):
            return jsonify({"formatted_text": text}) # Fallback to raw text

        if github_configured:
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {github_token}"}
            payload = {"model": "gpt-4o-mini", "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}], "temperature": 0.3, "max_tokens": 1500}
            resp = requests.post("https://models.inference.ai.azure.com/chat/completions", headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            formatted_text = resp.json()['choices'][0]['message']['content']
        elif azure_configured:
            headers = {"Content-Type": "application/json", "api-key": azure_api_key}
            payload = {"messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}], "temperature": 0.3, "max_tokens": 1500}
            resp = requests.post(azure_endpoint, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            formatted_text = resp.json()['choices'][0]['message']['content']
        else:
            model = genai.GenerativeModel(model_name="gemini-1.5-flash", system_instruction=system_prompt)
            response = model.generate_content(user_message)
            formatted_text = response.text

        return jsonify({"formatted_text": formatted_text.strip()})

    except Exception as e:
        return jsonify({"error": f"Error parsing LinkedIn PDF: {str(e)}"}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


# ═══════════════════════════════════════════════════════════════════════════
# ─── FEATURE 2: LinkedIn Profile Analyzer ──────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/linkedin-analyzer')
@login_required
def linkedin_analyzer():
    roles = get_available_roles()
    return render_template('linkedin_analyzer.html', roles=roles)


@app.route('/api/analyze-linkedin-url', methods=['POST'])
@login_required
def analyze_linkedin_url():
    """Analyze a LinkedIn profile URL by extracting text and running resume analysis."""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    profile_text = data.get('profile_text', '').strip()
    job_role = data.get('job_role', 'software_engineer')
    custom_role = data.get('custom_role', '')

    if not profile_text or len(profile_text) < 100:
        return jsonify({"error": "Please paste your LinkedIn profile text (at least 100 characters)."}), 400

    try:
        results = analyze_resume(profile_text, job_role, '', custom_role)
        results['source'] = 'linkedin'
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500


# ═══════════════════════════════════════════════════════════════════════════
# ─── FEATURE 3: Resume Comparison Mode ─────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/compare')
@login_required
def compare():
    return render_template('compare.html', roles=get_available_roles())


@app.route('/api/resume-versions', methods=['GET'])
@login_required
def get_resume_versions():
    versions = ResumeVersion.query.filter_by(user_id=current_user.id).order_by(ResumeVersion.created_at.desc()).all()
    return jsonify([v.to_dict() for v in versions])


@app.route('/api/resume-versions', methods=['POST'])
@login_required
def save_resume_version():
    import json
    data = request.json
    if not data or 'resume_text' not in data:
        return jsonify({"error": "resume_text is required"}), 400

    resume_text = data['resume_text']
    job_role = data.get('job_role', 'software_engineer')
    custom_role = data.get('custom_role', '')
    name = data.get('name', f"Version {datetime.now(timezone.utc).strftime('%b %d, %H:%M')}")

    try:
        results = analyze_resume(resume_text, job_role, '', custom_role)
        version = ResumeVersion(
            user_id=current_user.id,
            name=name,
            resume_text=resume_text,
            role=results.get('role', job_role),
            ats_score=results.get('ats_score', {}).get('total', 0),
            found_skills=json.dumps(results.get('found_skills', [])),
            missing_skills=json.dumps(results.get('missing_skills', []))
        )
        db.session.add(version)
        db.session.commit()
        return jsonify(version.to_dict()), 201
    except Exception as e:
        return jsonify({"error": f"Failed to save version: {str(e)}"}), 500


@app.route('/api/resume-versions/<int:version_id>', methods=['DELETE'])
@login_required
def delete_resume_version(version_id):
    version = ResumeVersion.query.get_or_404(version_id)
    if version.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    db.session.delete(version)
    db.session.commit()
    return jsonify({"success": True})


@app.route('/api/compare-versions', methods=['POST'])
@login_required
def compare_versions():
    """Compare two resume versions side by side."""
    data = request.json
    if not data or 'version_a_id' not in data or 'version_b_id' not in data:
        return jsonify({"error": "version_a_id and version_b_id are required"}), 400

    ver_a = ResumeVersion.query.get_or_404(data['version_a_id'])
    ver_b = ResumeVersion.query.get_or_404(data['version_b_id'])

    if ver_a.user_id != current_user.id or ver_b.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    import json
    skills_a = set(json.loads(ver_a.found_skills) if ver_a.found_skills else [])
    skills_b = set(json.loads(ver_b.found_skills) if ver_b.found_skills else [])

    return jsonify({
        "version_a": ver_a.to_dict(),
        "version_b": ver_b.to_dict(),
        "score_diff": ver_b.ats_score - ver_a.ats_score,
        "skills_gained": list(skills_b - skills_a),
        "skills_lost": list(skills_a - skills_b),
        "common_skills": list(skills_a & skills_b),
        "winner": "B" if ver_b.ats_score > ver_a.ats_score else ("A" if ver_a.ats_score > ver_b.ats_score else "Tie")
    })


# ═══════════════════════════════════════════════════════════════════════════
# ─── FEATURE 4: Salary Insights ────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/salary')
@login_required
def salary():
    roles = get_available_roles()
    return render_template('salary.html', roles=roles)


@app.route('/api/salary-insights', methods=['GET'])
@login_required
def salary_insights():
    """Real salary data researched from Glassdoor, Levels.fyi, AmbitionBox, PayScale 2024-2026."""
    role = request.args.get('role', 'Software Engineer')
    location = request.args.get('location', 'United States')

    # Currency config per location
    location_currency = {
        "united states": ("USD", "$"), "usa": ("USD", "$"), "san francisco": ("USD", "$"),
        "new york": ("USD", "$"), "seattle": ("USD", "$"), "austin": ("USD", "$"),
        "boston": ("USD", "$"), "chicago": ("USD", "$"), "los angeles": ("USD", "$"),
        "remote": ("USD", "$"),
        "india": ("INR", "\u20b9"), "bangalore": ("INR", "\u20b9"), "mumbai": ("INR", "\u20b9"),
        "delhi": ("INR", "\u20b9"), "hyderabad": ("INR", "\u20b9"), "pune": ("INR", "\u20b9"),
        "uk": ("GBP", "\u00a3"), "united kingdom": ("GBP", "\u00a3"), "london": ("GBP", "\u00a3"),
        "canada": ("CAD", "C$"), "toronto": ("CAD", "C$"), "vancouver": ("CAD", "C$"),
        "germany": ("EUR", "\u20ac"), "berlin": ("EUR", "\u20ac"), "munich": ("EUR", "\u20ac"),
        "france": ("EUR", "\u20ac"), "paris": ("EUR", "\u20ac"),
        "netherlands": ("EUR", "\u20ac"), "ireland": ("EUR", "\u20ac"),
        "spain": ("EUR", "\u20ac"), "italy": ("EUR", "\u20ac"),
        "australia": ("AUD", "A$"), "sydney": ("AUD", "A$"),
        "singapore": ("SGD", "S$"),
        "japan": ("JPY", "\u00a5"), "tokyo": ("JPY", "\u00a5"),
        "south korea": ("KRW", "\u20a9"), "seoul": ("KRW", "\u20a9"),
        "china": ("CNY", "\u00a5"), "beijing": ("CNY", "\u00a5"),
        "uae": ("AED", "AED"), "dubai": ("AED", "AED"),
        "switzerland": ("CHF", "Fr"), "zurich": ("CHF", "Fr"),
        "brazil": ("BRL", "R$"), "mexico": ("MXN", "MX$"),
        "poland": ("PLN", "z\u0142"), "pakistan": ("PKR", "\u20a8"),
        "bangladesh": ("BDT", "\u09f3"), "nigeria": ("NGN", "\u20a6"),
        "south africa": ("ZAR", "R"), "indonesia": ("IDR", "Rp"),
        "malaysia": ("MYR", "RM"), "philippines": ("PHP", "\u20b1"),
        "vietnam": ("VND", "\u20ab"), "thailand": ("THB", "\u0e3f"),
        "turkey": ("TRY", "\u20ba"), "russia": ("RUB", "\u20bd"),
        "israel": ("ILS", "\u20aa"), "new zealand": ("NZD", "NZ$"),
        "sweden": ("SEK", "kr"), "norway": ("NOK", "kr"), "denmark": ("DKK", "kr"),
        "egypt": ("EGP", "E\u00a3"), "kenya": ("KES", "KSh"),
        "argentina": ("ARS", "AR$"), "colombia": ("COP", "COP$"),
    }

    # Real salary data per role per country (annual, LOCAL CURRENCY)
    # Sources: Levels.fyi, Glassdoor, AmbitionBox, PayScale, Naukri 2024-2026
    real_salaries = {
        "software_engineer": {
            "united states": {"entry": 95000, "mid": 140000, "senior": 190000, "lead": 250000},
            "san francisco": {"entry": 120000, "mid": 170000, "senior": 230000, "lead": 310000},
            "new york": {"entry": 110000, "mid": 155000, "senior": 210000, "lead": 280000},
            "india": {"entry": 600000, "mid": 1500000, "senior": 2800000, "lead": 4500000},
            "uk": {"entry": 35000, "mid": 55000, "senior": 80000, "lead": 110000},
            "london": {"entry": 45000, "mid": 70000, "senior": 95000, "lead": 130000},
            "canada": {"entry": 70000, "mid": 105000, "senior": 145000, "lead": 185000},
            "germany": {"entry": 50000, "mid": 70000, "senior": 95000, "lead": 120000},
            "australia": {"entry": 80000, "mid": 120000, "senior": 160000, "lead": 200000},
            "singapore": {"entry": 60000, "mid": 90000, "senior": 130000, "lead": 170000},
            "japan": {"entry": 4500000, "mid": 7500000, "senior": 11000000, "lead": 15000000},
            "uae": {"entry": 180000, "mid": 300000, "senior": 450000, "lead": 600000},
            "france": {"entry": 38000, "mid": 55000, "senior": 75000, "lead": 100000},
            "netherlands": {"entry": 45000, "mid": 65000, "senior": 90000, "lead": 115000},
            "switzerland": {"entry": 90000, "mid": 130000, "senior": 170000, "lead": 210000},
            "brazil": {"entry": 72000, "mid": 144000, "senior": 240000, "lead": 360000},
            "south korea": {"entry": 40000000, "mid": 65000000, "senior": 95000000, "lead": 130000000},
            "china": {"entry": 200000, "mid": 400000, "senior": 700000, "lead": 1100000},
            "pakistan": {"entry": 600000, "mid": 1500000, "senior": 3000000, "lead": 5000000},
            "poland": {"entry": 84000, "mid": 168000, "senior": 264000, "lead": 360000},
            "israel": {"entry": 240000, "mid": 420000, "senior": 600000, "lead": 780000},
        },
        "ai_engineer": {
            "united states": {"entry": 120000, "mid": 175000, "senior": 240000, "lead": 320000},
            "san francisco": {"entry": 145000, "mid": 210000, "senior": 290000, "lead": 400000},
            "india": {"entry": 800000, "mid": 2000000, "senior": 4000000, "lead": 7000000},
            "uk": {"entry": 50000, "mid": 80000, "senior": 120000, "lead": 160000},
            "london": {"entry": 60000, "mid": 95000, "senior": 140000, "lead": 185000},
            "canada": {"entry": 90000, "mid": 135000, "senior": 185000, "lead": 240000},
            "germany": {"entry": 60000, "mid": 90000, "senior": 125000, "lead": 160000},
            "australia": {"entry": 100000, "mid": 150000, "senior": 200000, "lead": 260000},
            "singapore": {"entry": 80000, "mid": 120000, "senior": 170000, "lead": 220000},
            "japan": {"entry": 6000000, "mid": 10000000, "senior": 15000000, "lead": 22000000},
            "uae": {"entry": 250000, "mid": 420000, "senior": 600000, "lead": 850000},
            "switzerland": {"entry": 110000, "mid": 160000, "senior": 210000, "lead": 270000},
            "china": {"entry": 300000, "mid": 600000, "senior": 1000000, "lead": 1600000},
            "south korea": {"entry": 50000000, "mid": 80000000, "senior": 120000000, "lead": 170000000},
        },
        "data_scientist": {
            "united states": {"entry": 95000, "mid": 135000, "senior": 180000, "lead": 230000},
            "india": {"entry": 600000, "mid": 1400000, "senior": 2500000, "lead": 4000000},
            "uk": {"entry": 35000, "mid": 55000, "senior": 80000, "lead": 110000},
            "canada": {"entry": 75000, "mid": 110000, "senior": 150000, "lead": 195000},
            "germany": {"entry": 50000, "mid": 72000, "senior": 100000, "lead": 130000},
            "australia": {"entry": 85000, "mid": 125000, "senior": 165000, "lead": 210000},
            "singapore": {"entry": 65000, "mid": 95000, "senior": 135000, "lead": 175000},
            "japan": {"entry": 5000000, "mid": 8000000, "senior": 12000000, "lead": 17000000},
            "uae": {"entry": 200000, "mid": 350000, "senior": 500000, "lead": 700000},
        },
        "ml_engineer": {
            "united states": {"entry": 110000, "mid": 160000, "senior": 220000, "lead": 290000},
            "india": {"entry": 700000, "mid": 1800000, "senior": 3500000, "lead": 6000000},
            "uk": {"entry": 45000, "mid": 72000, "senior": 105000, "lead": 140000},
            "canada": {"entry": 85000, "mid": 125000, "senior": 170000, "lead": 220000},
            "germany": {"entry": 58000, "mid": 85000, "senior": 115000, "lead": 150000},
            "australia": {"entry": 95000, "mid": 140000, "senior": 190000, "lead": 245000},
            "singapore": {"entry": 75000, "mid": 110000, "senior": 155000, "lead": 200000},
            "japan": {"entry": 5500000, "mid": 9000000, "senior": 14000000, "lead": 20000000},
        },
        "frontend_developer": {
            "united states": {"entry": 75000, "mid": 110000, "senior": 150000, "lead": 195000},
            "india": {"entry": 400000, "mid": 1000000, "senior": 2000000, "lead": 3200000},
            "uk": {"entry": 30000, "mid": 48000, "senior": 70000, "lead": 95000},
            "canada": {"entry": 60000, "mid": 90000, "senior": 125000, "lead": 160000},
            "germany": {"entry": 42000, "mid": 60000, "senior": 82000, "lead": 105000},
            "australia": {"entry": 70000, "mid": 100000, "senior": 135000, "lead": 170000},
        },
        "backend_developer": {
            "united states": {"entry": 80000, "mid": 120000, "senior": 165000, "lead": 210000},
            "india": {"entry": 500000, "mid": 1200000, "senior": 2200000, "lead": 3600000},
            "uk": {"entry": 33000, "mid": 52000, "senior": 75000, "lead": 100000},
            "canada": {"entry": 65000, "mid": 95000, "senior": 135000, "lead": 170000},
            "germany": {"entry": 45000, "mid": 65000, "senior": 88000, "lead": 112000},
            "australia": {"entry": 75000, "mid": 110000, "senior": 145000, "lead": 185000},
        },
        "full_stack_developer": {
            "united states": {"entry": 78000, "mid": 118000, "senior": 160000, "lead": 205000},
            "india": {"entry": 450000, "mid": 1100000, "senior": 2100000, "lead": 3400000},
            "uk": {"entry": 32000, "mid": 50000, "senior": 72000, "lead": 98000},
            "canada": {"entry": 62000, "mid": 92000, "senior": 130000, "lead": 165000},
            "germany": {"entry": 44000, "mid": 63000, "senior": 85000, "lead": 110000},
            "australia": {"entry": 72000, "mid": 108000, "senior": 142000, "lead": 180000},
        },
        "devops_engineer": {
            "united states": {"entry": 85000, "mid": 125000, "senior": 170000, "lead": 215000},
            "india": {"entry": 600000, "mid": 1400000, "senior": 2600000, "lead": 4200000},
            "uk": {"entry": 38000, "mid": 58000, "senior": 82000, "lead": 110000},
            "canada": {"entry": 72000, "mid": 105000, "senior": 145000, "lead": 185000},
            "germany": {"entry": 50000, "mid": 72000, "senior": 98000, "lead": 125000},
            "australia": {"entry": 85000, "mid": 125000, "senior": 165000, "lead": 205000},
        },
        "cloud_engineer": {
            "united states": {"entry": 90000, "mid": 130000, "senior": 175000, "lead": 220000},
            "india": {"entry": 600000, "mid": 1500000, "senior": 2800000, "lead": 4500000},
            "uk": {"entry": 40000, "mid": 62000, "senior": 88000, "lead": 115000},
            "canada": {"entry": 75000, "mid": 110000, "senior": 150000, "lead": 190000},
            "germany": {"entry": 52000, "mid": 75000, "senior": 102000, "lead": 130000},
            "australia": {"entry": 90000, "mid": 130000, "senior": 170000, "lead": 215000},
        },
        "product_manager": {
            "united states": {"entry": 90000, "mid": 135000, "senior": 185000, "lead": 245000},
            "india": {"entry": 800000, "mid": 1800000, "senior": 3200000, "lead": 5500000},
            "uk": {"entry": 40000, "mid": 62000, "senior": 90000, "lead": 120000},
            "canada": {"entry": 75000, "mid": 110000, "senior": 150000, "lead": 195000},
            "germany": {"entry": 52000, "mid": 75000, "senior": 100000, "lead": 130000},
            "australia": {"entry": 90000, "mid": 130000, "senior": 170000, "lead": 220000},
            "singapore": {"entry": 65000, "mid": 100000, "senior": 140000, "lead": 185000},
        },
        "ux_designer": {
            "united states": {"entry": 70000, "mid": 100000, "senior": 140000, "lead": 180000},
            "india": {"entry": 400000, "mid": 900000, "senior": 1800000, "lead": 3000000},
            "uk": {"entry": 28000, "mid": 45000, "senior": 65000, "lead": 88000},
            "canada": {"entry": 55000, "mid": 80000, "senior": 110000, "lead": 145000},
            "germany": {"entry": 40000, "mid": 58000, "senior": 78000, "lead": 100000},
            "australia": {"entry": 70000, "mid": 100000, "senior": 135000, "lead": 170000},
        },
        "ui_designer": {
            "united states": {"entry": 62000, "mid": 90000, "senior": 125000, "lead": 160000},
            "india": {"entry": 350000, "mid": 700000, "senior": 1400000, "lead": 2400000},
            "uk": {"entry": 25000, "mid": 40000, "senior": 58000, "lead": 78000},
            "canada": {"entry": 50000, "mid": 72000, "senior": 100000, "lead": 130000},
            "germany": {"entry": 36000, "mid": 52000, "senior": 70000, "lead": 92000},
        },
        "data_analyst": {
            "united states": {"entry": 60000, "mid": 85000, "senior": 115000, "lead": 150000},
            "india": {"entry": 350000, "mid": 800000, "senior": 1500000, "lead": 2500000},
            "uk": {"entry": 28000, "mid": 42000, "senior": 60000, "lead": 82000},
            "canada": {"entry": 52000, "mid": 75000, "senior": 105000, "lead": 135000},
            "germany": {"entry": 40000, "mid": 55000, "senior": 75000, "lead": 98000},
            "australia": {"entry": 65000, "mid": 90000, "senior": 120000, "lead": 155000},
        },
        "cybersecurity_analyst": {
            "united states": {"entry": 75000, "mid": 110000, "senior": 150000, "lead": 195000},
            "india": {"entry": 500000, "mid": 1200000, "senior": 2200000, "lead": 3800000},
            "uk": {"entry": 35000, "mid": 55000, "senior": 78000, "lead": 105000},
            "canada": {"entry": 65000, "mid": 95000, "senior": 130000, "lead": 170000},
            "germany": {"entry": 48000, "mid": 68000, "senior": 92000, "lead": 120000},
            "australia": {"entry": 80000, "mid": 115000, "senior": 155000, "lead": 195000},
        },
        "mobile_app_developer": {
            "united states": {"entry": 80000, "mid": 120000, "senior": 160000, "lead": 205000},
            "india": {"entry": 450000, "mid": 1100000, "senior": 2200000, "lead": 3500000},
            "uk": {"entry": 32000, "mid": 50000, "senior": 72000, "lead": 98000},
            "canada": {"entry": 65000, "mid": 95000, "senior": 130000, "lead": 168000},
            "germany": {"entry": 45000, "mid": 65000, "senior": 88000, "lead": 112000},
        },
        "qa_engineer": {
            "united states": {"entry": 60000, "mid": 88000, "senior": 120000, "lead": 155000},
            "india": {"entry": 350000, "mid": 750000, "senior": 1400000, "lead": 2200000},
            "uk": {"entry": 28000, "mid": 42000, "senior": 60000, "lead": 80000},
            "canada": {"entry": 52000, "mid": 75000, "senior": 105000, "lead": 135000},
            "germany": {"entry": 38000, "mid": 55000, "senior": 75000, "lead": 98000},
        },
        "blockchain_developer": {
            "united states": {"entry": 100000, "mid": 150000, "senior": 200000, "lead": 260000},
            "india": {"entry": 700000, "mid": 1600000, "senior": 3000000, "lead": 5000000},
            "uk": {"entry": 45000, "mid": 72000, "senior": 100000, "lead": 135000},
            "canada": {"entry": 80000, "mid": 120000, "senior": 165000, "lead": 210000},
            "singapore": {"entry": 70000, "mid": 105000, "senior": 145000, "lead": 190000},
        },
        "game_developer": {
            "united states": {"entry": 60000, "mid": 90000, "senior": 130000, "lead": 170000},
            "india": {"entry": 350000, "mid": 800000, "senior": 1500000, "lead": 2500000},
            "uk": {"entry": 25000, "mid": 40000, "senior": 60000, "lead": 82000},
            "canada": {"entry": 52000, "mid": 78000, "senior": 110000, "lead": 145000},
            "japan": {"entry": 3500000, "mid": 5500000, "senior": 8000000, "lead": 11000000},
        },
    }

    role_key = role.lower().replace(' ', '_').replace('-', '_')
    loc_lower = location.lower().strip()

    # Find currency
    currency, symbol = "USD", "$"
    for loc_key, (cur, sym) in location_currency.items():
        if loc_key in loc_lower:
            currency, symbol = cur, sym
            break

    # Find salary data
    role_data = real_salaries.get(role_key, real_salaries.get("software_engineer", {}))
    salaries = None
    for loc_key in role_data:
        if loc_key in loc_lower or loc_lower in loc_key:
            salaries = role_data[loc_key]
            break

    # Fallback: city -> country mapping
    if not salaries:
        city_to_country = {
            "bangalore": "india", "mumbai": "india", "delhi": "india",
            "hyderabad": "india", "pune": "india", "chennai": "india",
            "toronto": "canada", "vancouver": "canada",
            "berlin": "germany", "munich": "germany",
            "paris": "france", "amsterdam": "netherlands", "dublin": "ireland",
            "sydney": "australia", "melbourne": "australia",
            "tokyo": "japan", "seoul": "south korea",
            "beijing": "china", "shanghai": "china",
            "sao paulo": "brazil", "tel aviv": "israel",
            "warsaw": "poland", "istanbul": "turkey",
            "zurich": "switzerland",
        }
        country = city_to_country.get(loc_lower, loc_lower)
        salaries = role_data.get(country)

    # Ultimate fallback: US data
    if not salaries:
        salaries = role_data.get("united states", {"entry": 70000, "mid": 105000, "senior": 145000, "lead": 185000})
        currency, symbol = "USD", "$"

    top_companies = {
        "software_engineer": ["Google", "Meta", "Apple", "Netflix", "Stripe"],
        "data_scientist": ["OpenAI", "DeepMind", "Google", "Meta", "Palantir"],
        "ml_engineer": ["OpenAI", "Anthropic", "Google DeepMind", "Meta AI", "Tesla"],
        "ai_engineer": ["OpenAI", "Anthropic", "Google", "Microsoft", "Nvidia"],
        "product_manager": ["Google", "Meta", "Airbnb", "Stripe", "Figma"],
        "devops_engineer": ["Netflix", "Cloudflare", "HashiCorp", "AWS", "Datadog"],
        "frontend_developer": ["Vercel", "Stripe", "Airbnb", "Shopify", "Figma"],
        "backend_developer": ["Google", "Stripe", "Cloudflare", "Databricks", "Snowflake"],
        "cybersecurity_analyst": ["CrowdStrike", "Palo Alto", "Fortinet", "Zscaler", "SentinelOne"],
        "blockchain_developer": ["Coinbase", "Binance", "Solana Labs", "Polygon", "Chainlink"],
    }
    companies = top_companies.get(role_key, ["Google", "Microsoft", "Amazon", "Apple", "Meta"])

    return jsonify({
        "role": role,
        "location": location,
        "currency": currency,
        "currency_symbol": symbol,
        "salaries": salaries,
        "top_companies": companies,
        "market_trend": "Growing" if role_key in ["ai_engineer", "ml_engineer", "data_scientist", "cloud_engineer", "cybersecurity_analyst"] else "Stable",
        "demand": "Very High" if role_key in ["ai_engineer", "ml_engineer"] else "High",
        "yoe_breakdown": [
            {"years": "0-2 years", "salary": salaries["entry"]},
            {"years": "3-5 years", "salary": salaries["mid"]},
            {"years": "6-9 years", "salary": salaries["senior"]},
            {"years": "10+ years", "salary": salaries["lead"]},
        ]
    })


# ═══════════════════════════════════════════════════════════════════════════
# ─── FEATURE 6: Application Email Draft Generator ──────────────────────
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/api/generate-followup-email', methods=['POST'])
@login_required
def generate_followup_email():
    """Generate a follow-up email for a job application."""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    company = data.get('company', 'the company')
    role = data.get('role', 'the position')
    days_since = data.get('days_since', 7)
    user_name = current_user.name
    email_type = data.get('email_type', 'followup')  # followup, thank_you, withdraw

    prompts = {
        'followup': f"""Write a professional, concise follow-up email from {user_name} to the hiring team at {company} for the {role} position. 
It has been {days_since} days since they applied. The email should:
- Be polite and professional
- Reiterate interest in the role
- Ask for an update on the application status
- Be under 150 words
Output ONLY the email text.""",
        'thank_you': f"""Write a professional thank-you email from {user_name} after an interview at {company} for the {role} position.
The email should:
- Thank the interviewer for their time
- Reiterate enthusiasm for the role
- Briefly mention one key point from the interview
- Be under 150 words
Output ONLY the email text.""",
        'withdraw': f"""Write a professional email from {user_name} to withdraw their application at {company} for the {role} position.
The email should:
- Be polite and gracious
- Thank them for their consideration
- Briefly mention they have accepted another opportunity (without details)
- Keep the door open for future opportunities
- Be under 100 words
Output ONLY the email text."""
    }

    prompt = prompts.get(email_type, prompts['followup'])

    if not (github_configured or azure_configured or gemini_configured):
        return jsonify({"error": "No AI service configured."}), 503

    try:
        if github_configured:
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {github_token}"}
            payload = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}], "temperature": 0.5, "max_tokens": 300}
            resp = requests.post("https://models.inference.ai.azure.com/chat/completions", headers=headers, json=payload, timeout=20)
            resp.raise_for_status()
            email_text = resp.json()['choices'][0]['message']['content']
        elif azure_configured:
            headers = {"Content-Type": "application/json", "api-key": azure_api_key}
            payload = {"messages": [{"role": "user", "content": prompt}], "temperature": 0.5, "max_tokens": 300}
            resp = requests.post(azure_endpoint, headers=headers, json=payload, timeout=20)
            resp.raise_for_status()
            email_text = resp.json()['choices'][0]['message']['content']
        else:
            model = genai.GenerativeModel(model_name="gemini-1.5-flash")
            response = model.generate_content(prompt)
            email_text = response.text

        return jsonify({"email": email_text.strip()})
    except Exception as e:
        return jsonify({"error": f"AI error: {str(e)}"}), 503


# ═══════════════════════════════════════════════════════════════════════════
# ─── FEATURE 7: Skill Progress Tracker ─────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/api/skill-progress', methods=['GET'])
@login_required
def get_skill_progress():
    role = request.args.get('role', '')
    query = SkillProgress.query.filter_by(user_id=current_user.id)
    if role:
        query = query.filter_by(role=role)
    skills = query.all()
    return jsonify([s.to_dict() for s in skills])


@app.route('/api/skill-progress', methods=['POST'])
@login_required
def add_skill_progress():
    """Add skills to track for a role."""
    import json
    data = request.json
    if not data or 'skills' not in data or 'role' not in data:
        return jsonify({"error": "skills and role are required"}), 400

    role = data['role']
    skills = data['skills']
    added = []

    for skill_name in skills:
        existing = SkillProgress.query.filter_by(
            user_id=current_user.id, skill_name=skill_name.lower(), role=role
        ).first()
        if not existing:
            sp = SkillProgress(user_id=current_user.id, skill_name=skill_name.lower(), role=role)
            db.session.add(sp)
            added.append(skill_name)

    db.session.commit()
    return jsonify({"added": added, "count": len(added)}), 201


@app.route('/api/skill-progress/<int:skill_id>', methods=['PUT'])
@login_required
def update_skill_progress(skill_id):
    """Mark a skill as learned or unlearned."""
    from datetime import datetime, timezone as tz
    sp = SkillProgress.query.get_or_404(skill_id)
    if sp.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    sp.learned = data.get('learned', sp.learned)
    sp.learned_at = datetime.now(tz.utc) if sp.learned else None
    db.session.commit()

    # Create notification when skill is learned
    if sp.learned:
        notif = Notification(
            user_id=current_user.id,
            title="Skill Unlocked! 🎉",
            message=f"You marked '{sp.skill_name}' as learned. Keep going!",
            type="success",
            link="/compare"
        )
        db.session.add(notif)
        db.session.commit()

    return jsonify(sp.to_dict())


# ═══════════════════════════════════════════════════════════════════════════
# ─── FEATURE 8: Interview Answer Bank ──────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/answer-bank')
@login_required
def answer_bank():
    return render_template('answer_bank.html')


@app.route('/api/interview-answers', methods=['GET'])
@login_required
def get_interview_answers():
    category = request.args.get('category', '')
    query = InterviewAnswer.query.filter_by(user_id=current_user.id)
    if category:
        query = query.filter_by(category=category)
    answers = query.order_by(InterviewAnswer.created_at.desc()).all()
    return jsonify([a.to_dict() for a in answers])


@app.route('/api/interview-answers', methods=['POST'])
@login_required
def save_interview_answer():
    data = request.json
    if not data or 'question' not in data or 'answer' not in data:
        return jsonify({"error": "question and answer are required"}), 400

    answer = InterviewAnswer(
        user_id=current_user.id,
        question=data['question'],
        answer=data['answer'],
        category=data.get('category', 'general'),
        role=data.get('role', ''),
        rating=data.get('rating')
    )
    db.session.add(answer)
    db.session.commit()
    return jsonify(answer.to_dict()), 201


@app.route('/api/interview-answers/<int:answer_id>', methods=['PUT'])
@login_required
def update_interview_answer(answer_id):
    ans = InterviewAnswer.query.get_or_404(answer_id)
    if ans.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    data = request.json
    if 'answer' in data:
        ans.answer = data['answer']
    if 'rating' in data:
        ans.rating = data['rating']
    if 'category' in data:
        ans.category = data['category']
    db.session.commit()
    return jsonify(ans.to_dict())


@app.route('/api/interview-answers/<int:answer_id>', methods=['DELETE'])
@login_required
def delete_interview_answer(answer_id):
    ans = InterviewAnswer.query.get_or_404(answer_id)
    if ans.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    db.session.delete(ans)
    db.session.commit()
    return jsonify({"success": True})


# ═══════════════════════════════════════════════════════════════════════════
# ─── FEATURE 9: Share Analysis (Public Read-Only Link) ─────────────────
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/api/share-analysis', methods=['POST'])
@login_required
def share_analysis():
    """Generate a shareable token for an analysis result."""
    import json, secrets
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Store in cache with a random token
    token = secrets.token_urlsafe(16)
    share_data = {
        'role': data.get('role', ''),
        'ats_score': data.get('ats_score', {}),
        'found_skills': data.get('found_skills', []),
        'missing_skills': data.get('missing_skills', []),
        'strengths': data.get('strengths', []),
        'weaknesses': data.get('weaknesses', []),
        'shared_by': current_user.name,
        'shared_at': datetime.now(timezone.utc).isoformat()
    }
    _result_cache[f'share_{token}'] = share_data
    share_url = f"/shared/{token}"
    return jsonify({"token": token, "url": share_url})


@app.route('/shared/<token>')
def view_shared_analysis(token):
    """Public read-only view of a shared analysis."""
    data = _result_cache.get(f'share_{token}')
    if not data:
        return render_template('404.html'), 404
    return render_template('shared_analysis.html', data=data, token=token)


# ═══════════════════════════════════════════════════════════════════════════
# ─── FEATURE 10: Notifications Center ──────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/api/notifications', methods=['GET'])
@login_required
def get_notifications():
    notifs = Notification.query.filter_by(user_id=current_user.id).order_by(
        Notification.created_at.desc()
    ).limit(50).all()
    unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({
        "notifications": [n.to_dict() for n in notifs],
        "unread_count": unread_count
    })


@app.route('/api/notifications/<int:notif_id>/read', methods=['PUT'])
@login_required
def mark_notification_read(notif_id):
    notif = Notification.query.get_or_404(notif_id)
    if notif.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    notif.is_read = True
    db.session.commit()
    return jsonify({"success": True})


@app.route('/api/notifications/read-all', methods=['PUT'])
@login_required
def mark_all_notifications_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify({"success": True})


@app.route('/api/notifications', methods=['POST'])
@login_required
def create_notification():
    """Internal: create a notification for the current user."""
    data = request.json
    if not data or 'title' not in data or 'message' not in data:
        return jsonify({"error": "title and message required"}), 400
    notif = Notification(
        user_id=current_user.id,
        title=data['title'],
        message=data['message'],
        type=data.get('type', 'info'),
        link=data.get('link')
    )
    db.session.add(notif)
    db.session.commit()
    return jsonify(notif.to_dict()), 201


# ─── Helper: Auto-create stale application notifications ─────────────────

def create_stale_app_notifications(app_obj, mail_obj):
    """Called by scheduler — also creates in-app notifications."""
    from datetime import timedelta
    with app_obj.app_context():
        threshold_date = datetime.now(timezone.utc) - timedelta(days=7)
        stale_apps = JobApplication.query.filter(
            JobApplication.status.in_(['Applied', 'Interviewing']),
            JobApplication.applied_at <= threshold_date
        ).all()
        for app_record in stale_apps:
            if app_record.last_reminded_at and app_record.last_reminded_at > threshold_date:
                continue
            # Create in-app notification
            existing = Notification.query.filter_by(
                user_id=app_record.user_id,
                link=f"/tracker"
            ).filter(
                Notification.message.contains(app_record.company)
            ).filter(
                Notification.created_at > threshold_date
            ).first()
            if not existing:
                notif = Notification(
                    user_id=app_record.user_id,
                    title="Follow-up Reminder 📬",
                    message=f"It's been 7+ days since you applied to {app_record.company} for '{app_record.role}'. Consider sending a follow-up!",
                    type="reminder",
                    link="/tracker"
                )
                db.session.add(notif)
        db.session.commit()



# ═══════════════════════════════════════════════════════════════════════════
# ─── PROFILE ROUTES ────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/api/profile/update-name', methods=['POST'])
@login_required
def update_name():
    data = request.json
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({"error": "Name cannot be empty"}), 400
    if len(name) > 150:
        return jsonify({"error": "Name too long"}), 400
    current_user.name = name
    db.session.commit()
    return jsonify({"message": "Name updated", "name": name})

@app.route('/api/profile/update-email', methods=['POST'])
@login_required
def update_email():
    data = request.json
    email = (data.get('email') or '').strip().lower()
    if not email:
        return jsonify({"error": "Email cannot be empty"}), 400
    if not User.validate_email(email):
        return jsonify({"error": "Invalid email format"}), 400
    if current_user.provider == 'google':
        return jsonify({"error": "Google accounts cannot change email here"}), 400
    existing = User.query.filter_by(email=email).first()
    if existing and existing.id != current_user.id:
        return jsonify({"error": "Email already in use"}), 409
    current_user.email = email
    db.session.commit()
    return jsonify({"message": "Email updated", "email": email})

@app.route('/api/profile/change-password', methods=['POST'])
@login_required
def change_password():
    data = request.json
    current_pwd = data.get('current_password', '')
    new_pwd = data.get('new_password', '')
    if current_user.provider == 'google':
        return jsonify({"error": "Google accounts cannot change password here"}), 400
    if not current_user.check_password(current_pwd):
        return jsonify({"error": "Current password is incorrect"}), 401
    valid, msg = User.validate_password(new_pwd)
    if not valid:
        return jsonify({"error": msg}), 400
    current_user.set_password(new_pwd)
    db.session.commit()
    return jsonify({"message": "Password changed successfully"})

@app.route('/api/profile/clear-history', methods=['DELETE'])
@login_required
def clear_history():
    ResumeHistory.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return jsonify({"message": "History cleared"})

@app.route('/api/profile/delete-account', methods=['DELETE'])
@login_required
def delete_account():
    from flask_login import logout_user
    user_id = current_user.id
    logout_user()
    # Delete all related data
    ResumeHistory.query.filter_by(user_id=user_id).delete()
    ResumeVersion.query.filter_by(user_id=user_id).delete()
    SkillProgress.query.filter_by(user_id=user_id).delete()
    InterviewAnswer.query.filter_by(user_id=user_id).delete()
    Notification.query.filter_by(user_id=user_id).delete()
    JobApplication.query.filter_by(user_id=user_id).delete()
    User.query.filter_by(id=user_id).delete()
    db.session.commit()
    return jsonify({"message": "Account deleted"})



# ═══════════════════════════════════════════════════════════════════════════
# ─── FEEDBACK ROUTES ───────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/api/feedback', methods=['GET'])
def get_feedback():
    """Public: Get approved feedback for landing page."""
    feedbacks = Feedback.query.filter_by(is_approved=True)\
        .order_by(Feedback.created_at.desc()).limit(20).all()
    return jsonify([f.to_dict() for f in feedbacks])

@app.route('/api/feedback', methods=['POST'])
@login_required
def submit_feedback():
    """Submit a review (logged in users only)."""
    data = request.json
    rating = data.get('rating')
    review = (data.get('review') or '').strip()
    job_title = (data.get('job_title') or '').strip()

    if not rating or not isinstance(rating, int) or not (1 <= rating <= 5):
        return jsonify({"error": "Rating must be 1-5"}), 400
    if not review or len(review) < 10:
        return jsonify({"error": "Review must be at least 10 characters"}), 400
    if len(review) > 500:
        return jsonify({"error": "Review too long (max 500 chars)"}), 400

    # One review per user
    existing = Feedback.query.filter_by(user_id=current_user.id).first()
    if existing:
        # Update existing
        existing.rating = rating
        existing.review = review
        existing.job_title = job_title
        db.session.commit()
        return jsonify({"message": "Review updated!", "feedback": existing.to_dict()})

    fb = Feedback(
        user_id=current_user.id,
        rating=rating,
        review=review,
        job_title=job_title
    )
    db.session.add(fb)
    db.session.commit()
    return jsonify({"message": "Thank you for your feedback!", "feedback": fb.to_dict()}), 201

@app.route('/api/feedback/mine', methods=['GET'])
@login_required
def get_my_feedback():
    """Get current user's feedback."""
    fb = Feedback.query.filter_by(user_id=current_user.id).first()
    if fb:
        return jsonify(fb.to_dict())
    return jsonify(None)

@app.route('/api/feedback/<int:fb_id>', methods=['DELETE'])
@login_required
def delete_feedback(fb_id):
    """Delete own feedback."""
    fb = Feedback.query.filter_by(id=fb_id, user_id=current_user.id).first()
    if not fb:
        return jsonify({"error": "Not found"}), 404
    db.session.delete(fb)
    db.session.commit()
    return jsonify({"message": "Feedback deleted"})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)
