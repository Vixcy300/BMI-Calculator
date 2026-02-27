"""
Upgraded Lifestyle - BMI & Wellness Web Application
Backend Flask server with MongoDB database and Google Gemini AI integration
"""
import os
import hashlib
import base64
import smtplib
from appwrite.client import Client as AppwriteClient
from appwrite.services.databases import Databases
from appwrite.id import ID
from appwrite.query import Query
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from io import BytesIO
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
# from pymongo import MongoClient
# from pymongo.errors import DuplicateKeyError
import google.generativeai as genai
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from PIL import Image

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'webp'}

# Session configuration
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600

# Create uploads directory
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Enable CORS
CORS(app, supports_credentials=True, resources={
    r"/*": {
        "origins": ["http://localhost:5000", "http://127.0.0.1:5000"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

# Appwrite Connection
APPWRITE_ENDPOINT = os.getenv("APPWRITE_ENDPOINT")
APPWRITE_PROJECT_ID = os.getenv("APPWRITE_PROJECT_ID")
APPWRITE_API_KEY = os.getenv("APPWRITE_API_KEY")
APPWRITE_WATER_COLLECTION_ID = os.getenv("APPWRITE_WATER_COLLECTION_ID")

if not all([APPWRITE_ENDPOINT, APPWRITE_PROJECT_ID, APPWRITE_API_KEY]):
    raise ValueError("Appwrite credentials not found in environment variables")

client = AppwriteClient()
client.set_endpoint(APPWRITE_ENDPOINT)
client.set_project(APPWRITE_PROJECT_ID)
client.set_key(APPWRITE_API_KEY)

databases = Databases(client)

# Appwrite IDs
DATABASE_ID = os.getenv("APPWRITE_DATABASE_ID", "default")
USERS_COLLECTION_ID = os.getenv("APPWRITE_USERS_COLLECTION_ID", "users")
BMI_RECORDS_COLLECTION_ID = os.getenv("APPWRITE_BMI_RECORDS_COLLECTION_ID", "bmi_records")
REPORTS_COLLECTION_ID = os.getenv("APPWRITE_REPORTS_COLLECTION_ID", "analyzed_reports")
MESSAGES_COLLECTION_ID = os.getenv("APPWRITE_MESSAGES_COLLECTION_ID", "chat_messages")
GOALS_COLLECTION_ID = os.getenv("APPWRITE_GOALS_COLLECTION_ID", "user_goals")

# Use Appwrite collections instead of local SQLite/Supabase

# Configure Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
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
    except Exception as e:
        print(f"✗ Gemini API configuration error: {e}")
        model = None
else:
    print("⚠ Warning: GEMINI_API_KEY not found in .env file")
    model = None

# Initialize Vision model
if GEMINI_API_KEY:
    try:
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
    except:
        vision_model = None
else:
    vision_model = None

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
    """Determine BMI category based on BMI value"""
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

# Routes
@app.route('/')
def index():
    """Render main index page"""
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    """User registration endpoint"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        
        # Validation
        if not username or not email or not password:
            return jsonify({'success': False, 'error': 'All fields are required'}), 400
        
        if len(username) < 3:
            return jsonify({'success': False, 'error': 'Username must be at least 3 characters'}), 400
        
        if len(password) < 6:
            return jsonify({'success': False, 'error': 'Password must be at least 6 characters'}), 400
        
        if '@' not in email:
            return jsonify({'success': False, 'error': 'Invalid email format'}), 400
        
        # Hash password
        hashed_password = hash_password(password)
        
        try:
            # Create a unique ID for the user
            user_id = ID.unique()
            
            # Insert into Appwrite
            response = databases.create_document(
                database_id=DATABASE_ID,
                collection_id=USERS_COLLECTION_ID,
                document_id=user_id,
                data={
                    'username': username,
                    'email': email,
                    'password': hashed_password,
                    'created_at': datetime.now().isoformat()
                }
            )
            
            # Create session
            session['user_id'] = user_id
            session['username'] = username
            
            return jsonify({'success': True, 'message': 'Registration successful'})
            
        except Exception as e:
            # Handle potential duplicate keys or other errors
            import traceback
            traceback.print_exc()
            error_msg = str(e)
            if "duplicate" in error_msg.lower() or "exists" in error_msg.lower():
                return jsonify({'success': False, 'error': 'Username or email already exists'}), 400
            return jsonify({'success': False, 'error': error_msg}), 500
            
    except Exception as e:
        import traceback
        traceback.print_exc()
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
        
        # Hash password
        hashed_password = hash_password(password)
        
        # Find user in Appwrite
        response = databases.list_documents(
            database_id=DATABASE_ID,
            collection_id=USERS_COLLECTION_ID,
            queries=[
                Query.equal("username", username),
                Query.equal("password", hashed_password)
            ]
        )
        
        if response['total'] > 0:
            user = response['documents'][0]
            # Set session variables
            session.permanent = True
            session['user_id'] = user['$id']
            session['username'] = user['username']
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': {
                    'id': user['$id'],
                    'username': user['username']
                }
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
        response = databases.get_document(
            database_id=DATABASE_ID,
            collection_id=USERS_COLLECTION_ID,
            document_id=session['user_id']
        )
        
        return jsonify({
            'username': response['username'],
            'email': response['email']
        })
        
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
        
        # Save to Appwrite
        response = databases.create_document(
            database_id=DATABASE_ID,
            collection_id=BMI_RECORDS_COLLECTION_ID,
            document_id=ID.unique(),
            data={
                'user_id': session['user_id'],
                'name': name,
                'age': age,
                'sex': sex,
                'height': height,
                'weight': weight,
                'bmi': bmi,
                'category': category,
                'created_at': datetime.now().isoformat()
            }
        )
        
        record_id = response['$id']
        
        return jsonify({
            'bmi': bmi,
            'category': category,
            'icon': icon,
            'saved': True,
            'record_id': record_id
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
        response = databases.list_documents(
            database_id=DATABASE_ID,
            collection_id=BMI_RECORDS_COLLECTION_ID,
            queries=[
                Query.equal("user_id", session['user_id']),
                Query.order_desc("created_at")
            ]
        )
        
        history = []
        for record in response['documents']:
            history.append({
                'id': record['$id'],
                'name': record['name'],
                'age': record['age'],
                'sex': record['sex'],
                'height': record['height'],
                'weight': record['weight'],
                'bmi': record['bmi'],
                'category': record['category'],
                'created_at': record['created_at']
            })
        
        return jsonify({'records': history})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete-record/<record_id>', methods=['DELETE'])
@login_required
def delete_record(record_id):
    """Delete a specific BMI record"""
    try:
        # Verify ownership before deleting
        record = databases.get_document(
            database_id=DATABASE_ID,
            collection_id=BMI_RECORDS_COLLECTION_ID,
            document_id=record_id
        )
        if record['user_id'] != session['user_id']:
            return jsonify({'error': 'Unauthorized'}), 401
        
        databases.delete_document(
            database_id=DATABASE_ID,
            collection_id=BMI_RECORDS_COLLECTION_ID,
            document_id=record_id
        )
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
        
        # Save user message to Appwrite
        databases.create_document(
            database_id=DATABASE_ID,
            collection_id=MESSAGES_COLLECTION_ID,
            document_id=ID.unique(),
            data={
                'user_id': session['user_id'],
                'role': 'user',
                'message': message,
                'created_at': datetime.now().isoformat()
            }
        )
        
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
                
                message_lower = message.lower()
                is_about_developer = any(word in message_lower for word in ['developer', 'owner', 'created', 'made', 'who made', 'who created', 'vignesh', 'creator', 'author'])
                
                if is_about_developer:
                    prompt = f"""You are Aurora, a friendly AI wellness assistant. {developer_info}
User: {message}
Aurora:"""
                else:
                    prompt = f"""You are Aurora, a friendly and helpful AI wellness assistant. You provide helpful, encouraging advice about BMI, health, fitness, nutrition, and wellness.

**FORMATTING RULES (VERY IMPORTANT):**
- Use **bold** for key terms
- Use bullet points (•) for lists
- Keep paragraphs SHORT (2-3 sentences max)
- Use line breaks between sections
- Add relevant emoji icons
- Never write walls of text

User: {message}
Aurora:"""
                
                response = model.generate_content(prompt)
                ai_response = response.text.strip()
                
                if ai_response.startswith("Aurora:"):
                    ai_response = ai_response[7:].strip()
                
                print(f"✓ Gemini API response received: {ai_response[:100]}...")
                
                # Save bot response to Appwrite (truncate to fit)
                databases.create_document(
                    database_id=DATABASE_ID,
                    collection_id=MESSAGES_COLLECTION_ID,
                    document_id=ID.unique(),
                    data={
                        'user_id': session['user_id'],
                        'role': 'bot',
                        'message': ai_response[:4900],
                        'created_at': datetime.now().isoformat()
                    }
                )
                
                return jsonify({
                    'response': ai_response,
                    'success': True
                })
            except Exception as e:
                import traceback
                print(f"✗ Gemini API error: {type(e).__name__}: {e}")
                traceback.print_exc()
        
        # Fallback responses
        import random
        fallback_responses = [
            "I'm here to help you with your wellness journey! Feel free to ask me about BMI, nutrition, or fitness.",
            "That's a great question! For personalized advice, consider consulting with a healthcare professional.",
            "Remember, maintaining a balanced diet and regular exercise are key to a healthy lifestyle!",
            "Every body is unique! Focus on overall wellness rather than just numbers.",
            "I'm currently having trouble connecting, but I'm here to support your health goals!"
        ]
        
        fallback = random.choice(fallback_responses)
        
        # Save fallback response to Appwrite
        databases.create_document(
            database_id=DATABASE_ID,
            collection_id=MESSAGES_COLLECTION_ID,
            document_id=ID.unique(),
            data={
                'user_id': session['user_id'],
                'role': 'bot',
                'message': fallback,
                'created_at': datetime.now().isoformat()
            }
        )
        
        return jsonify({
            'response': fallback,
            'success': True
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/api/analyze-image', methods=['POST'])
@login_required
def analyze_image():
    """Analyze uploaded image with Gemini Vision API"""
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
            analysis_prompt = """Analyze this BMI report or health-related document image. Format your response in clean, readable Markdown:

## Overview
A brief summary of what you see in this report

## Key Findings
- Important numbers, values, or data points (use bullet points)

## Analysis
What these findings mean (keep it concise)

## Suggestions
- Actionable health recommendations (use bullet points)

## Report Type
What kind of report this appears to be

Keep each section short and scannable. Use emoji where helpful."""
            
            response = vision_model.generate_content([analysis_prompt, img])
            
            try:
                analysis_text = response.text.strip()
            except ValueError:
                # If the response doesn't contain valid text (e.g. blocked by safety filters)
                return jsonify({'error': 'Image analysis was blocked or returned empty. Please try a different, clearer image.'}), 400
            
            
            import re
            
            # Extract sections from analysis using regex to handle markdown variations
            overview = ""
            suggestions = ""
            report_type = "Unknown"
            
            overview_match = re.search(r'##?\s*Overview\n(.*?)(?=##|\Z)', analysis_text, re.DOTALL | re.IGNORECASE)
            if overview_match:
                overview = overview_match.group(1).strip()
                
            suggestions_match = re.search(r'##?\s*Suggestions\n(.*?)(?=##|\Z)', analysis_text, re.DOTALL | re.IGNORECASE)
            if suggestions_match:
                suggestions = suggestions_match.group(1).strip()[:1000]
                
            type_match = re.search(r'##?\s*Report Type\n(.*?)(?=##|\Z)', analysis_text, re.DOTALL | re.IGNORECASE)
            if type_match:
                report_type = type_match.group(1).strip().split('\n')[0][:250]
                
            if not overview:
                overview = analysis_text[:500] + "..."
            
            # Truncate fields to fit Appwrite string limits
            analysis_text = analysis_text[:4900] if analysis_text else ''
            suggestions = suggestions[:4900] if suggestions else ''
            overview = overview[:4900] if overview else ''
            report_type = report_type[:250] if report_type else 'Unknown'
            
            # Save analysis to Appwrite
            response = databases.create_document(
                database_id=DATABASE_ID,
                collection_id=REPORTS_COLLECTION_ID,
                document_id=ID.unique(),
                data={
                    'user_id': session['user_id'],
                    'image_filename': filename[:250],
                    'analysis_text': analysis_text,
                    'suggestions': suggestions,
                    'overview': overview,
                    'report_type': report_type,
                    'created_at': datetime.now().isoformat()
                }
            )
            
            report_id = response['$id']
            
            return jsonify({
                'success': True,
                'report_id': str(report_id),
                'analysis': analysis_text,
                'overview': overview,
                'suggestions': suggestions,
                'report_type': report_type,
                'filename': filename
            })
            
        except Exception as e:
            print(f"Vision analysis error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Image analysis failed: {str(e)}'}), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyzed-reports', methods=['GET'])
@login_required
def get_analyzed_reports():
    """Get all analyzed reports for user"""
    try:
        response = databases.list_documents(
            database_id=DATABASE_ID,
            collection_id=REPORTS_COLLECTION_ID,
            queries=[
                Query.equal("user_id", session['user_id']),
                Query.order_desc("created_at")
            ]
        )
        
        result = []
        for report in response['documents']:
            result.append({
                'id': report['$id'],
                'image_filename': report['image_filename'],
                'analysis': report['analysis_text'],
                'suggestions': report['suggestions'],
                'overview': report['overview'],
                'report_type': report['report_type'],
                'created_at': report['created_at']
            })
        
        return jsonify({'reports': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyzed-reports/<report_id>', methods=['DELETE'])
@login_required
def delete_analyzed_report(report_id):
    """Delete a specific analyzed report"""
    try:
        # Check if report exists and belongs to user
        report = databases.get_document(
            database_id=DATABASE_ID,
            collection_id=REPORTS_COLLECTION_ID,
            document_id=report_id
        )
        
        if report['user_id'] != session['user_id']:
            return jsonify({'error': 'Unauthorized'}), 401
            
        # Delete database record
        databases.delete_document(
            database_id=DATABASE_ID,
            collection_id=REPORTS_COLLECTION_ID,
            document_id=report_id
        )
        
        # Attempt to delete uploaded file
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
        response = databases.list_documents(
            database_id=DATABASE_ID,
            collection_id=MESSAGES_COLLECTION_ID,
            queries=[
                Query.equal("user_id", session['user_id']),
                Query.order_asc("created_at")
            ]
        )
        
        messages = []
        for msg in response['documents']:
            messages.append({
                'id': msg['$id'],
                'role': msg['role'],
                'message': msg['message'],
                'created_at': msg['created_at']
            })
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
        
        databases.create_document(
            database_id=DATABASE_ID,
            collection_id=MESSAGES_COLLECTION_ID,
            document_id=ID.unique(),
            data={
                'user_id': session['user_id'],
                'role': role,
                'message': message,
                'created_at': datetime.now().isoformat()
            }
        )
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear-chat', methods=['POST'])
@login_required
def clear_chat():
    """Clear all chat messages for the logged-in user"""
    try:
        # Appwrite doesn't have delete_many, so we list and delete
        response = databases.list_documents(
            database_id=DATABASE_ID,
            collection_id=MESSAGES_COLLECTION_ID,
            queries=[Query.equal("user_id", session['user_id'])]
        )
        for doc in response['documents']:
            databases.delete_document(
                database_id=DATABASE_ID,
                collection_id=MESSAGES_COLLECTION_ID,
                document_id=doc['$id']
            )
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
    
    # AI Analysis
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
        diet_text = analysis_data.get('diet') if isinstance(analysis_data, dict) else None
        if routine_text:
            story.append(Paragraph("<b>Personalized Exercise Routine</b>", styles['Heading3']))
            story.append(Spacer(1, 6))
            story.append(Paragraph(routine_text, styles['Normal']))
            story.append(Spacer(1, 10))
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

@app.route('/api/generate-report', methods=['POST'])
@login_required
def generate_report():
    """Generate and return PDF report"""
    try:
        data = request.get_json()
        bmi_record_id = data.get('bmi_record_id')
        report_id = data.get('report_id')
        
        # Get user data
        user = databases.get_document(
            database_id=DATABASE_ID,
            collection_id=USERS_COLLECTION_ID,
            document_id=session['user_id']
        )
        
        user_data = {'username': user['username'], 'email': user['email']}
        bmi_data = None
        analysis_data = None
        
        if bmi_record_id:
            try:
                record = databases.get_document(
                    database_id=DATABASE_ID,
                    collection_id=BMI_RECORDS_COLLECTION_ID,
                    document_id=bmi_record_id
                )
                if record['user_id'] == session['user_id']:
                    bmi_data = {
                        'name': record['name'],
                        'age': record['age'],
                        'sex': record['sex'],
                        'height': record['height'],
                        'weight': record['weight'],
                        'bmi': record['bmi'],
                        'category': record['category']
                    }
            except Exception as e:
                print(f"Error fetching BMI record for PDF: {e}")
                pass
        
        # Get analyzed report if provided
        if report_id:
            try:
                analysis = databases.get_document(
                    database_id=DATABASE_ID,
                    collection_id=REPORTS_COLLECTION_ID,
                    document_id=report_id
                )
                if analysis['user_id'] == session['user_id']:
                    analysis_data = {
                        'overview': analysis.get('overview', ''),
                        'suggestions': analysis.get('suggestions', ''),
                        'report_type': analysis.get('report_type', 'Unknown Report')
                    }
            except Exception as e:
                print(f"Error fetching Report for PDF: {e}")
                pass
        
        # Generate PDF
        pdf_buffer = generate_bmi_pdf(user_data, bmi_data, analysis_data)
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'bmi_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        )
        
    except Exception as e:
        import traceback
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
        
        # Get user email
        user = databases.get_document(
            database_id=DATABASE_ID,
            collection_id=USERS_COLLECTION_ID,
            document_id=session['user_id']
        )
        
        user_email = user['email']
        username = user['username']
        
        user_data = {'username': username, 'email': user_email}
        bmi_data = None
        analysis_data = None
        
        # Get data
        if bmi_record_id:
            try:
                record = databases.get_document(
                    database_id=DATABASE_ID,
                    collection_id=BMI_RECORDS_COLLECTION_ID,
                    document_id=bmi_record_id
                )
                if record['user_id'] == session['user_id']:
                    bmi_data = {
                        'name': record['name'],
                        'age': record['age'],
                        'sex': record['sex'],
                        'height': record['height'],
                        'weight': record['weight'],
                        'bmi': record['bmi'],
                        'category': record['category']
                    }
            except:
                pass
        
        if report_id:
            try:
                analysis = databases.get_document(
                    database_id=DATABASE_ID,
                    collection_id=REPORTS_COLLECTION_ID,
                    document_id=report_id
                )
                if analysis['user_id'] == session['user_id']:
                    analysis_data = {
                        'overview': analysis.get('overview', ''),
                        'suggestions': analysis.get('suggestions', ''),
                        'report_type': analysis.get('report_type', 'Unknown Report')
                    }
            except Exception as e:
                print(f"Error fetching analysis for email: {e}")
                pass
        
        # Generate PDF
        pdf_buffer = generate_bmi_pdf(user_data, bmi_data, analysis_data)
        
        # Send email via Gmail SMTP
        email_user = os.getenv('EMAIL_USER')
        email_pass = os.getenv('EMAIL_PASS')
        
        if not email_user or not email_pass:
            return jsonify({'error': 'Email credentials not configured on server'}), 500
        
        msg = MIMEMultipart()
        msg['From'] = email_user
        msg['To'] = user_email
        msg['Subject'] = f'Your BMI Health Report - Upgraded Lifestyle'
        
        body = f"""Hi {username},\n\nPlease find your personalized BMI Health Report attached.\n\nGenerated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}\n\nStay healthy!\n- Upgraded Lifestyle Team"""
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach PDF
        pdf_attachment = MIMEBase('application', 'octet-stream')
        pdf_attachment.set_payload(pdf_buffer.read())
        encoders.encode_base64(pdf_attachment)
        pdf_attachment.add_header(
            'Content-Disposition',
            f'attachment; filename=BMI_Report_{datetime.now().strftime("%Y%m%d")}.pdf'
        )
        msg.attach(pdf_attachment)
        
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(email_user, email_pass)
            server.send_message(msg)
        
        return jsonify({
            'success': True,
            'message': f'Report sent successfully to {user_email}!'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/progress-insights', methods=['GET'])
@login_required
def get_progress_insights():
    """Get unique progress insights and trends"""
    try:
        response = databases.list_documents(
            database_id=DATABASE_ID,
            collection_id=BMI_RECORDS_COLLECTION_ID,
            queries=[
                Query.equal("user_id", session['user_id']),
                Query.order_desc("created_at"),
                Query.limit(10)
            ]
        )
        
        records = response['documents']
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
    """Generate personalized exercise routine"""
    try:
        data = request.get_json()
        activities = data.get('activities', [])
        bmi = data.get('bmi')
        goal = data.get('goal')
        activity_level = data.get('activity_level')
        
        if not activities:
            return jsonify({'error': 'Please select at least one activity'}), 400
        
        if model:
            prompt = f"""Generate a personalized weekly exercise routine for someone with:
- BMI: {bmi}
- Goal: {goal}
- Activity Level: {activity_level}
- Preferred activities: {', '.join(activities)}

**FORMAT YOUR RESPONSE EXACTLY LIKE THIS (use Markdown):**

## 📅 Weekly Exercise Schedule

### Monday - [Focus Area]
• **Exercise Name** — Duration, Intensity
• **Exercise Name** — Duration, Intensity

### Tuesday - [Focus Area]
• **Exercise Name** — Duration, Intensity

(Continue for each day...)

### 🚨 Sunday - Active Rest
• Light stretching or yoga

---

## ⚠️ Safety Tips
• Tip 1
• Tip 2

## 📊 Progress Tracking
• How to measure success
• When to increase intensity

Keep it concise, actionable, and encouraging. Use emoji icons."""
            
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
    """Generate personalized diet plan"""
    try:
        data = request.get_json()
        bmi = data.get('bmi')
        goal = data.get('goal')
        diet_type = data.get('diet_type')
        allergies = data.get('allergies', '')
        
        if not diet_type:
            return jsonify({'error': 'Please select a diet type'}), 400
        
        if model:
            prompt = f"""Generate a personalized diet plan for someone with:
- BMI: {bmi}
- Goal: {goal}
- Diet Type: {diet_type}
- Allergies/Restrictions: {allergies}

**FORMAT YOUR RESPONSE EXACTLY LIKE THIS (use Markdown):**

## 🍽 Daily Nutrition Plan

### 🎯 Daily Targets
| Nutrient | Amount |
|---|---|
| Calories | X kcal |
| Protein | X g |
| Carbs | X g |
| Fat | X g |

### 🌅 Breakfast (X AM)
• **Meal option 1** — Brief description
• **Meal option 2** — Brief description

### 🌞 Lunch (X PM)
• **Meal option 1** — Brief description

### 🌙 Dinner (X PM)
• **Meal option 1** — Brief description

### 🍎 Snacks
• Snack options

---

## ❌ Foods to Avoid
• Item 1
• Item 2

## 💊 Recommended Supplements
• Supplement + reason

Keep it concise and actionable. Use emoji icons."""
            
            response = model.generate_content(prompt)
            return jsonify({
                'success': True,
                'diet_plan': response.text
            })
        
        return jsonify({'error': 'AI model not available'}), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Page routes
# ==========================================
# Water Intake Tracker Routes
# ==========================================

@app.route('/api/water-logs', methods=['GET'])
@login_required
def get_water_logs():
    try:
        # Get today's date string (YYYY-MM-DD format)
        today = datetime.now().strftime('%Y-%m-%d')
        
        response = databases.list_documents(
            database_id=DATABASE_ID,
            collection_id=APPWRITE_WATER_COLLECTION_ID,
            queries=[
                Query.equal('user_id', session['user_id']),
                Query.equal('date', today)
            ]
        )
        
        # Calculate total
        total_ml = sum(doc['amount_ml'] for doc in response['documents'])
        
        return jsonify({
            'success': True,
            'total_ml': total_ml,
            'logs': response['documents']
        })
    except Exception as e:
        print(f"Error fetching water logs: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/water-logs', methods=['POST'])
@login_required
def add_water_log():
    try:
        data = request.json
        amount = int(data.get('amount_ml', 0))
        
        if amount <= 0:
            return jsonify({'error': 'Invalid amount'}), 400
            
        today = datetime.now().strftime('%Y-%m-%d')
        
        response = databases.create_document(
            database_id=DATABASE_ID,
            collection_id=APPWRITE_WATER_COLLECTION_ID,
            document_id=ID.unique(),
            data={
                'user_id': session['user_id'],
                'amount_ml': amount,
                'date': today,
                'created_at': datetime.now().isoformat()
            }
        )
        
        return jsonify({'success': True, 'log': response})
    except Exception as e:
        print(f"Error saving water log: {e}")
        return jsonify({'error': str(e)}), 500

# ==========================================
# Page Routes
# ==========================================

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/bmi-calculator')
@login_required
def bmi_calculator():
    return render_template('bmi_calculator.html')

@app.route('/health-insights')
@login_required
def health_insights():
    return render_template('health_insights.html')

@app.route('/photo-analysis')
@login_required
def photo_analysis():
    return render_template('photo_analysis.html')

@app.route('/reports')
@login_required
def reports():
    return render_template('reports.html')

@app.route('/routines')
@login_required
def routines():
    return render_template('routines.html')

@app.route('/api/ai-bmi-suggestions', methods=['POST'])
@login_required
def ai_bmi_suggestions():
    """Get AI-generated BMI suggestions"""
    try:
        data = request.get_json()
        bmi = data.get('bmi')
        category = data.get('category')
        goal = data.get('goal', 'maintain')
        activity_level = data.get('activity_level', 'moderate')
        
        if not model:
            return jsonify({'error': 'AI model not available'}), 500
        
        try:
            prompt = f"""As Aurora, provide a brief, friendly, and actionable personalized health suggestion for someone with:
- BMI: {bmi} ({category})
- Health Goal: {goal}
- Activity Level: {activity_level}

Keep your response conversational and VERY SHORT (max 3-4 sentences total). Do not provide a long list or comprehensive plan. Just 1 or 2 specific pieces of advice or encouragement based on their profile. Use emojis where helpful."""
            
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
            
            fallback_suggestions = f"""You're doing great with a BMI of {bmi} ({category.lower()})! Focus on sustainable, gradual changes that fit your lifestyle. Maintain a balanced diet, stay hydrated, and try to get a bit of movement every day. Remember, consistency is the key to reaching your goals! 😊"""
            
            return jsonify({
                'success': True,
                'suggestions': fallback_suggestions
            })
        
    except Exception as e:
        print(f"Route error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/save-routine', methods=['POST'])
@login_required
def save_routine():
    """Save user's health goals and routine"""
    try:
        data = request.get_json()
        goal_type = data.get('goal_type')
        activities = data.get('activities', [])
        target_weight = data.get('target_weight')
        
        databases.create_document(
            database_id=DATABASE_ID,
            collection_id=GOALS_COLLECTION_ID,
            document_id=ID.unique(),
            data={
                'user_id': session['user_id'],
                'goal_type': goal_type,
                'target_value': float(target_weight) if target_weight else 0.0,
                'status': 'active',
                'activities': ','.join(activities) if isinstance(activities, list) else str(activities),
                'created_at': datetime.now().isoformat()
            }
        )
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/email-report', methods=['POST'])
@login_required
def email_report():
    """Send report via email with SMTP"""
    try:
        data = request.get_json()
        report_type = data.get('report_type')
        email = data.get('email')
        
        # Configure email settings
        email_user = os.getenv('EMAIL_USER')
        email_pass = os.getenv('EMAIL_PASS')
        
        if not email_user or not email_pass:
            return jsonify({
                'success': False,
                'error': 'Email credentials not configured on server.'
            }), 500
        
        # Generate PDF
        pdf_buffer = generate_bmi_pdf(
            user_data={'username': session.get('username')},
            bmi_data=data.get('bmi_data'),
            analysis_data=data.get('analysis_data')
        )
        
        # Create email
        msg = MIMEMultipart()
        msg['From'] = email_user
        msg['To'] = email
        msg['Subject'] = f'Your {report_type} Report from Upgraded Lifestyle'
        
        body = f"Please find your requested {report_type} report attached.\n\nStay healthy!\n- Upgraded Lifestyle"
        msg.attach(MIMEText(body, 'plain'))
        
        # Add PDF attachment
        pdf_attachment = MIMEBase('application', 'octet-stream')
        pdf_attachment.set_payload(pdf_buffer.read())
        encoders.encode_base64(pdf_attachment)
        pdf_attachment.add_header(
            'Content-Disposition',
            f'attachment; filename=report_{datetime.now().strftime("%Y%m%d")}.pdf'
        )
        msg.attach(pdf_attachment)
        
        # Send email via Gmail SMTP
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(email_user, email_pass)
            server.send_message(msg)
        
        return jsonify({'success': True, 'message': f'Report sent to {email}!'})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0', ssl_context=None)
