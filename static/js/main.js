/**
 * Upgraded Lifestyle - Main JavaScript
 * Handles authentication, BMI calculator, Aurora chat, and history management
 */

// ========================================
// Global Variables
// ========================================
const API_BASE = '';

// ========================================
// Utility Functions
// ========================================

/**
 * Escape HTML to prevent XSS attacks
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Validate email format
 */
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

/**
 * Show error message
 */
function showError(elementId, message) {
    const errorElement = document.getElementById(elementId);
    if (errorElement) {
        errorElement.textContent = message;
        errorElement.style.display = 'block';
    }
}

/**
 * Clear error message
 */
function clearError(elementId) {
    const errorElement = document.getElementById(elementId);
    if (errorElement) {
        errorElement.textContent = '';
        errorElement.style.display = 'none';
    }
}

/**
 * Show success notification (optional enhancement)
 */
function showSuccess(message) {
    // Simple alert for now, can be enhanced with toast notifications
    console.log('Success:', message);
}

/**
 * Format date string nicely
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// ========================================
// Dark Mode Toggle
// ========================================

function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-mode');
        updateDarkModeButtons(true);
    }
}

function toggleDarkMode() {
    document.body.classList.toggle('dark-mode');
    const isDark = document.body.classList.contains('dark-mode');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    updateDarkModeButtons(isDark);
}

function updateDarkModeButtons(isDark) {
    const icon = isDark ? '☀️' : '🌙';
    const btn1 = document.getElementById('darkModeBtn1');
    const btn2 = document.getElementById('darkModeBtn2');
    if (btn1) btn1.textContent = icon;
    if (btn2) btn2.textContent = icon;
}

initTheme();

// ========================================
// Authentication Functions
// ========================================

/**
 * Open auth modal and switch to specified tab
 */
function openAuth(tab = 'login') {
    const modal = document.getElementById('authModal');
    if (modal) {
        modal.style.display = 'flex';
        switchAuthTab(tab);
    }
}

/**
 * Close auth modal
 */
function closeAuth() {
    const modal = document.getElementById('authModal');
    if (modal) {
        modal.style.display = 'none';
        // Clear forms
        document.getElementById('loginForm').reset();
        document.getElementById('signupForm').reset();
        clearError('loginError');
        clearError('signupError');
    }
}

/**
 * Switch between login and signup tabs
 */
function switchAuthTab(tab) {
    const loginTab = document.getElementById('loginTab');
    const signupTab = document.getElementById('signupTab');
    const loginForm = document.getElementById('loginForm');
    const signupForm = document.getElementById('signupForm');

    if (tab === 'login') {
        loginTab.classList.add('active');
        signupTab.classList.remove('active');
        loginForm.style.display = 'flex';
        signupForm.style.display = 'none';
        clearError('loginError');
        clearError('signupError');
    } else {
        signupTab.classList.add('active');
        loginTab.classList.remove('active');
        signupForm.style.display = 'flex';
        loginForm.style.display = 'none';
        clearError('loginError');
        clearError('signupError');
    }
}

/**
 * Handle login form submission
 */
async function handleLogin(event) {
    event.preventDefault();
    clearError('loginError');

    const username = document.getElementById('loginUsername').value.trim();
    const password = document.getElementById('loginPassword').value.trim();

    if (!username || !password) {
        showError('loginError', 'Please fill in all fields');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (data.success) {
            closeAuth();
            await checkAuth();
        } else {
            showError('loginError', data.error || 'Login failed. Please try again.');
        }
    } catch (error) {
        console.error('Login error:', error);
        showError('loginError', 'Network error. Please try again.');
    }
}

/**
 * Handle signup form submission
 */
async function handleSignup(event) {
    event.preventDefault();
    clearError('signupError');

    const username = document.getElementById('signupUsername').value.trim();
    const email = document.getElementById('signupEmail').value.trim();
    const password = document.getElementById('signupPassword').value.trim();

    // Validation
    if (!username || !email || !password) {
        showError('signupError', 'Please fill in all fields');
        return;
    }

    if (username.length < 3) {
        showError('signupError', 'Username must be at least 3 characters');
        return;
    }

    if (password.length < 6) {
        showError('signupError', 'Password must be at least 6 characters');
        return;
    }

    if (!validateEmail(email)) {
        showError('signupError', 'Please enter a valid email address');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, email, password })
        });

        const data = await response.json();

        if (data.success) {
            closeAuth();
            await checkAuth();
        } else {
            showError('signupError', data.error || 'Registration failed. Please try again.');
        }
    } catch (error) {
        console.error('Signup error:', error);
        showError('signupError', 'Network error. Please try again.');
    }
}

/**
 * Handle logout
 */
async function logout() {
    try {
        const response = await fetch(`${API_BASE}/logout`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include'
        });

        const data = await response.json();
        if (data.success) {
            showLanding();
        }
    } catch (error) {
        console.error('Logout error:', error);
        // Still show landing page on error
        showLanding();
    }
}

// ========================================
// Dashboard Functions
// ========================================

/**
 * Check if user is authenticated on page load
 */
async function checkAuth() {
    try {
        const response = await fetch(`${API_BASE}/api/check-auth`, { credentials: 'include' });
        const data = await response.json();

        if (data.authenticated) {
            showDashboard();
            await initDashboard();
        } else {
            showLanding();
        }
    } catch (error) {
        console.error('Auth check error:', error);
        showLanding();
    }
}

/**
 * Show dashboard and hide landing page
 */
function showDashboard() {
    const landingPage = document.getElementById('landingPage');
    const dashboardPage = document.getElementById('dashboardPage');

    if (landingPage) landingPage.style.display = 'none';
    if (dashboardPage) dashboardPage.style.display = 'block';
}

/**
 * Show landing page and hide dashboard
 */
function showLanding() {
    const landingPage = document.getElementById('landingPage');
    const dashboardPage = document.getElementById('dashboardPage');

    if (landingPage) landingPage.style.display = 'block';
    if (dashboardPage) dashboardPage.style.display = 'none';

    // Reset chat UI for new/anonymous users
    resetChatToWelcome();
}

/**
 * Initialize dashboard with user data
 */
async function initDashboard() {
    try {
        // Load user profile
        const profileResponse = await fetch(`${API_BASE}/api/user-profile`, { credentials: 'include' });
        if (profileResponse.ok) {
            const profileData = await profileResponse.json();
            document.getElementById('profileUsername').textContent = profileData.username || '';
            document.getElementById('profileEmail').textContent = profileData.email || '';
            document.getElementById('usernameDisplay').textContent = profileData.username || 'User';
        }

        // Load BMI history
        await loadBMIHistory();
    } catch (error) {
        console.error('Dashboard init error:', error);
    }
}

// ========================================
// BMI Calculator Functions
// ========================================

/**
 * Handle BMI form submission
 */
async function handleBMISubmit(event) {
    event.preventDefault();

    const name = document.getElementById('bmiName').value.trim();
    const age = parseInt(document.getElementById('bmiAge').value);
    const sex = document.getElementById('bmiSex').value;
    const height = parseFloat(document.getElementById('bmiHeight').value);
    const weight = parseFloat(document.getElementById('bmiWeight').value);

    // Validation
    if (!name || !age || !sex || !height || !weight) {
        alert('Please fill in all fields');
        return;
    }

    if (age < 13 || age > 120) {
        alert('Age must be between 13 and 120');
        return;
    }

    if (height < 100 || height > 300) {
        alert('Height must be between 100 and 300 cm');
        return;
    }

    if (weight < 20 || weight > 500) {
        alert('Weight must be between 20 and 500 kg');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/calculate-bmi`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({ name, age, sex, height, weight })
        });

        const data = await response.json();

        if (data.error) {
            alert(data.error);
        } else {
            displayBMIResult(data);
            resetBMIForm();
            // Refresh history
            await loadBMIHistory();
        }
    } catch (error) {
        console.error('BMI calculation error:', error);
        alert('Error calculating BMI. Please try again.');
    }
}

/**
 * Display BMI calculation result
 */
function displayBMIResult(data) {
    const resultCard = document.getElementById('resultCard');
    const bmiIcon = document.getElementById('bmiIcon');
    const bmiValue = document.getElementById('bmiValue');
    const bmiCategory = document.getElementById('bmiCategory');
    const bmiAdvice = document.getElementById('bmiAdvice');

    if (resultCard) {
        bmiIcon.textContent = data.icon || '📊';
        bmiValue.textContent = data.bmi || '0';
        bmiCategory.textContent = data.category || 'Normal';

        // Health advice based on category
        const advice = getBMIAdvice(data.category);
        bmiAdvice.textContent = advice;

        // Update SVG color based on category
        const silhouette = document.querySelector('.human-silhouette');
        if (silhouette) {
            silhouette.classList.remove('silhouette-underweight', 'silhouette-normal', 'silhouette-overweight', 'silhouette-obese');
            const categoryClass = 'silhouette-' + data.category.toLowerCase();
            silhouette.classList.add(categoryClass);
        }

        resultCard.style.display = 'block';

        // Smooth scroll to result
        resultCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

/**
 * Get health advice based on BMI category
 */
function getBMIAdvice(category) {
    const adviceMap = {
        'Underweight': 'Consider consulting with a healthcare provider to develop a healthy weight gain plan. Focus on nutrient-dense foods and strength training.',
        'Normal': 'Great job! Your BMI is within the healthy range. Maintain a balanced diet and regular exercise to stay healthy.',
        'Overweight': 'Consider incorporating more physical activity and making dietary adjustments. Small, sustainable changes can make a big difference.',
        'Obese': 'It\'s important to consult with healthcare professionals to develop a personalized weight management plan. Focus on gradual, sustainable changes.'
    };
    return adviceMap[category] || 'Maintain a healthy lifestyle with balanced nutrition and regular exercise.';
}

/**
 * Reset BMI form
 */
function resetBMIForm() {
    document.getElementById('bmiForm').reset();
}

// ========================================
// Aurora Chat Functions
// ========================================

/**
 * Send message to Aurora AI
 */
async function sendMessage() {
    const chatInput = document.getElementById('chatInput');
    const message = chatInput.value.trim();

    if (!message) return;

    // Display user message
    displayUserMessage(message);
    // Save user message for logged-in users (best-effort)
    try {
        await saveChatMessage('user', message);
    } catch (e) {
        // ignore save errors
    }
    chatInput.value = '';

    // Disable input while waiting
    chatInput.disabled = true;
    const sendButton = document.getElementById('sendButton');
    if (sendButton) sendButton.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/api/aurora-chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({ message })
        });

        const data = await response.json();

        if (data.response) {
            displayAuroraMessage(data.response);
            try {
                await saveChatMessage('bot', data.response);
            } catch (e) {
                // ignore
            }
        } else {
            displayAuroraMessage('I apologize, but I\'m having trouble responding right now. Please try again later.');
        }
    } catch (error) {
        console.error('Chat error:', error);
        displayAuroraMessage('Sorry, I encountered an error. Please try again.');
    } finally {
        // Re-enable input
        chatInput.disabled = false;
        if (sendButton) sendButton.disabled = false;
        chatInput.focus();
    }
}

// Save a chat message to backend (best-effort). Returns promise.
async function saveChatMessage(role, message) {
    try {
        await fetch(`${API_BASE}/api/save-chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ role, message })
        });
    } catch (e) {
        // Ignore errors (non-logged-in users will get 401)
        // console.warn('saveChatMessage failed', e);
    }
}

// Reset chat to default welcome message
function resetChatToWelcome() {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;
    chatMessages.innerHTML = `
        <div class="message bot-message">
            <div class="message-content">
                Hello! I'm Aurora, your wellness assistant. Ask me anything about BMI, health, fitness, nutrition, or wellness! 😊<br><br>
                <strong>New:</strong> You can now upload BMI report images above and I'll analyze them for you!
            </div>
        </div>
    `;
}

// Load chat history for logged-in user and display it. If none, show welcome.
async function loadChatHistory() {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;
    try {
        const response = await fetch(`${API_BASE}/api/chat-history`, { credentials: 'include' });
        if (!response.ok) {
            resetChatToWelcome();
            return;
        }
        const data = await response.json();
        if (!data.messages || data.messages.length === 0) {
            resetChatToWelcome();
            return;
        }

        // Render messages
        chatMessages.innerHTML = '';
        data.messages.forEach(m => {
            const div = document.createElement('div');
            div.className = m.role === 'user' ? 'message user-message' : 'message bot-message';
            const content = m.role === 'user' ? escapeHtml(m.message) : formatBotMessage(m.message);
            div.innerHTML = `<div class="message-content">${content}</div>`;
            chatMessages.appendChild(div);
        });
        scrollToBottom();
    } catch (e) {
        console.error('Load chat history error:', e);
        resetChatToWelcome();
    }
}

function formatBotMessage(text) {
    if (typeof marked !== 'undefined' && typeof DOMPurify !== 'undefined') {
        return DOMPurify.sanitize(marked.parse(text));
    }
    return escapeHtml(text).replace(/\n/g, '<br>');
}

/**
 * Display user message in chat
 */
function displayUserMessage(text) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;

    const messageDiv = document.createElement('div');
    messageDiv.className = 'message user-message';
    messageDiv.innerHTML = `
        <div class="message-content">${escapeHtml(text)}</div>
    `;

    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

/**
 * Display Aurora AI message in chat
 */
function displayAuroraMessage(text) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;

    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot-message';
    messageDiv.innerHTML = `
        <div class="message-content">${formatBotMessage(text)}</div>
    `;

    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

/**
 * Auto-scroll chat to bottom
 */
function scrollToBottom() {
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

// ========================================
// History Management Functions
// ========================================

/**
 * Load BMI history from API
 */
async function loadBMIHistory() {
    try {
        const response = await fetch(`${API_BASE}/api/bmi-history`, { credentials: 'include' });
        const data = await response.json();

        if (data.records) {
            displayHistory(data.records);
        }
    } catch (error) {
        console.error('History load error:', error);
    }
}

/**
 * Display BMI history in table
 */
function displayHistory(records) {
    const historyBody = document.getElementById('historyBody');
    if (!historyBody) return;

    if (records.length === 0) {
        historyBody.innerHTML = `
            <tr>
                <td colspan="8" class="empty-state">No records yet. Calculate your BMI to get started!</td>
            </tr>
        `;
        return;
    }

    historyBody.innerHTML = records.map(record => {
        const icon = getBMIIcon(record.category);
        return `
            <tr>
                <td>${formatDate(record.created_at)}</td>
                <td>${escapeHtml(record.name)}</td>
                <td>${record.age}</td>
                <td>${record.height} cm</td>
                <td>${record.weight} kg</td>
                <td>${record.bmi}</td>
                <td>${icon} ${escapeHtml(record.category)}</td>
                <td>
                    <button class="btn btn-danger" onclick="deleteRecord(${record.id})">
                        Delete
                    </button>
                </td>
            </tr>
        `;
    }).join('');

    // Update Chart
    renderBMIChart(records);
}

// Global variable for chart instance
let bmiChartInstance = null;

/**
 * Render or update the BMI history chart
 */
function renderBMIChart(records) {
    if (typeof Chart === 'undefined') return;

    const chartContainer = document.getElementById('bmiChartContainer');
    const ctx = document.getElementById('bmiChart');
    if (!ctx || !chartContainer) return;

    if (records.length < 2) {
        chartContainer.style.display = 'none';
        return;
    }

    chartContainer.style.display = 'block';

    // Sort chronologically for the chart (oldest to newest)
    const sortedRecords = [...records].reverse();
    const labels = sortedRecords.map(r => new Date(r.created_at).toLocaleDateString([], { month: 'short', day: 'numeric' }));
    const dataPoints = sortedRecords.map(r => r.bmi);

    const data = {
        labels: labels,
        datasets: [{
            label: 'BMI Trend',
            data: dataPoints,
            borderColor: '#ff6b9d',
            backgroundColor: 'rgba(255, 107, 157, 0.2)',
            borderWidth: 3,
            fill: true,
            tension: 0.4,
            pointBackgroundColor: '#ff8e53',
            pointRadius: 5,
            pointHoverRadius: 7
        }]
    };

    const config = {
        type: 'line',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            return `BMI: ${context.parsed.y}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    suggestedMin: Math.min(...dataPoints) - 2,
                    suggestedMax: Math.max(...dataPoints) + 2
                }
            }
        }
    };

    if (bmiChartInstance) {
        bmiChartInstance.destroy();
    }

    bmiChartInstance = new Chart(ctx, config);
}

/**
 * Get icon for BMI category
 */
function getBMIIcon(category) {
    const icons = {
        'Underweight': '💪',
        'Normal': '✅',
        'Overweight': '⚠️',
        'Obese': '🔴'
    };
    return icons[category] || '📊';
}

/**
 * Delete a BMI record
 */
async function deleteRecord(id) {
    if (!confirm('Are you sure you want to delete this record?')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/delete-record/${id}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
            , credentials: 'include'
        });

        const data = await response.json();

        if (data.success) {
            await loadBMIHistory();
        } else {
            alert('Failed to delete record. Please try again.');
        }
    } catch (error) {
        console.error('Delete error:', error);
        alert('Error deleting record. Please try again.');
    }
}

// ========================================
// Event Listeners
// ========================================

// Wait for DOM to load
document.addEventListener('DOMContentLoaded', function () {
    // Check authentication on page load
    checkAuth();

    // Chat input Enter key
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }

    // Close modal on Escape key
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            const modal = document.getElementById('authModal');
            if (modal && modal.style.display !== 'none') {
                closeAuth();
            }
        }
    });

    // Close modal when clicking outside
    const modal = document.getElementById('authModal');
    if (modal) {
        modal.addEventListener('click', function (e) {
            if (e.target === modal || e.target.classList.contains('modal-overlay')) {
                closeAuth();
            }
        });
    }

    // Tooltip behavior for info icons (mobile-friendly)
    document.querySelectorAll('.info-icon').forEach(btn => {
        btn.addEventListener('click', function (e) {
            e.stopPropagation();
            // Toggle the next tooltip sibling
            const tooltip = btn.parentElement.querySelector('.tooltip');
            if (!tooltip) return;
            tooltip.classList.toggle('show');
            // Close others
            document.querySelectorAll('.tooltip').forEach(t => {
                if (t !== tooltip) t.classList.remove('show');
            });
        });
    });

    // Close tooltips when tapping/clicking elsewhere
    document.addEventListener('click', function () {
        document.querySelectorAll('.tooltip').forEach(t => t.classList.remove('show'));
    });
});

// ========================================
// Aurora Advice Functions
// ========================================

async function askAuroraAdvice() {
    const bmiValue = document.getElementById('bmiValue')?.textContent;
    const bmiCategory = document.getElementById('bmiCategory')?.textContent;
    const goal = document.getElementById('bmiGoal')?.value;
    const activity = document.getElementById('bmiActivity')?.value;

    if (!bmiValue || !bmiCategory) {
        alert('Please calculate your BMI first.');
        return;
    }

    try {
        // First, show a loading message in chat
        displayAuroraMessage("Analyzing your BMI and preparing personalized suggestions...");

        const response = await fetch(`${API_BASE}/api/ai-bmi-suggestions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                bmi: bmiValue,
                category: bmiCategory,
                goal: goal,
                activity_level: activity
            })
        });

        if (!response.ok) {
            throw new Error('Failed to get AI suggestions');
        }

        const data = await response.json();

        if (data.success) {
            // Add Aurora's response to chat
            displayAuroraMessage(
                `Based on your profile:\n` +
                `• BMI: ${bmiValue} (${bmiCategory})\n` +
                `• Goal: ${goal || 'Not specified'}\n` +
                `• Activity Level: ${activity || 'Not specified'}\n\n` +
                `Here are my suggestions:\n\n${data.suggestions}`
            );

            // Scroll to chat section
            document.getElementById('chatSection').scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        } else {
            throw new Error(data.error || 'Failed to get suggestions');
        }
    } catch (error) {
        console.error('AI suggestions error:', error);
        displayAuroraMessage("I apologize, but I'm having trouble generating suggestions right now. Please try again or contact support if the issue persists.");
    }
}

// ========================================
// Animation on Page Load (optional GSAP)
// ========================================

window.addEventListener('load', function () {
    // Animate hero elements if GSAP is loaded
    if (typeof gsap !== 'undefined') {
        const heroTitle = document.querySelector('.hero-title');
        const heroSubtitle = document.querySelector('.hero-subtitle');
        const heroButton = document.querySelector('.hero .btn');

        if (heroTitle) {
            gsap.from(heroTitle, {
                duration: 1,
                opacity: 0,
                y: 30,
                ease: 'power3.out'
            });
        }

        if (heroSubtitle) {
            gsap.from(heroSubtitle, {
                duration: 1,
                opacity: 0,
                y: 30,
                delay: 0.2,
                ease: 'power3.out'
            });
        }

        if (heroButton) {
            gsap.from(heroButton, {
                duration: 1,
                opacity: 0,
                y: 30,
                delay: 0.4,
                ease: 'power3.out'
            });
        }
    }
});


// ========================================
// Image Upload & Analysis Functions (UNIQUE FEATURES)
// ========================================

let uploadedImageFile = null;

function handleImageUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    // Verify file type
    const fileType = file.type.toLowerCase();
    const allowedTypes = ['image/png', 'image/jpg', 'image/jpeg', 'image/gif', 'image/webp'];
    if (!allowedTypes.includes(fileType)) {
        alert('Please select a valid image file (PNG, JPG, JPEG, GIF, WEBP)');
        return;
    }

    // Verify file size (16MB max)
    const maxSize = 16 * 1024 * 1024; // 16MB in bytes
    if (file.size > maxSize) {
        alert('File is too large. Maximum size is 16MB');
        return;
    }

    // Save file for upload
    uploadedImageFile = file;

    // Show preview
    const reader = new FileReader();
    reader.onload = function (e) {
        document.getElementById('previewImg').src = e.target.result;
        document.getElementById('imagePreview').style.display = 'block';
        document.getElementById('uploadArea').style.display = 'none';
        document.getElementById('analyzeBtn').style.display = 'block';
    };
    reader.onerror = function () {
        alert('Error reading file. Please try again.');
    };
    reader.readAsDataURL(file);
}

function handleChatImageUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    analyzeImageInChat(file);
}

async function analyzeUploadedImage() {
    if (!uploadedImageFile) {
        alert('Please select an image first');
        return;
    }

    const analyzeBtn = document.getElementById('analyzeBtn');
    analyzeBtn.disabled = true;
    analyzeBtn.textContent = 'Analyzing...';

    try {
        const formData = new FormData();
        formData.append('image', uploadedImageFile);

        // Make sure to include credentials for session
        const response = await fetch(`${API_BASE}/api/analyze-image`, {
            method: 'POST',
            body: formData,
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.success) {
            displayAnalysisResult(data);
            await loadAnalyzedReports();
        } else {
            throw new Error(data.error || 'Analysis failed');
        }
    } catch (error) {
        console.error('Analysis error:', error);
        alert(error.message || 'Error analyzing image. Please try again.');
    } finally {
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = 'Analyze with AI';
    }
}

async function analyzeImageInChat(file) {
    try {
        displayUserMessage(`📷 Uploaded image: ${file.name}`);
        // Save user message (best-effort)
        try { await saveChatMessage('user', `📷 ${file.name}`); } catch (e) { }

        const formData = new FormData();
        formData.append('image', file);
        const response = await fetch(`${API_BASE}/api/analyze-image`, {
            method: 'POST',
            body: formData,
            credentials: 'include'
        });
        const data = await response.json();
        if (data.success) {
            const botText = `I've analyzed your report! 📋 Type: ${data.report_type}\n\n📊 Overview: ${data.overview}\n\n💡 Suggestions: ${data.suggestions}`;
            displayAuroraMessage(botText);
            try { await saveChatMessage('bot', botText); } catch (e) { }
            await loadAnalyzedReports();
        } else {
            displayAuroraMessage(`Sorry, I had trouble analyzing that image. ${data.error || 'Please try again.'}`);
        }
    } catch (error) {
        console.error('Chat image analysis error:', error);
        displayAuroraMessage('Sorry, I encountered an error analyzing your image.');
    }
}

/**
 * Clear chat for current user (calls backend to delete messages) and reset UI
 */
async function clearChat() {
    const confirmClear = confirm('Are you sure you want to clear your chat history? This cannot be undone.');
    if (!confirmClear) return;

    try {
        const response = await fetch(`${API_BASE}/api/clear-chat`, {
            method: 'POST',
            credentials: 'include'
        });
        const data = await response.json();
        if (response.ok && data.success) {
            resetChatToWelcome();
            alert('Chat history cleared.');
        } else {
            alert(data.error || 'Failed to clear chat.');
        }
    } catch (e) {
        console.error('Clear chat error:', e);
        alert('Error clearing chat. Please try again.');
    }
}

function displayAnalysisResult(data) {
    const resultDiv = document.getElementById('analysisResult');
    resultDiv.innerHTML = `<div class="analysis-card"><h3>📋 Analysis Complete!</h3><p><strong>Report Type:</strong> ${escapeHtml(data.report_type)}</p><div class="analysis-section"><h4>📊 Overview:</h4><p>${escapeHtml(data.overview || 'No overview')}</p></div><div class="analysis-section"><h4>💡 Suggestions:</h4><p>${escapeHtml(data.suggestions || 'No suggestions')}</p></div><div class="analysis-actions"><button class="btn btn-gradient" onclick="generateReportPDF(null, '${data.report_id || data.$id}')">📥 Download PDF</button></div></div>`;
    resultDiv.style.display = 'block';
}

async function loadAnalyzedReports() {
    try {
        const response = await fetch(`${API_BASE}/api/analyzed-reports`, { credentials: 'include' });
        const data = await response.json();
        if (data.reports) displayAnalyzedReports(data.reports);
    } catch (error) {
        console.error('Load reports error:', error);
    }
}

function displayAnalyzedReports(reports) {
    const reportsList = document.getElementById('analyzedReportsList');
    if (!reportsList) return;
    if (reports.length === 0) {
        reportsList.innerHTML = '<p class="empty-state">No analyzed reports yet. Upload a BMI report image!</p>';
        return;
    }
    reportsList.innerHTML = reports.map(report => `
        <div class="report-card">
            <div class="report-header">
                <h3>${escapeHtml(report.report_type || 'Report')}</h3>
                <span class="report-date">${formatDate(report.created_at)}</span>
            </div>
            <div class="report-body">
                <p><strong>Overview:</strong> ${escapeHtml(report.overview || (report.analysis || '').substring(0, 200))}</p>
                ${report.suggestions ? `<p><strong>Suggestions:</strong> ${escapeHtml(report.suggestions)}</p>` : ''}
            </div>
            <div class="report-actions">
                <button class="btn btn-primary" onclick="generateReportPDF(null, '${report.$id || report.id}')">📥 Download PDF</button>
                <button class="btn btn-danger" onclick="deleteAnalyzedReport('${report.$id || report.id}')">🗑️ Delete</button>
            </div>
        </div>
    `).join('');
}


/**
 * Delete an analyzed report (with confirmation) and refresh the list
 */
async function deleteAnalyzedReport(reportId) {
    if (!confirm('Are you sure you want to delete this analyzed report? This action cannot be undone.')) return;

    try {
        const response = await fetch(`${API_BASE}/api/analyzed-reports/${reportId}`, {
            method: 'DELETE',
            credentials: 'include'
        });

        const data = await response.json();
        if (response.ok && data.success) {
            await loadAnalyzedReports();
            alert('Report deleted.');
        } else {
            alert(data.error || 'Failed to delete report.');
        }
    } catch (error) {
        console.error('Delete analyzed report error:', error);
        alert('Error deleting report. Please try again.');
    }
}

async function generateReportPDF(bmiRecordId = null, reportId = null) {
    try {
        const response = await fetch(`${API_BASE}/api/generate-report`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ bmi_record_id: bmiRecordId, report_id: reportId })
        });
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `bmi_report_${new Date().getTime()}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } else {
            const data = await response.json();
            alert(data.error || 'Failed to generate PDF');
        }
    } catch (error) {
        console.error('PDF generation error:', error);
        alert('Error generating PDF. Please try again.');
    }
}

async function generateAllReportsPDF() {
    alert('Generating comprehensive report...');
}

async function loadProgressInsights() {
    try {
        const response = await fetch(`${API_BASE}/api/progress-insights`, { credentials: 'include' });
        const data = await response.json();
        if (data.insights) displayInsights(data.insights);
    } catch (error) {
        console.error('Insights load error:', error);
    }
}

function displayInsights(insights) {
    document.getElementById('totalRecords').textContent = insights.total_records || 0;
    document.getElementById('latestBMI').textContent = insights.latest_bmi ? insights.latest_bmi.toFixed(1) : '-';
    const trendEl = document.getElementById('bmiTrend');
    const trend = insights.trend || 'stable';
    if (trend === 'increasing') {
        trendEl.textContent = '📈 Increasing';
        trendEl.style.color = '#ef4444';
    } else if (trend === 'decreasing') {
        trendEl.textContent = '📉 Decreasing';
        trendEl.style.color = '#10b981';
    } else {
        trendEl.textContent = '➡️ Stable';
        trendEl.style.color = '#666';
    }
}

// ========================================
// Routine & Diet Frontend Handlers
// ========================================

function switchRoutineTab(tab) {
    const exercisesTab = document.getElementById('exercisesTab');
    const dietTab = document.getElementById('dietTab');
    const exerciseBtn = document.querySelector(".tab-btn[onclick*='exercises']");
    const dietBtn = document.querySelector(".tab-btn[onclick*='diet']");

    if (tab === 'exercises') {
        if (exercisesTab) exercisesTab.style.display = 'block';
        if (dietTab) dietTab.style.display = 'none';
        if (exerciseBtn) exerciseBtn.classList.add('active');
        if (dietBtn) dietBtn.classList.remove('active');
    } else {
        if (exercisesTab) exercisesTab.style.display = 'none';
        if (dietTab) dietTab.style.display = 'block';
        if (exerciseBtn) exerciseBtn.classList.remove('active');
        if (dietBtn) dietBtn.classList.add('active');
    }
}

async function generateRoutine() {
    const checkboxes = document.querySelectorAll('input[name="exercise"]:checked');
    const activities = Array.from(checkboxes).map(cb => cb.value);
    const routineResult = document.getElementById('routineResult');
    const generateBtn = document.querySelector('#exercisesTab .btn');

    if (activities.length === 0) {
        routineResult.innerHTML = '<p class="error-message">Please select at least one exercise preference.</p>';
        return;
    }

    const bmi = document.getElementById('bmiValue')?.textContent || null;
    const goal = document.getElementById('bmiGoal')?.value || '';
    const activity_level = document.getElementById('bmiActivity')?.value || '';

    // UI feedback
    if (generateBtn) {
        generateBtn.disabled = true;
        generateBtn.textContent = 'Generating...';
    }

    try {
        const response = await fetch(`${API_BASE}/api/generate-routine`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ activities, bmi, goal, activity_level })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            const routineText = data.routine || data.text || data.generated_text || '';
            let formattedHtml = routineText;
            if (typeof marked !== 'undefined' && typeof DOMPurify !== 'undefined') {
                formattedHtml = DOMPurify.sanitize(marked.parse(routineText));
            } else {
                formattedHtml = escapeHtml(routineText).replace(/\n/g, '<br>');
            }
            routineResult.innerHTML = `<div class="markdown-body">${formattedHtml}</div>`;
        } else {
            routineResult.innerHTML = `<p class="error-message">${escapeHtml(data.error || data.message || 'Failed to generate routine')}</p>`;
        }
    } catch (error) {
        console.error('Generate routine error:', error);
        routineResult.innerHTML = `<p class="error-message">Error generating routine. Please try again.</p>`;
    } finally {
        if (generateBtn) {
            generateBtn.disabled = false;
            generateBtn.textContent = 'Generate Routine';
        }
    }
}

async function generateDietPlan() {
    const dietType = document.getElementById('dietType')?.value || '';
    const allergies = document.getElementById('allergies')?.value || '';
    const dietResult = document.getElementById('dietResult');
    const generateBtn = document.querySelector('#dietTab .btn');

    if (!dietType) {
        dietResult.innerHTML = '<p class="error-message">Please select a diet type.</p>';
        return;
    }

    const bmi = document.getElementById('bmiValue')?.textContent || null;
    const goal = document.getElementById('bmiGoal')?.value || '';

    if (generateBtn) {
        generateBtn.disabled = true;
        generateBtn.textContent = 'Generating...';
    }

    try {
        const response = await fetch(`${API_BASE}/api/generate-diet`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ diet_type: dietType, allergies, bmi, goal })
        });

        const data = await response.json();
        if (response.ok && data.success) {
            const dietText = data.diet_plan || data.text || data.generated_text || '';
            let formattedHtml = dietText;
            if (typeof marked !== 'undefined' && typeof DOMPurify !== 'undefined') {
                formattedHtml = DOMPurify.sanitize(marked.parse(dietText));
            } else {
                formattedHtml = escapeHtml(dietText).replace(/\n/g, '<br>');
            }
            dietResult.innerHTML = `<div class="markdown-body">${formattedHtml}</div>`;
        } else {
            dietResult.innerHTML = `<p class="error-message">${escapeHtml(data.error || data.message || 'Failed to generate diet plan')}</p>`;
        }
    } catch (error) {
        console.error('Generate diet error:', error);
        dietResult.innerHTML = `<p class="error-message">Error generating diet plan. Please try again.</p>`;
    } finally {
        if (generateBtn) {
            generateBtn.disabled = false;
            generateBtn.textContent = 'Generate Diet Plan';
        }
    }
}

// Enhanced dashboard initialization
const originalInitDashboard = initDashboard;
initDashboard = async function () {
    await originalInitDashboard();
    await loadProgressInsights();
    await loadAnalyzedReports();
    // Load per-user chat history (if any)
    await loadChatHistory();
    // Load Water Tracker
    await loadWaterLogs();
};

// ========================================
// Email Reports
// ========================================

async function sendEmailReports() {
    const emailInput = document.getElementById('reportEmail');
    const statusEl = document.getElementById('emailStatus');
    const checkboxes = document.querySelectorAll('input[name="reportType"]:checked');
    const reportTypes = Array.from(checkboxes).map(cb => cb.value);

    if (!emailInput) return;
    const email = emailInput.value.trim();
    if (!email) {
        statusEl.innerHTML = '<p class="error-message">Please enter an email address.</p>';
        return;
    }

    if (reportTypes.length === 0) {
        statusEl.innerHTML = '<p class="error-message">Please select at least one report to send.</p>';
        return;
    }

    // UI feedback
    statusEl.innerHTML = '<p>Sending report... please wait.</p>';
    try {
        const response = await fetch(`${API_BASE}/api/send-report-email`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ email: email, report_types: reportTypes })
        });

        const data = await response.json();
        if (response.ok && data.success) {
            statusEl.innerHTML = `<p class="success-message">${escapeHtml(data.message || 'Report sent successfully!')}</p>`;
        } else {
            statusEl.innerHTML = `<p class="error-message">${escapeHtml(data.error || data.message || 'Failed to send report.')}</p>`;
        }
    } catch (error) {
        console.error('Send email reports error:', error);
        statusEl.innerHTML = '<p class="error-message">Error sending report. Please try again later.</p>';
    }
}

// ========================================
// Water Intake Tracker (NEW FEATURE)
// ========================================

const DAILY_WATER_GOAL = 2000; // ml

async function loadWaterLogs() {
    try {
        const response = await fetch(`${API_BASE}/api/water-logs`, { credentials: 'include' });
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                updateWaterUI(data.total_ml);
            }
        }
    } catch (error) {
        console.error('Error loading water logs:', error);
    }
}

function updateWaterUI(currentAmount) {
    const totalEl = document.getElementById('waterTotal');
    const goalEl = document.getElementById('waterGoal');
    const barFill = document.getElementById('waterBarFill');

    if (!totalEl || !barFill) return;

    totalEl.textContent = currentAmount;
    goalEl.textContent = DAILY_WATER_GOAL;

    // Calculate percentage (cap at 100%)
    let percentage = (currentAmount / DAILY_WATER_GOAL) * 100;
    if (percentage > 100) percentage = 100;

    barFill.style.width = `${percentage}%`;

    // Change color if goal reached
    if (percentage >= 100) {
        barFill.style.background = 'linear-gradient(135deg, #2ecc71, #27ae60)';
        barFill.style.boxShadow = '0 0 10px rgba(46, 204, 113, 0.5)';
    } else {
        barFill.style.background = 'linear-gradient(135deg, #3498db, #2980b9)';
        barFill.style.boxShadow = '0 0 10px rgba(52, 152, 219, 0.5)';
    }
}

async function addWater(amount) {
    if (!amount || amount <= 0) return;

    // Optimistic UI update
    const totalEl = document.getElementById('waterTotal');
    const currentTotal = parseInt(totalEl.textContent || 0);
    updateWaterUI(currentTotal + amount);

    try {
        const response = await fetch(`${API_BASE}/api/water-logs`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ amount_ml: amount })
        });

        const data = await response.json();
        if (data.success) {
            // Re-fetch to ensure sync
            await loadWaterLogs();
            displayAuroraMessage(`🌊 Gulp gulp! Logged ${amount}ml of water into your tracker. Keep hydrating!`);
        } else {
            console.error('Failed to log water:', data.error);
            // Revert on failure
            await loadWaterLogs();
            alert('Failed to log water intake.');
        }
    } catch (error) {
        console.error('Error logging water:', error);
        await loadWaterLogs();
        alert('Network error. Failed to log water intake.');
    }
}

function addCustomWater() {
    const input = document.getElementById('customWaterAmount');
    if (!input) return;

    const amount = parseInt(input.value);
    if (isNaN(amount) || amount <= 0) {
        alert('Please enter a valid amount greater than 0.');
        return;
    }

    addWater(amount);
    input.value = ''; // clear input
}

