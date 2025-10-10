# memorycare_app/ui/streamlit_app.py
import requests
import streamlit as st
from datetime import datetime

API = "http://127.0.0.1:8000"

# Page Configuration
st.set_page_config(
    page_title="MemoryCare - AI Companion",
    page_icon="💙",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for Dark Theme
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #312e81 100%);
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .main-header {
        background: rgba(30, 27, 75, 0.8);
        backdrop-filter: blur(10px);
        padding: 1.5rem 2rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(147, 51, 234, 0.3);
    }
    .header-title {
        background: linear-gradient(135deg, #a855f7 0%, #ec4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: 800;
        margin: 0;
    }
    .header-subtitle {
        color: #cbd5e1;
        font-size: 1rem;
        margin-top: 0.5rem;
    }
    .custom-card {
        background: rgba(30, 27, 75, 0.6);
        backdrop-filter: blur(10px);
        padding: 2rem;
        border-radius: 24px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(147, 51, 234, 0.3);
        margin-bottom: 1.5rem;
    }
    .card-header {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 1.5rem;
    }
    .card-icon {
        width: 50px;
        height: 50px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
    }
    .icon-purple {
        background: linear-gradient(135deg, #a855f7 0%, #ec4899 100%);
    }
    .icon-green {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    }
    .icon-blue {
        background: linear-gradient(135deg, #3b82f6 0%, #06b6d4 100%);
    }
    .icon-orange {
        background: linear-gradient(135deg, #f59e0b 0%, #ef4444 100%);
    }
    .card-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #f1f5f9;
        margin: 0;
    }
    .stButton>button {
        background: linear-gradient(135deg, #a855f7 0%, #ec4899 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(147, 51, 234, 0.3);
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 12px rgba(147, 51, 234, 0.4);
    }
    .stTextInput>div>div>input,
    .stTextArea>div>div>textarea,
    .stNumberInput>div>div>input,
    .stSelectbox>div>div>div {
        background: rgba(15, 23, 42, 0.6);
        border: 2px solid rgba(147, 51, 234, 0.3);
        border-radius: 12px;
        padding: 0.75rem 1rem;
        font-size: 1rem;
        color: #f1f5f9;
        transition: all 0.3s ease;
    }
    .stTextInput>div>div>input:focus,
    .stTextArea>div>div>textarea:focus,
    .stNumberInput>div>div>input:focus,
    .stSelectbox>div>div>div:focus {
        border-color: #a855f7;
        box-shadow: 0 0 0 3px rgba(168, 85, 247, 0.2);
        background: rgba(15, 23, 42, 0.8);
    }
    .stTextInput>label,
    .stTextArea>label,
    .stNumberInput>label,
    .stSelectbox>label {
        color: #cbd5e1 !important;
        font-weight: 600;
    }
    .goal-item {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        padding: 1rem 1.5rem;
        border-radius: 12px;
        border: 2px solid #047857;
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
        gap: 1rem;
        color: white;
        font-weight: 600;
    }
    .goal-completed {
        opacity: 0.7;
        background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%);
        border-color: #374151;
    }
    .info-box {
        background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%);
        padding: 1.5rem;
        border-radius: 16px;
        border: 2px solid #6d28d9;
        margin-bottom: 1.5rem;
    }
    .info-title {
        font-weight: 700;
        color: white;
        margin-bottom: 0.5rem;
        font-size: 1.1rem;
    }
    .info-text {
        color: #e9d5ff;
        font-size: 0.95rem;
        line-height: 1.6;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(30, 27, 75, 0.6);
        padding: 8px;
        border-radius: 16px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 12px;
        padding: 12px 24px;
        font-weight: 600;
        background: transparent;
        color: #cbd5e1;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #a855f7 0%, #ec4899 100%);
        color: white;
    }
    .stSuccess, .stError, .stInfo, .stWarning {
        border-radius: 12px;
        padding: 1rem;
    }
    .welcome-card {
        background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%);
        padding: 2rem;
        border-radius: 20px;
        border: 2px solid #6d28d9;
        text-align: center;
        margin: 2rem 0;
    }
    .welcome-icon {
        font-size: 4rem;
        margin-bottom: 1rem;
    }
    .welcome-title {
        font-size: 2.5rem;
        font-weight: 800;
        color: white;
        margin-bottom: 0.5rem;
    }
    .welcome-subtitle {
        font-size: 1.2rem;
        color: #e9d5ff;
    }
    h1, h2, h3, h4, h5, h6, p, span, div {
        color: #f1f5f9;
    }
    .stExpander {
        background: rgba(30, 27, 75, 0.4);
        border-radius: 12px;
        border: 1px solid rgba(147, 51, 234, 0.3);
    }
    
    /* Chat message styling */
    .stChatMessage {
        background: rgba(30, 27, 75, 0.6) !important;
        border-radius: 16px !important;
        border: 1px solid rgba(147, 51, 234, 0.3) !important;
        padding: 1rem !important;
        margin-bottom: 1rem !important;
    }
    
    [data-testid="stChatMessageContent"] {
        color: #f1f5f9 !important;
    }
    
    /* User message styling */
    [data-testid="stChatMessage"][data-testid*="user"] {
        background: rgba(168, 85, 247, 0.2) !important;
        border: 1px solid rgba(168, 85, 247, 0.4) !important;
    }
    
    /* Assistant message styling */
    [data-testid="stChatMessage"][data-testid*="assistant"] {
        background: rgba(30, 27, 75, 0.8) !important;
        border: 2px solid rgba(147, 51, 234, 0.3) !important;
    }
    
    .chat-container {
        background: rgba(30, 27, 75, 0.3);
        border-radius: 16px;
        padding: 1rem;
        margin-bottom: 1rem;
        border: 1px solid rgba(147, 51, 234, 0.2);
        max-height: 500px;
        overflow-y: auto;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "role" not in st.session_state:
    st.session_state.role = None
if "token" not in st.session_state:
    st.session_state.token = None
if "patient_username" not in st.session_state:
    st.session_state.patient_username = None
if "chat_log" not in st.session_state:
    st.session_state.chat_log = []
if "goals" not in st.session_state:
    st.session_state.goals = []
if "page" not in st.session_state:
    st.session_state.page = "role_select"
if "user_type" not in st.session_state:
    st.session_state.user_type = None
if "conversation_started" not in st.session_state:
    st.session_state.conversation_started = False
if "message_count" not in st.session_state:
    st.session_state.message_count = 0
if "medication_taken" not in st.session_state:
    st.session_state.medication_taken = {}

# Header
st.markdown("""
<div class="main-header">
    <h1 class="header-title">💙 MemoryCare</h1>
    <p class="header-subtitle">Your Compassionate AI Companion for Dementia & Alzheimer's Care</p>
</div>
""", unsafe_allow_html=True)

# Logout button
if st.session_state.role:
    col1, col2, col3 = st.columns([6, 1, 1])
    with col3:
        if st.button("🚪 Logout", key="logout_btn"):
            st.session_state.role = None
            st.session_state.token = None
            st.session_state.patient_username = None
            st.session_state.chat_log = []
            st.session_state.goals = []
            st.session_state.page = "role_select"
            st.session_state.user_type = None
            st.session_state.conversation_started = False
            st.session_state.message_count = 0
            st.session_state.medication_taken = {}
            st.rerun()

# ==================== AUTH PAGES ====================
if not st.session_state.role:
    if st.session_state.page == "role_select":
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            <div class="welcome-card">
                <div class="welcome-icon">💙</div>
                <h2 class="welcome-title">Welcome to MemoryCare</h2>
                <p class="welcome-subtitle">Please select your role to continue</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            col_patient, col_doctor = st.columns(2)
            
            with col_patient:
                if st.button("👤 I'm a Patient", use_container_width=True, key="patient_role"):
                    st.session_state.user_type = "patient"
                    st.session_state.page = "login"
                    st.rerun()
                st.markdown("""
                <div style="text-align: center; padding: 1rem; background: rgba(30, 27, 75, 0.6); border-radius: 12px; border: 1px solid rgba(147, 51, 234, 0.3); margin-top: 1rem;">
                    <p style="color: #cbd5e1; margin: 0;">Access your personalized care, chat with AI, and track your goals</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col_doctor:
                if st.button("👨‍⚕️ I'm a Doctor", use_container_width=True, key="doctor_role"):
                    st.session_state.user_type = "doctor"
                    st.session_state.page = "doctor_login"
                    st.rerun()
                st.markdown("""
                <div style="text-align: center; padding: 1rem; background: rgba(30, 27, 75, 0.6); border-radius: 12px; border: 1px solid rgba(147, 51, 234, 0.3); margin-top: 1rem;">
                    <p style="color: #cbd5e1; margin: 0;">Manage patients, assign goals, and monitor medications</p>
                </div>
                """, unsafe_allow_html=True)
    
    elif st.session_state.page == "login":
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("⬅️ Back to Role Selection", key="back_to_role"):
                st.session_state.page = "role_select"
                st.session_state.user_type = None
                st.rerun()
            
            st.markdown("""
            <div class="welcome-card">
                <div class="welcome-icon">👤</div>
                <h2 class="welcome-title">Patient Login</h2>
                <p class="welcome-subtitle">Welcome back! Sign in to continue</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            login_user = st.text_input("Username", key="login_user", placeholder="Enter your username")
            login_pass = st.text_input("Password", type="password", key="login_pass", placeholder="Enter your password")
            
            if st.button("🔓 Sign In", use_container_width=True):
                r = requests.post(f"{API}/auth/patient/login", json={"username": login_user, "password": login_pass})
                if r.ok:
                    j = r.json()
                    st.session_state.role = j["role"]
                    st.session_state.token = j["token"]
                    st.session_state.patient_username = login_user
                    g_resp = requests.get(f"{API}/patient/goals", params={"token": j["token"]})
                    if g_resp.ok:
                        st.session_state.goals = g_resp.json().get("goals", [])
                    st.success("✅ Logged in successfully!")
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials. Please try again.")
            
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("<h3 style='color: #f1f5f9; text-align: center;'>Don't have an account?</h3>", unsafe_allow_html=True)
            if st.button("✨ Create New Account", use_container_width=True):
                st.session_state.page = "signup"
                st.rerun()
    
    elif st.session_state.page == "doctor_login":
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("⬅️ Back to Role Selection", key="back_to_role_doc"):
                st.session_state.page = "role_select"
                st.session_state.user_type = None
                st.rerun()
            
            st.markdown("""
            <div class="welcome-card">
                <div class="welcome-icon">👨‍⚕️</div>
                <h2 class="welcome-title">Doctor Login</h2>
                <p class="welcome-subtitle">Access patient management portal</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            doc_user = st.text_input("Doctor Username", key="doc_user", value="doctor", placeholder="Enter doctor username")
            doc_pass = st.text_input("Password", type="password", key="doc_pass", value="doctor", placeholder="Enter password")
            
            if st.button("🔓 Sign In as Doctor", use_container_width=True):
                r = requests.post(f"{API}/auth/doctor/login", json={"username": doc_user, "password": doc_pass})
                if r.ok:
                    j = r.json()
                    st.session_state.role = j["role"]
                    st.session_state.token = j["token"]
                    st.success("✅ Doctor logged in successfully!")
                    st.rerun()
                else:
                    st.error("❌ Invalid doctor credentials.")
            st.markdown("</div>", unsafe_allow_html=True)
    
    elif st.session_state.page == "signup":
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("⬅️ Back to Login", key="back_to_login"):
                st.session_state.page = "login"
                st.rerun()
            
            st.markdown("""
            <div class="welcome-card">
                <div class="welcome-icon">✨</div>
                <h2 class="welcome-title">Create Your Account</h2>
                <p class="welcome-subtitle">Join MemoryCare today</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            st.markdown("<h3 style='color: #f1f5f9;'>👤 Basic Information</h3>", unsafe_allow_html=True)
            su_user = st.text_input("Username *", key="su_user", placeholder="Choose a unique username")
            su_pass = st.text_input("Password *", type="password", key="su_pass", placeholder="Create a secure password")
            su_name = st.text_input("Full Name *", key="su_name", placeholder="Your full name")
            st.markdown("---")
            st.markdown("<h3 style='color: #f1f5f9;'>💙 Personal Details</h3>", unsafe_allow_html=True)
            su_family = st.text_area("Family Information", key="su_family", placeholder="Tell us about your family members", height=100)
            su_hobbies = st.text_area("Hobbies & Interests", key="su_hobbies", placeholder="What activities do you enjoy?", height=100)
            st.markdown("---")
            st.markdown("<h3 style='color: #f1f5f9;'>🚨 Emergency Contact</h3>", unsafe_allow_html=True)
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                su_em_name = st.text_input("Contact Name", key="su_em_name", placeholder="Emergency contact person")
            with col_e2:
                su_em_phone = st.text_input("Phone Number", key="su_em_phone", placeholder="Contact phone")
            st.markdown("</div>", unsafe_allow_html=True)
            
            if st.button("🎉 Create Account", use_container_width=True):
                if not su_user or not su_pass or not su_name:
                    st.error("❌ Please fill in all required fields (marked with *)")
                else:
                    payload = {
                        "username": su_user,
                        "password": su_pass,
                        "full_name": su_name,
                        "family_info": su_family,
                        "emergency_contact_name": su_em_name,
                        "emergency_contact_phone": su_em_phone,
                        "hobbies": su_hobbies,
                    }
                    r = requests.post(f"{API}/auth/patient/signup", json=payload)
                    if r.ok:
                        st.success("✅ Account created successfully! Please login to continue.")
                        st.session_state.page = "login"
                        st.rerun()
                    else:
                        st.error(f"❌ Signup failed: {r.text}")
            st.markdown("<p style='text-align: center; color: #cbd5e1; margin-top: 1rem;'>* Required fields</p>", unsafe_allow_html=True)

# ==================== MAIN APP ====================
else:
    if st.session_state.role == "patient":
        # START CONVERSATION
        if not st.session_state.conversation_started:
            try:
                initial_greeting = {
                    "user_id": st.session_state.patient_username,
                    "message": "__SYSTEM_START__",
                    "token": st.session_state.token,
                }
                r = requests.post(f"{API}/chat", json=initial_greeting)
                if r.ok:
                    data = r.json()
                    st.session_state.chat_log.append(("MemoryCare", data["reply"]))
                    st.session_state.conversation_started = True
            except Exception as e:
                print(f"Error starting conversation: {e}")
        
        col_left, col_right = st.columns([1, 2])
        
        with col_left:
            st.markdown("""
            <div class="custom-card">
                <div class="card-header">
                    <div class="card-icon icon-green">🎯</div>
                    <h3 class="card-title">Your Goals</h3>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.session_state.goals:
                for g in st.session_state.goals:
                    completed = g.get('completed', False)
                    icon = "✅" if completed else "⭕"
                    status_class = "goal-completed" if completed else ""
                    st.markdown(f"""
                    <div class="goal-item {status_class}">
                        <span style="font-size: 1.5rem;">{icon}</span>
                        <span style="flex: 1; color: white; font-weight: 600;">{g.get('text', '')}</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("🎯 No goals assigned yet. Your doctor will set some goals for you soon!")
            
            st.markdown(f"""
            <div class="info-box">
                <div class="info-title">👋 Welcome, {st.session_state.patient_username}!</div>
                <div class="info-text">
                    I'm here to chat with you, remind you about medications, and help you 
                    achieve your goals. Let's have a great conversation today!
                </div>
            </div>
            """, unsafe_allow_html=True)
        # === Medication Dashboard === ## MEDICATION CARD UPDATE ISSUE 2 CLAUDE
            st.markdown(f"""
            <div style="text-align: center; background: rgba(30, 27, 75, 0.6); padding: 1rem; border-radius: 12px; border: 1px solid rgba(147, 51, 234, 0.3); margin-bottom: 1rem;">
                <h3 style="color: #a855f7; margin: 0;">📅 {datetime.now().strftime('%A, %B %d, %Y')}</h3>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("""
            <div class="custom-card">
                <div class="card-header">
                    <div class="card-icon icon-blue">💊</div>
                    <h3 class="card-title">Your Medications</h3>
                </div>
            </div>
            """, unsafe_allow_html=True)

            try:
                med_resp = requests.get(f"{API}/patient/medications", params={"token": st.session_state.token})
                
                if med_resp.ok:
                    meds = med_resp.json().get("medications", [])
                    
                    if meds:
                        for m in meds:
                            st.markdown(f"**{m['name']}** — {m['times_per_day']}x per day")
                            st.caption(f"🕒 {m['specific_times'] or 'No specific times'} | {m['instructions'] or ''}")

                            # Get today's logs - FIX: Parse date properly
                            today_str = datetime.now().strftime("%Y-%m-%d")
                            taken_today = []
                            
                            for log in m['logs']:
                                # Extract just the date part (YYYY-MM-DD) from the log
                                log_date = log['date'].split()[0] if ' ' in log['date'] else log['date']
                                if log_date == today_str and log.get('taken', True):
                                    taken_today.append(log)
                            
                            taken_count = len(taken_today)
                            remaining = m['times_per_day'] - taken_count
                            
                            # Disable button if all doses taken
                            button_disabled = taken_count >= m['times_per_day']
                            button_text = f"✅ Complete ({taken_count}/{m['times_per_day']})" if button_disabled else f"✅ Take {m['name']}"
                            
                            if st.button(button_text, key=f"take_{m['name']}", disabled=button_disabled):
                                log_resp = requests.post(
                                    f"{API}/patient/medications/log",
                                    params={"token": st.session_state.token, "med_name": m["name"]}
                                )
                                if log_resp.ok:
                                    st.success(f"Marked {m['name']} as taken!")
                                    st.rerun()
                                else:
                                    st.error(log_resp.json().get("detail", "Error logging medication"))

                            # Display progress
                            progress_value = taken_count / m['times_per_day'] if m['times_per_day'] > 0 else 0
                            st.progress(progress_value)
                            
                            if button_disabled:
                                st.caption(f"✅ All doses complete! ({taken_count}/{m['times_per_day']})")
                            else:
                                st.caption(f"Taken {taken_count}/{m['times_per_day']} times today | {remaining} remaining")
                            
                            st.markdown("---")
                    else:
                        st.info("💊 No medications assigned yet.")
                else:
                    st.error(f"Error fetching medications: Status {med_resp.status_code}")
                    
            except Exception as e:
                st.error(f"Failed to load medications: {e}")


        with col_right:
            st.markdown("""
            <div class="custom-card">
                <div class="card-header">
                    <div class="card-icon icon-purple">💬</div>
                    <h3 class="card-title">Chat with MemoryCare</h3>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Chat container with native Streamlit chat messages
            chat_container = st.container(height=450)
            
            with chat_container:
                if not st.session_state.chat_log:
                    st.markdown("""
                    <div style="display: flex; align-items: center; justify-content: center; height: 400px;">
                        <div style="text-align: center;">
                            <div style="font-size: 4rem; margin-bottom: 1rem;">💙</div>
                            <h3 style="color: #f1f5f9;">Loading your conversation...</h3>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    for who, text in st.session_state.chat_log:
                        if who == "You":
                            with st.chat_message("user", avatar="👤"):
                                st.write(text)
                        else:
                            with st.chat_message("assistant", avatar="💙"):
                                st.write(text)
            
            # Input form
            st.markdown("---")
            
            with st.form(key="chat_form", clear_on_submit=True):
                col_msg, col_btn = st.columns([4, 1])
                with col_msg:
                    msg = st.text_input("", key="chat_input", label_visibility="collapsed", placeholder="Say something...")
                with col_btn:
                    send_btn = st.form_submit_button("📤 Send", use_container_width=True)
                
                if send_btn and msg:
                    st.session_state.message_count += 1
                    took_med_keywords = ["took", "taken", "had my", "had the", "took my", "swallowed"]
                    if any(k in msg.lower() for k in took_med_keywords) and ("pill" in msg.lower() or "medicine" in msg.lower() or "medication" in msg.lower()):
                        st.session_state.medication_taken["last_taken"] = st.session_state.message_count
                    
                    payload = {
                        "user_id": st.session_state.patient_username,
                        "message": msg,
                        "token": st.session_state.token,
                        "message_count": st.session_state.message_count,
                        "medication_taken": st.session_state.medication_taken
                    }
                    r = requests.post(f"{API}/chat", json=payload)
                    if r.ok:
                        data = r.json()
                        st.session_state.chat_log.append(("You", msg))
                        st.session_state.chat_log.append(("MemoryCare", data["reply"]))
                        g_resp = requests.get(f"{API}/patient/goals", params={"token": st.session_state.token})
                        if g_resp.ok:
                            st.session_state.goals = g_resp.json().get("goals", [])
                        st.rerun()
                    else:
                        st.error("❌ Error sending message")

    elif st.session_state.role == "doctor":
        st.markdown("""
        <div class="custom-card">
            <div class="card-header">
                <div class="card-icon icon-orange">👨‍⚕️</div>
                <h3 class="card-title">Doctor Dashboard</h3>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Fetch all patients
        try:
            patients_response = requests.get(f"{API}/doctor/patients", params={"token": st.session_state.token})
            if patients_response.ok:
                patients_data = patients_response.json()
                all_patients = patients_data.get("patients", [])
            else:
                all_patients = []
        except Exception as e:
            all_patients = []
            st.error(f"Error fetching patients: {e}")
        
        st.markdown("<h3 style='color: #f1f5f9;'>Select Patient to Manage</h3>", unsafe_allow_html=True)
        
        if all_patients:
            patient_options = ["-- Select a patient --"] + [f"{p['full_name']} ({p['username']})" for p in all_patients]
            patient_usernames = {f"{p['full_name']} ({p['username']})": p['username'] for p in all_patients}
            
            selected_patient = st.selectbox(
                "Choose from registered patients:",
                options=patient_options,
                index=0,
                key="patient_selector"
            )
            
            if selected_patient != "-- Select a patient --":
                selected_username = patient_usernames[selected_patient]
                if st.button("✅ Select This Patient", use_container_width=True):
                    st.session_state.patient_username = selected_username
                    st.success(f"✅ Now managing: **{selected_patient}**")
                    st.rerun()
        else:
            st.warning("⚠️ No patients found in the system. Patients need to sign up first.")
            st.info("💡 Tip: You can still manually enter a username if you know it.")
        
        with st.expander("🔍 Or manually enter patient username"):
            manual_username = st.text_input("Patient username", placeholder="Enter patient username manually")
            if st.button("✅ Select Manually"):
                if manual_username:
                    st.session_state.patient_username = manual_username
                    st.success(f"✅ Now managing: **{manual_username}**")
                    st.rerun()
                else:
                    st.error("Please enter a username")
        
        if st.session_state.patient_username:
            st.markdown(f"""
            <div class="info-box">
                <div class="info-title">Currently Managing</div>
                <div class="info-text">Patient: <strong>{st.session_state.patient_username}</strong></div>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                <div class="custom-card">
                    <div class="card-header">
                        <div class="card-icon icon-green">🎯</div>
                        <h3 class="card-title">Manage Goals</h3>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Fetch patient goals
                try:
                    goals_response = requests.get(
                        f"{API}/doctor/patient-goals",
                        params={
                            "patient_username": st.session_state.patient_username,
                            "token": st.session_state.token
                        }
                    )
                    if goals_response.ok:
                        patient_goals = goals_response.json().get("goals", [])
                    else:
                        patient_goals = []
                except Exception as e:
                    patient_goals = []
                    st.error(f"Error fetching goals: {e}")

                # Show goal status tabs
                goal_tab1, goal_tab2 = st.tabs(["📝 Assign New Goal", "📊 Goal Status"])

                with goal_tab1:
                    with st.form("add_goal"):
                        goal_text = st.text_area("Goal description", placeholder="e.g., Go for a short walk after dinner", height=100)
                        ok = st.form_submit_button("➕ Assign Goal", use_container_width=True)
                        if ok and goal_text:
                            r = requests.post(
                                f"{API}/doctor/goals",
                                params={
                                    "patient_username": st.session_state.patient_username,
                                    "token": st.session_state.token,
                                },
                                json={"text": goal_text},
                            )
                            if r.ok:
                                st.success("🎯 Goal assigned successfully!")
                                st.rerun()
                            else:
                                st.error(f"❌ {r.text}")

                with goal_tab2:
                    if patient_goals:
                        active_goals = [g for g in patient_goals if not g['completed']]
                        completed_goals = [g for g in patient_goals if g['completed']]
                        
                        # Show active goals
                        st.markdown("<h4 style='color: #10b981;'>✅ Active Goals</h4>", unsafe_allow_html=True)
                        if active_goals:
                            for g in active_goals:
                                st.markdown(f"""
                                <div class="goal-item">
                                    <span style="font-size: 1.5rem;">⭕</span>
                                    <span style="flex: 1; color: white; font-weight: 600;">{g['text']}</span>
                                    <span style="color: #e9d5ff; font-size: 0.9rem;">Assigned: {g['created_at'][:10]}</span>
                                </div>
                                """, unsafe_allow_html=True)
                        else:
                            st.info("No active goals assigned yet.")
                        
                        st.markdown("---")
                        
                        # Show completed goals
                        st.markdown("<h4 style='color: #6b7280;'>🎉 Completed Goals</h4>", unsafe_allow_html=True)
                        if completed_goals:
                            for g in completed_goals:
                                completed_date = g.get('completed_at_str', g.get('completed_at', 'Unknown')[:10] if g.get('completed_at') else 'Unknown')
                                st.markdown(f"""
                                <div class="goal-item goal-completed">
                                    <span style="font-size: 1.5rem;">✅</span>
                                    <span style="flex: 1; color: white; font-weight: 600;">{g['text']}</span>
                                    <span style="color: #d1d5db; font-size: 0.9rem;">Completed: {completed_date}</span>
                                </div>
                                """, unsafe_allow_html=True)
                        else:
                            st.info("No completed goals yet.")
                        
                        # Summary statistics
                        total_goals = len(patient_goals)
                        completion_rate = (len(completed_goals) / total_goals * 100) if total_goals > 0 else 0
                        
                        st.markdown(f"""
                        <div class="info-box" style="margin-top: 1rem;">
                            <div class="info-title">📈 Goal Progress Summary</div>
                            <div class="info-text">
                                Total Goals: <strong>{total_goals}</strong> | 
                                Active: <strong>{len(active_goals)}</strong> | 
                                Completed: <strong>{len(completed_goals)}</strong> | 
                                Completion Rate: <strong>{completion_rate:.1f}%</strong>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.info("No goals assigned yet. Use the 'Assign New Goal' tab to create one.")
            
            with col2:
                st.markdown("""
                <div class="custom-card">
                    <div class="card-header">
                        <div class="card-icon icon-blue">💊</div>
                        <h3 class="card-title">Add Medication</h3>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                with st.form("add_med"):
                    name = st.text_input("Medication name", placeholder="e.g., Aspirin")
                    tpd = st.number_input("Times per day", min_value=1, max_value=6, value=3)
                    times = st.text_input("Specific times (HH:MM)", value="09:00,14:00,20:00")
                    instr = st.text_area("Instructions", value="Take with water.", height=80)
                    ok = st.form_submit_button("➕ Add Medication", use_container_width=True)
                    if ok and name:
                        r = requests.post(
                            f"{API}/doctor/medications",
                            params={"token": st.session_state.token},
                            json={
                                "patient_username": st.session_state.patient_username,
                                "name": name,
                                "times_per_day": int(tpd),
                                "specific_times": times.strip(),
                                "instructions": instr,
                                "active": True,
                            },
                        )
                        if r.ok:
                            st.success("💊 Medication added successfully!")
                        else:
                            st.error(f"❌ {r.text}")
                
                st.markdown("""
                <div class="custom-card">
                    <div class="card-header">
                        <div class="card-icon icon-blue">📊</div>
                        <h3 class="card-title">Medication Status</h3>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                try:
                    med_hist_resp = requests.get(
                        f"{API}/doctor/patient-medications",
                        params={"patient_username": st.session_state.patient_username, "token": st.session_state.token}
                    )
                    if med_hist_resp.ok:
                        meds = med_hist_resp.json().get("medications", [])
                        if meds:
                            for m in meds:
                                st.markdown(f"**{m['name']}** — {m['times_per_day']}x/day | {m['specific_times']}")
                                st.caption(f"📝 {m['instructions'] or ''}")

                                logs = m.get('logs', [])
                                recent_logs = [l for l in logs if l['date'] == datetime.now().strftime("%Y-%m-%d")]
                                taken_today = sum(1 for l in recent_logs if l['taken'])
                                st.progress(taken_today / m['times_per_day'])
                                st.caption(f"Taken {taken_today}/{m['times_per_day']} times today")

                                with st.expander("📅 View History"):
                                    for l in logs[-10:]:
                                        st.write(f"{l['date']} — {'✅' if l['taken'] else '❌'} {l.get('time_taken', '')}")
                        else:
                            st.info("No medications found for this patient.")
                    else:
                        st.error("Failed to fetch medication history.")
                except Exception as e:
                    st.error(f"Error: {e}")


        else:
            st.markdown("""
            <div style="text-align: center; padding: 3rem; background: rgba(30, 27, 75, 0.6); border-radius: 20px; border: 2px solid rgba(147, 51, 234, 0.3); margin-top: 2rem;">
                <div style="font-size: 4rem; margin-bottom: 1rem;">🏥</div>
                <h3 style="color: #f1f5f9;">Select a Patient to Begin</h3>
                <p style="color: #cbd5e1;">Choose a patient from the dropdown above to manage their care</p>
            </div>
            """, unsafe_allow_html=True)