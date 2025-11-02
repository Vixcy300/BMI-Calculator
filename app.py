"""
Upgraded Lifestyle - BMI & Wellness Web Application
Backend Flask server with MongoDB database and Google Gemini AI integration
Complete implementation with Email Reports, PDF Generation, and AI Chat
"""

import os
import hashlib
import smtplib
from datetime import datetime
from bson.objectid import ObjectId
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
import google.generativeai as genai
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from PIL import Image
from io import BytesIO
import base64
import random
import traceback

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'webp'}

# Session configuration
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600

# Create uploads directory
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Enable CORS
CORS(app, supports_credentials=True, resources={
    r"/*": {
        "origins": ["*"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

# MongoDB Connection
MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    raise ValueError("MONGODB_URI not found in environment variables")

try:
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    db = client["upgraded_lifestyle"]
    users_collection = db["users"]
    bmi_records_collection = db["bmi_records"]
    analyzed_reports_collection = db["analyzed_reports"]
    user_goals_collection = db["user_goals"]
    chat_messages_collection = db["chat_messages"]

    # Create indexes with error handling
    try:
        users_collection.create_index("username", unique=True)
        users_collection.create_index("email", unique=True)
        bmi_records_collection.create_index("user_id")
        analyzed_reports_collection.create_index("user_id")
        user_goals_collection.create_index("user_id")
        chat_messages_collection.create_index("user_id")
        print("✓ MongoDB connected and indexes created")
    except Exception as e:
        print(f"⚠ Index creation warning (non-critical): {e}")
        print("✓ MongoDB connected (indexes may already exist)")
        
except Exception as e:
    print(f"✗ MongoDB connection error: {e}")
    raise

# Configure Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
model = None
vision_model = None

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        try:
            model = genai.GenerativeModel('models/gemini-2.5-flash')
            print("✓ Gemini API initialized with gemini-2.5-flash")
        except Exception as e1:
            try:
                model = genai.GenerativeModel('models/gemini-1.5-flash')
                print("✓ Gemini API initialized with gemini-1.5-flash")
            except Exception as e2:
                try:
                    model = genai.GenerativeModel('models/gemini-pro')
                    print("✓ Gemini API initialized with gemini-pro")
                except Exception as e3:
                    print(f"✗ Failed to initialize Gemini model: {e3}")
                    model = None
        
        # Initialize Vision model
        try:
            vision_model = genai.GenerativeModel('models/gemini-2.5-flash')
            print("✓ Gemini Vision API initialized with gemini-2.5-flash")
        except:
            try:
                vision_model = genai.GenerativeModel('models/gemini-1.5-flash')
                print("✓ Gemini Vision API initialized with gemini-1.5-flash")
            except:
                vision_model = model
                print("⚠ Using text model for vision (limited)")
    except Exception as e:
        print(f"✗ Gemini API configuration error: {e}")
        model = None
else:
    print("⚠ Warning: GEMINI_API_KEY not found in .env file")
    model = None

# Utility Functions
def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    """Decorator to check if user is logged in"""
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

def get_bmi_category(bmi):
    """Get BMI category based on BMI value"""
    if bmi < 18.5:
        return 'Underweight'
    elif bmi < 25:
        return 'Normal'
    elif bmi < 30:
        return 'Overweight'
    else:
        return 'Obese'

def get_bmi_icon(category):
    """Get emoji icon for BMI category"""
    icons = {
        'Underweight': '💪',
        'Normal': '✅',
        'Overweight': '⚠️',
        'Obese': '🔴'
    }
    return icons.get(category, '📊')

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def send_email(recipient_email, subject, html_content):
    """Send email via SMTP"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = os.getenv('SMTP_USER')
        msg['To'] = recipient_email
        
        part = MIMEText(html_content, 'html')
        msg.attach(part)
        
        server = smtplib.SMTP(os.getenv('SMTP_SERVER'), int(os.getenv('SMTP_PORT')))
        server.starttls()
        server.login(os.getenv('SMTP_USER'), os.getenv('SMTP_PASSWORD'))
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Email send error: {e}")
        return False

def generate_bmi_pdf(user_data, bmi_data, analysis_data=None):
    """Generate PDF report with BMI data"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        textColor=colors.HexColor('#ff6b9d'),
        fontSize=24,
        spaceAfter=30,
    )

    # Title
    story.append(Paragraph("BMI Health Report", title_style))
    story.append(Spacer(1, 12))
    
    # Capstone Project Info
    capstone_style = ParagraphStyle(
        'Capstone',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey,
        alignment=0
    )
    story.append(Paragraph("Capstone Project by <b>VIGNESH</b>, SIMATS Engineering Student", capstone_style))
    story.append(Spacer(1, 20))
    
    # User Info
    story.append(Paragraph(f"<b>Generated for:</b> {user_data.get('username', 'User')}", styles['Normal']))
    story.append(Paragraph(f"<b>Email:</b> {user_data.get('email', 'N/A')}", styles['Normal']))
    story.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%B %d, %Y')}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # BMI Data
    if bmi_data:
        story.append(Paragraph("<b>BMI Calculation Results</b>", styles['Heading2']))
        story.append(Spacer(1, 12))
        
        bmi_table_data = [
            ['Metric', 'Value'],
            ['Name', bmi_data.get('name', 'N/A')],
            ['Age', str(bmi_data.get('age', 'N/A'))],
            ['Sex', bmi_data.get('sex', 'N/A')],
            ['Height (cm)', str(bmi_data.get('height', 'N/A'))],
            ['Weight (kg)', str(bmi_data.get('weight', 'N/A'))],
            ['BMI', str(bmi_data.get('bmi', 'N/A'))],
            ['Category', bmi_data.get('category', 'N/A')],
        ]
        
        bmi_table = Table(bmi_table_data, colWidths=[3*72, 3*72])
        bmi_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ff6b9d')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(bmi_table)
        story.append(Spacer(1, 20))
    
    # AI Analysis / Routine / Diet Sections
    if analysis_data:
        story.append(Paragraph("<b>AI Analysis</b>", styles['Heading2']))
        story.append(Spacer(1, 8))
        
        overview = analysis_data.get('overview') if isinstance(analysis_data, dict) else None
        if overview:
            story.append(Paragraph("<b>Overview:</b>", styles['Normal']))
            story.append(Paragraph(overview, styles['Normal']))
            story.append(Spacer(1, 8))
        
        suggestions = analysis_data.get('suggestions') if isinstance(analysis_data, dict) else None
        if suggestions:
            story.append(Paragraph("<b>Suggestions:</b>", styles['Normal']))
            story.append(Paragraph(suggestions, styles['Normal']))
            story.append(Spacer(1, 10))
        
        routine_text = analysis_data.get('routine') if isinstance(analysis_data, dict) else None
        if routine_text:
            story.append(Paragraph("<b>Personalized Exercise Routine</b>", styles['Heading3']))
            story.append(Spacer(1, 6))
            story.append(Paragraph(routine_text, styles['Normal']))
            story.append(Spacer(1, 10))
        
        diet_text = analysis_data.get('diet') if isinstance(analysis_data, dict) else None
        if diet_text:
            story.append(Paragraph("<b>Diet Recommendations</b>", styles['Heading3']))
            story.append(Spacer(1, 6))
            story.append(Paragraph(diet_text, styles['Normal']))
            story.append(Spacer(1, 10))
        
        if not any([overview, suggestions, routine_text, diet_text]):
            story.append(Paragraph('No AI analysis available for this report.', styles['Normal']))
            story.append(Spacer(1, 10))
    
    # Footer
    story.append(Spacer(1, 30))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=1,
    )
    story.append(Paragraph("Upgraded Lifestyle - Capstone Project by Vignesh, SIMATS Engineering", footer_style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

# API Routes
@app.route('/')
def index():
    """Health check endpoint"""
    return jsonify({
        'message': 'Upgraded Lifestyle API Running',
        'status': 'online',
        'version': '1.0.0'
    })

@app.route('/register', methods=['POST'])
def register():
    """User registration endpoint"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not email or not password:
            return jsonify({'success': False, 'error': 'All fields are required'}), 400
        
        if len(username) < 3:
            return jsonify({'success': False, 'error': 'Username must be at least 3 characters'}), 400
        
        if len(password) < 6:
            return jsonify({'success': False, 'error': 'Password must be at least 6 characters'}), 400
        
        if '@' not in email:
            return jsonify({'success': False, 'error': 'Invalid email format'}), 400
        
        hashed_password = hash_password(password)
        
        try:
            result = users_collection.insert_one({
                'username': username,
                'email': email,
                'password': hashed_password,
                'created_at': datetime.now()
            })
            
            session.permanent = True
            session['user_id'] = str(result.inserted_id)
            session['username'] = username
            
            return jsonify({'success': True, 'message': 'Registration successful'})
        except DuplicateKeyError:
            return jsonify({'success': False, 'error': 'Username or email already exists'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return jsonify({'success': False, 'error': 'Username and password are required'}), 400
        
        hashed_password = hash_password(password)
        user = users_collection.find_one({
            'username': username,
            'password': hashed_password
        })
        
        if user:
            session.permanent = True
            session['user_id'] = str(user['_id'])
            session['username'] = user['username']
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': {'id': str(user['_id']), 'username': user['username']}
            })
        else:
            return jsonify({'success': False, 'error': 'Invalid username or password'}), 401
            
    except Exception as e:
        print(f"Login error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/logout', methods=['POST'])
def logout():
    """User logout endpoint"""
    session.clear()
    return jsonify({'success': True})

@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    """Check if user is authenticated"""
    if 'user_id' in session:
        return jsonify({
            'authenticated': True,
            'username': session.get('username', '')
        })
    return jsonify({'authenticated': False})

@app.route('/api/user-profile', methods=['GET'])
@login_required
def user_profile():
    """Get logged-in user profile"""
    try:
        user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
        if user:
            return jsonify({
                'username': user['username'],
                'email': user['email']
            })
        return jsonify({'error': 'User not found'}), 404
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/calculate-bmi', methods=['POST'])
@login_required
def calculate_bmi():
    """Calculate BMI and save to database"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        age = int(data.get('age', 0))
        sex = data.get('sex', '').strip()
        height = float(data.get('height', 0))
        weight = float(data.get('weight', 0))
        
        # Validation
        if not name or not age or not sex or not height or not weight:
            return jsonify({'error': 'All fields are required'}), 400
        
        if age < 13 or age > 120:
            return jsonify({'error': 'Age must be between 13 and 120'}), 400
        
        if height < 100 or height > 300:
            return jsonify({'error': 'Height must be between 100 and 300 cm'}), 400
        
        if weight < 20 or weight > 500:
            return jsonify({'error': 'Weight must be between 20 and 500 kg'}), 400
        
        # Calculate BMI
        height_m = height / 100
        bmi = round(weight / (height_m ** 2), 1)
        category = get_bmi_category(bmi)
        icon = get_bmi_icon(category)
        
        # Save to database
        result = bmi_records_collection.insert_one({
            'user_id': ObjectId(session['user_id']),
            'name': name,
            'age': age,
            'sex': sex,
            'height': height,
            'weight': weight,
            'bmi': bmi,
            'category': category,
            'created_at': datetime.now()
        })
        
        return jsonify({
            'bmi': bmi,
            'category': category,
            'icon': icon,
            'saved': True,
            'record_id': str(result.inserted_id)
        })
        
    except ValueError:
        return jsonify({'error': 'Invalid input format'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bmi-history', methods=['GET'])
@login_required
def bmi_history():
    """Get all BMI records for logged-in user"""
    try:
        records = list(bmi_records_collection.find({
            'user_id': ObjectId(session['user_id'])
        }).sort('created_at', -1).limit(50))
        
        history = [{
            'id': str(r['_id']),
            'name': r['name'],
            'age': r['age'],
            'sex': r['sex'],
            'height': r['height'],
            'weight': r['weight'],
            'bmi': r['bmi'],
            'category': r['category'],
            'created_at': r['created_at'].isoformat() if isinstance(r['created_at'], datetime) else str(r['created_at'])
        } for r in records]
        
        return jsonify({'records': history})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete-record/<record_id>', methods=['DELETE'])
@login_required
def delete_record(record_id):
    """Delete a specific BMI record"""
    try:
        # Verify record belongs to user
        record = bmi_records_collection.find_one({
            '_id': ObjectId(record_id),
            'user_id': ObjectId(session['user_id'])
        })
        if not record:
            return jsonify({'error': 'Record not found'}), 404
        
        # Delete record
        bmi_records_collection.delete_one({'_id': ObjectId(record_id)})
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/aurora-chat', methods=['POST'])
@login_required
def aurora_chat():
    """Handle Aurora AI chat messages using Gemini API"""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Save user message
        chat_messages_collection.insert_one({
            'user_id': ObjectId(session['user_id']),
            'role': 'user',
            'message': message,
            'created_at': datetime.now()
        })
        
        # Try Gemini API first
        if model:
            try:
                developer_info = """
IMPORTANT: About the developer/owner:
- The developer and owner of this application is Vignesh
- This is a Capstone Project created by Vignesh, a SIMATS Engineering Student
- If asked about the developer, owner, creator, or who made this app, mention that it was created by Vignesh as part of his capstone project at SIMATS Engineering
- Always mention it's a capstone project when discussing the developer
"""
                
                # Check if user is asking about developer/owner
                message_lower = message.lower()
                is_about_developer = any(word in message_lower for word in ['developer', 'owner', 'created', 'made', 'who made', 'who created', 'vignesh', 'creator', 'author'])
                
                if is_about_developer:
                    prompt = f"""You are Aurora, a friendly AI wellness assistant. {developer_info}
User: {message}
Aurora:"""
                else:
                    prompt = f"""You are Aurora, a friendly and helpful AI wellness assistant. You provide helpful, encouraging advice about BMI, health, fitness, nutrition, and wellness. Keep responses concise (2-3 sentences max) and supportive. Be conversational and helpful.
User: {message}
Aurora:"""
                
                response = model.generate_content(prompt)
                ai_response = response.text.strip()
                
                # Clean up the response
                if ai_response.startswith("Aurora:"):
                    ai_response = ai_response[7:].strip()
                
                print(f"✓ Gemini API response received: {ai_response[:100]}...")
                
                # Save bot message to DB
                chat_messages_collection.insert_one({
                    'user_id': ObjectId(session['user_id']),
                    'role': 'bot',
                    'message': ai_response,
                    'created_at': datetime.now()
                })
                
                return jsonify({
                    'response': ai_response,
                    'success': True
                })
            except Exception as e:
                print(f"✗ Gemini API error: {type(e).__name__}: {e}")
                traceback.print_exc()
        
        # Fallback responses
        fallback_responses = [
            "I'm here to help you with your wellness journey! Feel free to ask me about BMI, nutrition, or fitness.",
            "That's a great question! For personalized advice, consider consulting with a healthcare professional.",
            "Remember, maintaining a balanced diet and regular exercise are key to a healthy lifestyle!",
            "Every body is unique! Focus on overall wellness rather than just numbers.",
            "I'm currently having trouble connecting, but I'm here to support your health goals!"
        ]
        
        fallback = random.choice(fallback_responses)
        
        # Save fallback bot message
        chat_messages_collection.insert_one({
            'user_id': ObjectId(session['user_id']),
            'role': 'bot',
            'message': fallback,
            'created_at': datetime.now()
        })
        
        return jsonify({
            'response': fallback,
            'success': True
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze-image', methods=['POST'])
@login_required
def analyze_image():
    """Analyze uploaded image with Gemini Vision"""
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Allowed: PNG, JPG, JPEG, GIF, WEBP'}), 400
        
        # Save uploaded file
        filename = secure_filename(f"{session['user_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Analyze image with Gemini Vision
        if not vision_model:
            return jsonify({'error': 'Vision model not available'}), 500
        
        try:
            # Read and prepare image
            img = Image.open(filepath)
            
            # Create analysis prompt
            analysis_prompt = """Analyze this BMI report or health-related document image. Provide:
1. Overview: A brief summary of what you see in this report
2. Key Findings: Important numbers, values, or data points
3. Analysis: What these findings mean
4. Suggestions: Actionable health recommendations based on the report
5. Report Type: What kind of report this appears to be (BMI report, lab results, etc.)
Format your response clearly with these sections."""
            
            response = vision_model.generate_content([analysis_prompt, img])
            analysis_text = response.text.strip()
            
            # Extract sections from analysis
            overview = ""
            suggestions = ""
            report_type = "Unknown"
            
            # Simple parsing of analysis
            if "Overview:" in analysis_text:
                parts = analysis_text.split("Overview:")
                if len(parts) > 1:
                    overview = parts[1].split("Key Findings:")[0].strip() if "Key Findings:" in parts[1] else parts[1][:200].strip()
            
            if "Suggestions:" in analysis_text:
                suggestions = analysis_text.split("Suggestions:")[1].strip()[:500]
            
            if "Report Type:" in analysis_text:
                report_type = analysis_text.split("Report Type:")[1].strip().split("\n")[0]
            
            # Save analysis to database
            result = analyzed_reports_collection.insert_one({
                'user_id': ObjectId(session['user_id']),
                'image_filename': filename,
                'analysis_text': analysis_text,
                'suggestions': suggestions,
                'overview': overview,
                'report_type': report_type,
                'created_at': datetime.now()
            })
            
            return jsonify({
                'success': True,
                'report_id': str(result.inserted_id),
                'analysis': analysis_text,
                'overview': overview,
                'suggestions': suggestions,
                'report_type': report_type,
                'filename': filename
            })
            
        except Exception as e:
            print(f"Vision analysis error: {e}")
            traceback.print_exc()
            return jsonify({'error': f'Image analysis failed: {str(e)}'}), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyzed-reports', methods=['GET'])
@login_required
def get_analyzed_reports():
    """Get all analyzed reports for user"""
    try:
        reports = list(analyzed_reports_collection.find({
            'user_id': ObjectId(session['user_id'])
        }).sort('created_at', -1).limit(50))
        
        result = [{
            'id': str(r['_id']),
            'image_filename': r['image_filename'],
            'analysis': r['analysis_text'],
            'suggestions': r['suggestions'],
            'overview': r['overview'],
            'report_type': r['report_type'],
            'created_at': r['created_at'].isoformat() if isinstance(r['created_at'], datetime) else str(r['created_at'])
        } for r in reports]
        
        return jsonify({'reports': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyzed-reports/<report_id>', methods=['DELETE'])
@login_required
def delete_analyzed_report(report_id):
    """Delete a specific analyzed report"""
    try:
        # Verify report belongs to user
        report = analyzed_reports_collection.find_one({
            '_id': ObjectId(report_id),
            'user_id': ObjectId(session['user_id'])
        })
        if not report:
            return jsonify({'error': 'Report not found'}), 404
        
        # Delete database record
        analyzed_reports_collection.delete_one({'_id': ObjectId(report_id)})
        
        # Attempt to delete the uploaded file
        try:
            if report['image_filename']:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], report['image_filename'])
                if os.path.exists(file_path):
                    os.remove(file_path)
        except Exception:
            pass
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat-history', methods=['GET'])
@login_required
def get_chat_history():
    """Return chat messages for the logged-in user"""
    try:
        rows = list(chat_messages_collection.find({
            'user_id': ObjectId(session['user_id'])
        }).sort('created_at', 1).limit(100))
        
        messages = [{
            'id': str(r['_id']),
            'role': r['role'],
            'message': r['message'],
            'created_at': r['created_at'].isoformat() if isinstance(r['created_at'], datetime) else str(r['created_at'])
        } for r in rows]
        
        return jsonify({'messages': messages})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/save-chat', methods=['POST'])
@login_required
def save_chat_message():
    """Save a chat message for the logged-in user"""
    try:
        data = request.get_json()
        role = data.get('role')
        message = data.get('message', '').strip()
        
        if not role or not message:
            return jsonify({'error': 'role and message are required'}), 400
        
        chat_messages_collection.insert_one({
            'user_id': ObjectId(session['user_id']),
            'role': role,
            'message': message,
            'created_at': datetime.now()
        })
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear-chat', methods=['POST'])
@login_required
def clear_chat():
    """Clear all chat messages for the logged-in user"""
    try:
        chat_messages_collection.delete_many({'user_id': ObjectId(session['user_id'])})
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-report', methods=['POST'])
@login_required
def generate_report():
    """Generate and return PDF report"""
    try:
        data = request.get_json()
        bmi_record_id = data.get('bmi_record_id')
        report_id = data.get('report_id')
        
        # Get user data
        user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
        user_data = {'username': user['username'], 'email': user['email']}
        
        bmi_data = None
        analysis_data = None
        
        # Get BMI record if provided
        if bmi_record_id:
            record = bmi_records_collection.find_one({
                '_id': ObjectId(bmi_record_id),
                'user_id': ObjectId(session['user_id'])
            })
            if record:
                bmi_data = {
                    'name': record['name'],
                    'age': record['age'],
                    'sex': record['sex'],
                    'height': record['height'],
                    'weight': record['weight'],
                    'bmi': record['bmi'],
                    'category': record['category']
                }
        
        # Get analyzed report if provided
        if report_id:
            analysis = analyzed_reports_collection.find_one({
                '_id': ObjectId(report_id),
                'user_id': ObjectId(session['user_id'])
            })
            if analysis:
                analysis_data = {
                    'overview': analysis.get('overview', ''),
                    'suggestions': analysis.get('suggestions', ''),
                    'report_type': analysis.get('report_type', '')
                }
        
        # Generate PDF
        pdf_buffer = generate_bmi_pdf(user_data, bmi_data, analysis_data)
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'bmi_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        )
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/send-report-email', methods=['POST'])
@login_required
def send_report_email():
    """Send PDF report via email"""
    try:
        data = request.get_json()
        bmi_record_id = data.get('bmi_record_id')
        report_id = data.get('report_id')
        recipient_email = data.get('email', '').strip()
        
        if not recipient_email:
            return jsonify({'error': 'Email address required'}), 400
        
        # Get user data
        user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
        user_data = {'username': user['username'], 'email': user['email']}
        
        bmi_data = None
        analysis_data = None
        
        # Get BMI record if provided
        if bmi_record_id:
            record = bmi_records_collection.find_one({
                '_id': ObjectId(bmi_record_id),
                'user_id': ObjectId(session['user_id'])
            })
            if record:
                bmi_data = {
                    'name': record['name'],
                    'age': record['age'],
                    'sex': record['sex'],
                    'height': record['height'],
                    'weight': record['weight'],
                    'bmi': record['bmi'],
                    'category': record['category']
                }
        
        # Get analyzed report if provided
        if report_id:
            analysis = analyzed_reports_collection.find_one({
                '_id': ObjectId(report_id),
                'user_id': ObjectId(session['user_id'])
            })
            if analysis:
                analysis_data = {
                    'overview': analysis.get('overview', ''),
                    'suggestions': analysis.get('suggestions', ''),
                    'report_type': analysis.get('report_type', '')
                }
        
        # Generate PDF
        pdf_buffer = generate_bmi_pdf(user_data, bmi_data, analysis_data)
        
        # Create HTML email content
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; background: #f5f5f5;">
                <div style="max-width: 600px; margin: 20px auto; padding: 30px; background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <h2 style="color: #FF6B9D; text-align: center;">📊 Your Upgraded Lifestyle Reports</h2>
                    <hr style="border: none; border-top: 2px solid #FF6B9D; margin: 20px 0;">
                    
                    <p style="font-size: 16px;">Hello {user_data.get('username', 'User')},</p>
                    <p style="font-size: 14px; color: #666;">Your health report has been generated. Please find it attached.</p>
                    
                    <p style="margin-top: 20px;">Report includes:</p>
                    <ul>
                        <li>BMI Analysis and History</li>
                        <li>Health Insights and Recommendations</li>
                        <li>Personalized Suggestions</li>
                    </ul>
                    
                    <hr style="border: none; border-top: 2px solid #FF6B9D; margin: 20px 0;">
                    
                    <p style="font-size: 14px; color: #666; margin-top: 20px;">
                        Stay healthy and keep tracking your wellness journey with Upgraded Lifestyle!
                    </p>
                    
                    <p style="font-size: 12px; color: #999; margin-top: 30px;">
                        Best regards,<br>
                        <strong style="color: #FF6B9D;">Upgraded Lifestyle Team</strong>
                    </p>
                    
                    <p style="font-size: 11px; color: #ccc; text-align: center; margin-top: 20px;">
                        © 2025 Upgraded Lifestyle | All Rights Reserved
                    </p>
                </div>
            </body>
        </html>
        """
        
        # Send email with PDF attachment
        try:
            msg = MIMEMultipart()
            msg['From'] = os.getenv('SMTP_USER')
            msg['To'] = recipient_email
            msg['Subject'] = 'Your Upgraded Lifestyle Health Report'
            
            msg.attach(MIMEText(html_content, 'html'))
            
            # Attach PDF
            pdf_attachment = MIMEBase('application', 'octet-stream')
            pdf_buffer.seek(0)
            pdf_attachment.set_payload(pdf_buffer.read())
            encoders.encode_base64(pdf_attachment)
            pdf_attachment.add_header(
                'Content-Disposition',
                f'attachment; filename=health_report_{datetime.now().strftime("%Y%m%d")}.pdf'
            )
            msg.attach(pdf_attachment)
            
            # Send
            server = smtplib.SMTP(os.getenv('SMTP_SERVER'), int(os.getenv('SMTP_PORT')))
            server.starttls()
            server.login(os.getenv('SMTP_USER'), os.getenv('SMTP_PASSWORD'))
            server.send_message(msg)
            server.quit()
            
            return jsonify({
                'success': True,
                'message': f'Report sent successfully to {recipient_email}'
            })
        except Exception as e:
            print(f"Email sending error: {e}")
            return jsonify({
                'success': False,
                'error': f'Failed to send email: {str(e)}'
            }), 500
            
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/email-reports', methods=['POST'])
@login_required
def email_reports():
    """Send reports via email (backward compatibility endpoint)"""
    try:
        data = request.get_json()
        recipient_email = data.get('email', '').strip()
        reports_to_send = data.get('reports', [])
        
        if not recipient_email or not reports_to_send:
            return jsonify({'success': False, 'error': 'Email and reports required'}), 400
        
        # Create HTML email content
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; background: #f5f5f5;">
                <div style="max-width: 600px; margin: 20px auto; padding: 30px; background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <h2 style="color: #FF6B9D; text-align: center;">📊 Your Upgraded Lifestyle Reports</h2>
                    <hr style="border: none; border-top: 2px solid #FF6B9D; margin: 20px 0;">
                    
                    <p style="font-size: 16px;">Hello,</p>
                    <p style="font-size: 14px; color: #666;">Here are your selected wellness reports:</p>
                    
                    <ul style="list-style: none; padding: 0; margin: 20px 0;">
        """
        
        for report in reports_to_send:
            html_content += f"""
                        <li style="padding: 12px; background: #f9f9f9; margin: 10px 0; border-left: 4px solid #FF6B9D; border-radius: 4px;">
                            ✓ {report}
                        </li>
            """
        
        html_content += """
                    </ul>
                    
                    <hr style="border: none; border-top: 2px solid #FF6B9D; margin: 20px 0;">
                    
                    <p style="font-size: 14px; color: #666; margin-top: 20px;">
                        Stay healthy and keep tracking your wellness journey with Upgraded Lifestyle!
                    </p>
                    
                    <p style="font-size: 12px; color: #999; margin-top: 30px;">
                        Best regards,<br>
                        <strong style="color: #FF6B9D;">Upgraded Lifestyle Team</strong>
                    </p>
                    
                    <p style="font-size: 11px; color: #ccc; text-align: center; margin-top: 20px;">
                        © 2025 Upgraded Lifestyle | All Rights Reserved
                    </p>
                </div>
            </body>
        </html>
        """
        
        # Send email
        if send_email(recipient_email, 'Your Upgraded Lifestyle Reports', html_content):
            return jsonify({
                'success': True,
                'message': f'Reports sent successfully to {recipient_email}'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to send email. Please check your email settings.'
            }), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/progress-insights', methods=['GET'])
@login_required
def get_progress_insights():
    """Get unique progress insights and trends"""
    try:
        records = list(bmi_records_collection.find({
            'user_id': ObjectId(session['user_id'])
        }).sort('created_at', -1).limit(10))
        
        insights = {
            'total_records': len(records),
            'latest_bmi': records[0]['bmi'] if records else None,
            'trend': 'stable'
        }
        
        if len(records) >= 2:
            latest_bmi = records[0]['bmi']
            previous_bmi = records[1]['bmi']
            if latest_bmi > previous_bmi:
                insights['trend'] = 'increasing'
            elif latest_bmi < previous_bmi:
                insights['trend'] = 'decreasing'
        
        return jsonify({'insights': insights})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-routine', methods=['POST'])
@login_required
def generate_routine():
    """Generate personalized exercise routine based on BMI and preferences"""
    try:
        data = request.get_json()
        activities = data.get('activities', [])
        bmi = data.get('bmi')
        goal = data.get('goal')
        activity_level = data.get('activity_level')
        
        if not activities:
            return jsonify({'error': 'Please select at least one activity'}), 400
        
        # Ask Aurora AI for routine
        if model:
            prompt = f"""Generate a personalized weekly exercise routine for someone with:
- BMI: {bmi}
- Goal: {goal}
- Activity Level: {activity_level}
- Preferred activities: {', '.join(activities)}
The routine should include:
1. Weekly schedule with specific activities
2. Duration and intensity for each activity
3. Rest periods
4. Safety precautions
5. Progress tracking tips"""
            
            response = model.generate_content(prompt)
            return jsonify({
                'success': True,
                'routine': response.text
            })
        
        return jsonify({'error': 'AI model not available'}), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-diet', methods=['POST'])
@login_required
def generate_diet():
    """Generate personalized diet plan based on BMI and preferences"""
    try:
        data = request.get_json()
        bmi = data.get('bmi')
        goal = data.get('goal')
        diet_type = data.get('diet_type')
        allergies = data.get('allergies', '')
        
        if not diet_type:
            return jsonify({'error': 'Please select a diet type'}), 400
        
        # Ask Aurora AI for diet plan
        if model:
            prompt = f"""Generate a personalized diet plan for someone with:
- BMI: {bmi}
- Goal: {goal}
- Diet Type: {diet_type}
- Allergies/Restrictions: {allergies}
The plan should include:
1. Daily calorie target
2. Macronutrient distribution
3. Sample meal plan
4. Foods to avoid
5. Recommended supplements
6. Meal timing suggestions"""
            
            response = model.generate_content(prompt)
            return jsonify({
                'success': True,
                'diet_plan': response.text
            })
        
        return jsonify({'error': 'AI model not available'}), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai-bmi-suggestions', methods=['POST'])
@login_required
def ai_bmi_suggestions():
    """Get AI-powered BMI suggestions"""
    try:
        data = request.get_json()
        bmi = data.get('bmi')
        category = data.get('category')
        goal = data.get('goal', 'maintain')
        activity_level = data.get('activity_level', 'moderate')
        
        if not model:
            return jsonify({'error': 'AI model not available'}), 500
        
        try:
            prompt = f"""As Aurora, provide personalized health suggestions for someone with:
            - BMI: {bmi}
            - Category: {category}
            - Health Goal: {goal}
            - Activity Level: {activity_level}
            Format your response like this:
            1. Initial Assessment
            2. Diet Recommendations:
               - Specific foods to include/avoid
               - Meal timing suggestions
               - Calorie guidance (if appropriate)
               
            3. Exercise Plan:
               - Types of exercises suited for their BMI and activity level
               - Frequency recommendations
               - Safety precautions
               
            4. Lifestyle Adjustments:
               - Sleep recommendations
               - Stress management
               - Daily habits to build
               
            5. Progress Tracking:
               - How to measure success
               - When to adjust the plan
               - Warning signs to watch for
            
            Keep your tone encouraging and supportive. Focus on sustainable, healthy changes rather than quick fixes."""
            
            response = model.generate_content(prompt)
            suggestions = response.text.strip()
            
            if suggestions.startswith("Aurora:"):
                suggestions = suggestions[7:].strip()
            
            return jsonify({
                'success': True,
                'suggestions': suggestions
            })
        except Exception as e:
            print(f"Gemini API error: {e}")
            
            fallback_suggestions = f"""Based on your BMI of {bmi} in the {category} category:
1. Initial Assessment:
   Your BMI indicates {category.lower()} status. Let's focus on gradual, sustainable changes.
2. Diet Recommendations:
   - Maintain a balanced diet with whole foods
   - Stay hydrated with plenty of water
   - Consider consulting a nutritionist for personalized advice
3. Exercise Plan:
   - Start with activities you enjoy
   - Begin gradually and increase intensity over time
   - Listen to your body and rest when needed
4. Lifestyle Adjustments:
   - Aim for 7-8 hours of quality sleep
   - Practice stress management
   - Build healthy daily routines
5. Progress Tracking:
   - Monitor your BMI regularly
   - Keep a food and exercise journal
   - Celebrate small victories
Remember, health is a journey, not a destination. I'm here to support you!"""
            
            return jsonify({
                'success': True,
                'suggestions': fallback_suggestions
            })
        
    except Exception as e:
        print(f"Route error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health-insights', methods=['GET'])
@login_required
def health_insights():
    """Get health insights from BMI data"""
    try:
        user_id = ObjectId(session['user_id'])
        latest_bmi = bmi_records_collection.find_one(
            {'user_id': user_id},
            sort=[('created_at', -1)]
        )
        
        if not latest_bmi:
            return jsonify({'insights': 'No BMI data available yet. Start by calculating your BMI!'}), 200
        
        bmi = latest_bmi['bmi']
        category = latest_bmi['category']
        
        insights_map = {
            'Underweight': 'You are underweight. Focus on nutritious meals and strength training to build healthy weight.',
            'Normal': 'Great job! You maintain a healthy weight. Continue with regular exercise and balanced diet.',
            'Overweight': 'Consider increasing physical activity and reviewing your diet. Consult a healthcare professional for personalized advice.',
            'Obese': 'Your health may be at risk. Seek guidance from a healthcare provider for a safe weight management plan.'
        }
        
        return jsonify({
            'category': category,
            'bmi': bmi,
            'insights': insights_map.get(category, 'Consult a healthcare professional for personalized advice.'),
            'recommendations': [
                '🏃 Exercise 30 minutes daily',
                '🥗 Eat balanced, nutritious meals',
                '💧 Drink plenty of water',
                '😴 Get 7-8 hours of sleep',
                '📊 Track your progress'
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=False, port=int(os.getenv('PORT', 5000)), host='0.0.0.0')
