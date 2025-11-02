# Upgraded Lifestyle - BMI & Wellness Platform

A full-stack web application for calculating BMI, tracking health history, and chatting with an AI wellness assistant. Built as a capstone project for SIMATS Engineering students.

## Features

- **User Authentication**: Secure registration and login system with session management
- **BMI Calculator**: Accurate BMI calculations with personalized health advice
- **Aurora AI Assistant**: Chat with an AI wellness assistant powered by Google Gemini API
- **History Tracking**: View and manage your BMI records over time
- **Modern UI**: Jeton.com-inspired design with pink/orange gradient theme
- **Responsive Design**: Works seamlessly on desktop, tablet, and mobile devices

## Tech Stack

### Backend
- Flask 2.3.3 (Python web framework)
- SQLite3 (Database)
- Google Generative AI (Gemini API)
- Flask-CORS (Cross-origin resource sharing)

### Frontend
- HTML5 (Semantic structure)
- CSS3 (Modern styling with gradients)
- Vanilla JavaScript (ES6+)
- GSAP (Animations)

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd upgraded-lifestyle
   ```

2. **Create a virtual environment**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Linux/Mac
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   
   Create a `.env` file in the root directory:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   FLASK_SECRET_KEY=your_secret_key_here
   ```
   
   **Getting a Gemini API Key:**
   - Visit https://ai.google.dev/
   - Sign in with your Google account
   - Create a new API key
   - Copy and paste it into your `.env` file
   
   **Generating a Flask Secret Key:**
   - You can use any random string (e.g., `openssl rand -hex 32`)
   - Or use an online generator

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the application**
   - Open your browser and navigate to `http://localhost:5000`

## Project Structure

```
upgraded-lifestyle/
├── app.py                 # Flask backend server
├── requirements.txt       # Python dependencies
├── .env                  # Environment variables (not in git)
├── .gitignore           # Git ignore rules
├── README.md            # This file
├── templates/
│   └── index.html       # Main HTML template
└── static/
    ├── css/
    │   └── style.css    # All styles
    └── js/
        └── main.js      # All JavaScript
```

## API Endpoints

### Authentication
- `POST /register` - User registration
- `POST /login` - User login
- `POST /logout` - User logout
- `GET /api/check-auth` - Check authentication status

### User Profile
- `GET /api/user-profile` - Get user profile (requires auth)

### BMI Calculator
- `POST /api/calculate-bmi` - Calculate and save BMI (requires auth)
- `GET /api/bmi-history` - Get all BMI records (requires auth)
- `DELETE /api/delete-record/<id>` - Delete a BMI record (requires auth)

### Aurora Chat
- `POST /api/aurora-chat` - Send message to AI assistant (requires auth)

## Database Schema

### Users Table
- `id` (INTEGER, PRIMARY KEY)
- `username` (TEXT, UNIQUE)
- `email` (TEXT, UNIQUE)
- `password` (TEXT, hashed with SHA256)
- `created_at` (TIMESTAMP)

### BMI Records Table
- `id` (INTEGER, PRIMARY KEY)
- `user_id` (INTEGER, FOREIGN KEY)
- `name` (TEXT)
- `age` (INTEGER)
- `sex` (TEXT)
- `height` (REAL, in cm)
- `weight` (REAL, in kg)
- `bmi` (REAL)
- `category` (TEXT)
- `created_at` (TIMESTAMP)

## Usage Guide

### Registration
1. Click "Sign Up" button on the landing page
2. Enter username, email, and password
3. Click "Sign Up" to create your account

### Calculating BMI
1. Log in to your account
2. Navigate to the BMI Calculator section
3. Fill in your details (name, age, sex, height, weight)
4. Click "Calculate BMI"
5. View your result with personalized health advice

### Using Aurora AI
1. Scroll to the Aurora Chat section
2. Type your question about health, fitness, or nutrition
3. Press Enter or click "Send"
4. Receive AI-powered wellness advice

### Viewing History
1. Navigate to the BMI History section
2. View all your past BMI calculations
3. Delete records by clicking the "Delete" button

## BMI Categories

- **Underweight**: BMI < 18.5
- **Normal**: BMI 18.5 - 24.9
- **Overweight**: BMI 25 - 29.9
- **Obese**: BMI ≥ 30

## Deployment

### Local Development
The app runs on `http://localhost:5000` by default.

### Production (Render.com)
1. Push your code to GitHub
2. Create an account on [Render.com](https://render.com)
3. Create a new Web Service
4. Connect your GitHub repository
5. Set build command: `pip install -r requirements.txt`
6. Set start command: `gunicorn app:app`
7. Add environment variables:
   - `GEMINI_API_KEY`
   - `FLASK_SECRET_KEY`
8. Deploy!

## Security Notes

- Passwords are hashed using SHA256 before storage
- Session-based authentication (no JWT)
- SQL injection protection via parameterized queries
- XSS protection via input sanitization
- CORS enabled for cross-origin requests

## Troubleshooting

### Common Issues

**1. Database errors**
- Delete `upgraded_lifestyle.db` and restart the app (database will be recreated)

**2. Gemini API not working**
- Check that `GEMINI_API_KEY` is set in `.env`
- Verify the API key is valid at https://ai.google.dev/
- The app will use fallback responses if API fails

**3. Module not found errors**
- Ensure virtual environment is activated
- Run `pip install -r requirements.txt` again

**4. Port already in use**
- Change the port in `app.py`: `app.run(debug=True, port=5001)`

## Testing

### Manual Testing Checklist
- [ ] User can register with new account
- [ ] User can log in with credentials
- [ ] BMI calculator works correctly
- [ ] BMI saved to database
- [ ] BMI history displays correctly
- [ ] Delete record works
- [ ] Aurora chat responds
- [ ] Logout works
- [ ] Session persists on refresh
- [ ] Forms validate input
- [ ] Error messages display properly
- [ ] Responsive on mobile devices

### Test Data
- Username: `testuser`
- Email: `test@test.com`
- Password: `test123`
- BMI Test: Height 170cm, Weight 70kg → BMI 24.2 (Normal)

## Contributing

This is a capstone project for SIMATS Engineering students. Contributions and improvements are welcome!

## License

This project is created for educational purposes as part of a capstone project.

## Credits

- Design inspiration: [Jeton.com](https://www.jeton.com/)
- AI Assistant: Google Gemini API
- Framework: Flask (Python)
- Frontend: Vanilla JavaScript, HTML5, CSS3

## Support

For issues or questions, please contact the development team or refer to the project documentation.

---

**Built with ❤️ by SIMATS Engineering Students**

