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
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
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

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf'}

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
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        vision_model = genai.GenerativeModel('models/gemini-2.5-flash')
        print("✓ Gemini API initialized with gemini-2.5-flash")
    except Exception as e:
        print(f"✗ Gemini API error: {e}")

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
            return jsonify({'success': False, 'error': 'All fields required'}), 400
        
        if len(username) < 3:
            return jsonify({'success': False, 'error': 'Username must be at least 3 characters'}), 400
        
        if len(password) < 6:
            return jsonify({'success': False, 'error': 'Password must be at least 6 characters'}), 400
        
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
            return jsonify({'success': False, 'error': 'Username and password required'}), 400
        
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
            return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/logout', methods=['POST'])
def logout():
    """User logout endpoint"""
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    """Check if user is authenticated"""
    if 'user_id' in session:
        return jsonify({'authenticated': True, 'username': session.get('username')})
    return jsonify({'authenticated': False})

@app.route('/api/calculate-bmi', methods=['POST'])
@login_required
def calculate_bmi():
    """Calculate BMI and save record"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        age = int(data.get('age', 0))
        sex = data.get('sex', '').strip()
        height = float(data.get('height', 0))
        weight = float(data.get('weight', 0))
        
        if not all([name, age, sex, height, weight]):
            return jsonify({'error': 'All fields required'}), 400
        
        if not (13 <= age <= 120):
            return jsonify({'error': 'Age must be between 13 and 120'}), 400
        if not (100 <= height <= 300):
            return jsonify({'error': 'Height must be between 100-300 cm'}), 400
        if not (20 <= weight <= 500):
            return jsonify({'error': 'Weight must be between 20-500 kg'}), 400
        
        height_m = height / 100
        bmi = round(weight / (height_m ** 2), 1)
        category = get_bmi_category(bmi)
        icon = get_bmi_icon(category)
        
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
        return jsonify({'error': 'Invalid input values'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bmi-history', methods=['GET'])
@login_required
def bmi_history():
    """Get user's BMI history"""
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
        
        return jsonify({'records': history, 'total': len(history)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/aurora-chat', methods=['POST'])
@login_required
def aurora_chat():
    """Aurora AI Chat endpoint"""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'error': 'Message required'}), 400
        
        chat_messages_collection.insert_one({
            'user_id': ObjectId(session['user_id']),
            'role': 'user',
            'message': message,
            'created_at': datetime.now()
        })
        
        if model:
            try:
                developer_info = """
IMPORTANT: About the developer/owner:
- Developer: Vignesh
- SIMATS Engineering Student
- Capstone Project: Upgraded Lifestyle BMI & Wellness Web Application
- GitHub: Vixcy300
"""
                
                message_lower = message.lower()
                is_about_developer = any(word in message_lower for word in ['developer', 'owner', 'created', 'vignesh', 'creator', 'who made'])
                
                if is_about_developer:
                    prompt = f"""{developer_info}
User: {message}
Aurora:"""
                else:
                    prompt = f"""You are Aurora, a friendly AI wellness assistant. Provide helpful, concise advice about BMI, health, fitness, nutrition, and lifestyle. Keep responses to 2-3 sentences max.
User: {message}
Aurora:"""
                
                response = model.generate_content(prompt)
                ai_response = response.text.strip()
                
                if ai_response.startswith("Aurora:"):
                    ai_response = ai_response[7:].strip()
                
                chat_messages_collection.insert_one({
                    'user_id': ObjectId(session['user_id']),
                    'role': 'bot',
                    'message': ai_response,
                    'created_at': datetime.now()
                })
                
                return jsonify({'response': ai_response, 'success': True})
            except Exception as e:
                print(f"Gemini error: {e}")
        
        fallback = "I'm here to help! Ask me about BMI, nutrition, fitness, or wellness."
        chat_messages_collection.insert_one({
            'user_id': ObjectId(session['user_id']),
            'role': 'bot',
            'message': fallback,
            'created_at': datetime.now()
        })
        
        return jsonify({'response': fallback, 'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat-history', methods=['GET'])
@login_required
def get_chat_history():
    """Get user's chat history"""
    try:
        messages = list(chat_messages_collection.find({
            'user_id': ObjectId(session['user_id'])
        }).sort('created_at', 1).limit(100))
        
        result = [{
            'id': str(m['_id']),
            'role': m['role'],
            'message': m['message'],
            'created_at': m['created_at'].isoformat() if isinstance(m['created_at'], datetime) else str(m['created_at'])
        } for m in messages]
        
        return jsonify({'messages': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear-chat', methods=['POST'])
@login_required
def clear_chat():
    """Clear user's chat history"""
    try:
        chat_messages_collection.delete_many({'user_id': ObjectId(session['user_id'])})
        return jsonify({'success': True, 'message': 'Chat history cleared'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze-image', methods=['POST'])
@login_required
def analyze_image():
    """Analyze uploaded image with Gemini Vision"""
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            return jsonify({'error': 'Invalid image format'}), 400
        
        # Read and encode image
        image_data = file.read()
        
        if vision_model:
            try:
                # Use Gemini Vision API
                response = vision_model.generate_content([
                    "Analyze this image and provide insights about health, nutrition, or wellness. Keep response concise.",
                    {"mime_type": file.content_type, "data": base64.standard_b64encode(image_data).decode()}
                ])
                
                analysis = response.text.strip()
                
                # Save analysis
                analyzed_reports_collection.insert_one({
                    'user_id': ObjectId(session['user_id']),
                    'analysis': analysis,
                    'filename': secure_filename(file.filename),
                    'created_at': datetime.now()
                })
                
                return jsonify({'analysis': analysis, 'success': True})
            except Exception as e:
                print(f"Vision API error: {e}")
                return jsonify({'error': 'Image analysis failed'}), 500
        
        return jsonify({'error': 'Vision API not available'}), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/email-reports', methods=['POST'])
@login_required
def email_reports():
    """Send reports via email"""
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
