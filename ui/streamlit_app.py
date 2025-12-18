# memorycare_app/ui/streamlit_app.py
"""
MemoryCare Streamlit 前端应用

本文件是 MemoryCare 应用的前端界面，使用 Streamlit 框架构建。
提供以下功能：
1. 用户认证界面（患者注册/登录、医生登录）
2. 患者界面（聊天、药物管理、目标查看）
3. 医生界面（患者管理、药物分配、目标分配、进度监控）

技术栈：
- Streamlit: Web 应用框架
- Requests: HTTP 客户端（与后端 API 通信）
"""

import requests
import streamlit as st
from datetime import datetime

# 后端 API 服务器地址
# 注意：如果后端运行在不同端口，需要修改此地址
API = "http://127.0.0.1:8001"

# 中文日期格式化函数
def format_chinese_date(dt: datetime) -> str:
    """
    将日期时间格式化为中文格式
    
    参数:
        dt: datetime 对象
        
    返回:
        str: 中文格式的日期字符串，如 "2024年1月1日 星期一"
    """
    # 中文星期映射
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    # 中文月份映射
    months = ["", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二"]
    
    weekday = weekdays[dt.weekday()]
    month = months[dt.month]
    day = dt.day
    year = dt.year
    
    return f"{year}年{month}月{day}日 {weekday}"

# 页面配置：设置应用的基本外观和行为
st.set_page_config(
    page_title="MemoryCare - AI 护理助手",  # 浏览器标签页标题
    page_icon="💙",  # 页面图标（emoji）
    layout="wide",  # 宽屏布局，充分利用屏幕空间
    initial_sidebar_state="collapsed"  # 初始状态：侧边栏折叠
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
        font-size: 0.8rem;
        color: #f1f5f9 !important;
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
    ul[data-testid="stSelectboxVirtualDropdown"] {
        background-color: #222 !important;
        color: #ffffff !important;
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

# ============================
#        会话状态初始化
# ============================
# Streamlit 使用 session_state 在页面重新加载之间保持状态
# 这些变量用于跟踪用户登录状态、对话历史等

# 用户角色：None（未登录）、"patient"（患者）、"doctor"（医生）
if "role" not in st.session_state:
    st.session_state.role = None

# 认证 Token：用于 API 调用的身份验证
if "token" not in st.session_state:
    st.session_state.token = None

# 患者用户名：当前登录的患者用户名（医生界面也用于选择管理的患者）
if "patient_username" not in st.session_state:
    st.session_state.patient_username = None

# 聊天日志：存储对话历史，格式为 [("You", "消息"), ("MemoryCare", "回复"), ...]
if "chat_log" not in st.session_state:
    st.session_state.chat_log = []

# 目标列表：患者当前的治疗目标
if "goals" not in st.session_state:
    st.session_state.goals = []

# 当前页面：用于导航控制
# 可能的值："role_select"（角色选择）、"login"（登录）、"signup"（注册）、"doctor_login"（医生登录）
if "page" not in st.session_state:
    st.session_state.page = "role_select"

# 用户类型：在角色选择时使用，区分患者和医生流程
if "user_type" not in st.session_state:
    st.session_state.user_type = None

# 对话是否已开始：标记是否已发送初始问候消息
if "conversation_started" not in st.session_state:
    st.session_state.conversation_started = False

# 消息计数：追踪对话中的消息数量（用于未来功能扩展）
if "message_count" not in st.session_state:
    st.session_state.message_count = 0

# 药物服用追踪：记录药物服用情况（用于未来功能扩展）
if "medication_taken" not in st.session_state:
    st.session_state.medication_taken = {}

# 页面头部
st.markdown("""
<div class="main-header">
    <h1 class="header-title">💙 MemoryCare</h1>
    <p class="header-subtitle">您的贴心 AI 护理助手，专为痴呆症和阿尔茨海默病护理而设计</p>
</div>
""", unsafe_allow_html=True)

# 登出按钮
if st.session_state.role:
    col1, col2, col3 = st.columns([6, 1, 1])
    with col3:
        if st.button("🚪 退出登录", key="logout_btn"):
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

# ==================== 认证页面 ====================
# 如果用户未登录（role 为 None），显示认证相关页面
if not st.session_state.role:
    if st.session_state.page == "role_select":
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            <div class="welcome-card">
                <div class="welcome-icon">💙</div>
                <h2 class="welcome-title">欢迎使用 MemoryCare</h2>
                <p class="welcome-subtitle">请选择您的身份以继续</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            col_patient, col_doctor = st.columns(2)
            
            with col_patient:
                if st.button("👤 我是患者", use_container_width=True, key="patient_role"):
                    st.session_state.user_type = "patient"
                    st.session_state.page = "login"
                    st.rerun()
                st.markdown("""
                <div style="text-align: center; padding: 1rem; background: rgba(30, 27, 75, 0.6); border-radius: 12px; border: 1px solid rgba(147, 51, 234, 0.3); margin-top: 1rem;">
                    <p style="color: #cbd5e1; margin: 0;">访问您的个性化护理，与 AI 聊天，追踪您的目标</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col_doctor:
                if st.button("👨‍⚕️ 我是医生", use_container_width=True, key="doctor_role"):
                    st.session_state.user_type = "doctor"
                    st.session_state.page = "doctor_login"
                    st.rerun()
                st.markdown("""
                <div style="text-align: center; padding: 1rem; background: rgba(30, 27, 75, 0.6); border-radius: 12px; border: 1px solid rgba(147, 51, 234, 0.3); margin-top: 1rem;">
                    <p style="color: #cbd5e1; margin: 0;">管理患者，分配目标，监控药物</p>
                </div>
                """, unsafe_allow_html=True)
    
    elif st.session_state.page == "login":
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("⬅️ 返回角色选择", key="back_to_role"):
                st.session_state.page = "role_select"
                st.session_state.user_type = None
                st.rerun()
            
            st.markdown("""
            <div class="welcome-card">
                <div class="welcome-icon">👤</div>
                <h2 class="welcome-title">患者登录</h2>
                <p class="welcome-subtitle">欢迎回来！请登录以继续</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            login_user = st.text_input("用户名", key="login_user", placeholder="请输入您的用户名")
            login_pass = st.text_input("密码", type="password", key="login_pass", placeholder="请输入您的密码")
            
            if st.button("🔓 登录", use_container_width=True):
                try:
                    r = requests.post(f"{API}/auth/patient/login", json={"username": login_user, "password": login_pass}, timeout=5)
                    if r.ok:
                        j = r.json()
                        st.session_state.role = j["role"]
                        st.session_state.token = j["token"]
                        st.session_state.patient_username = login_user
                        try:
                            g_resp = requests.get(f"{API}/patient/goals", params={"token": j["token"]}, timeout=5)
                            if g_resp.ok:
                                st.session_state.goals = g_resp.json().get("goals", [])
                        except:
                            pass  # 如果获取目标失败，不影响登录
                        st.success("✅ 登录成功！")
                        st.rerun()
                    else:
                        st.error("❌ 用户名或密码错误，请重试。")
                except requests.exceptions.ConnectionError:
                    st.error("❌ 无法连接到后端服务器。请确保后端服务正在运行（运行：uvicorn api.main:app --reload）")
                except requests.exceptions.Timeout:
                    st.error("❌ 请求超时，请稍后重试")
                except Exception as e:
                    st.error(f"❌ 发生错误：{str(e)}")
            
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("<h3 style='color: #f1f5f9; text-align: center;'>还没有账户？</h3>", unsafe_allow_html=True)
            if st.button("✨ 创建新账户", use_container_width=True):
                st.session_state.page = "signup"
                st.rerun()
    
    elif st.session_state.page == "doctor_login":
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("⬅️ 返回角色选择", key="back_to_role_doc"):
                st.session_state.page = "role_select"
                st.session_state.user_type = None
                st.rerun()
            
            st.markdown("""
            <div class="welcome-card">
                <div class="welcome-icon">👨‍⚕️</div>
                <h2 class="welcome-title">医生登录</h2>
                <p class="welcome-subtitle">访问患者管理门户</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            doc_user = st.text_input("医生用户名", key="doc_user", value="doctor", placeholder="请输入医生用户名")
            doc_pass = st.text_input("密码", type="password", key="doc_pass", value="doctor", placeholder="请输入密码")
            
            if st.button("🔓 医生登录", use_container_width=True):
                try:
                    r = requests.post(f"{API}/auth/doctor/login", json={"username": doc_user, "password": doc_pass}, timeout=5)
                    if r.ok:
                        j = r.json()
                        st.session_state.role = j["role"]
                        st.session_state.token = j["token"]
                        st.success("✅ 医生登录成功！")
                        st.rerun()
                    else:
                        st.error("❌ 医生凭证无效。")
                except requests.exceptions.ConnectionError:
                    st.error("❌ 无法连接到后端服务器。请确保后端服务正在运行（运行：uvicorn api.main:app --reload）")
                except requests.exceptions.Timeout:
                    st.error("❌ 请求超时，请稍后重试")
                except Exception as e:
                    st.error(f"❌ 发生错误：{str(e)}")
            st.markdown("</div>", unsafe_allow_html=True)
    
    elif st.session_state.page == "signup":
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("⬅️ 返回登录", key="back_to_login"):
                st.session_state.page = "login"
                st.rerun()
            
            st.markdown("""
            <div class="welcome-card">
                <div class="welcome-icon">✨</div>
                <h2 class="welcome-title">创建您的账户</h2>
                <p class="welcome-subtitle">立即加入 MemoryCare</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            st.markdown("<h3 style='color: #f1f5f9;'>👤 基本信息</h3>", unsafe_allow_html=True)
            su_user = st.text_input("用户名 *", key="su_user", placeholder="请选择一个唯一的用户名")
            su_pass = st.text_input("密码 *", type="password", key="su_pass", placeholder="请创建一个安全的密码")
            su_name = st.text_input("全名 *", key="su_name", placeholder="请输入您的全名")
            st.markdown("---")
            st.markdown("<h3 style='color: #f1f5f9;'>💙 个人信息</h3>", unsafe_allow_html=True)
            su_family = st.text_area("家庭信息", key="su_family", placeholder="请告诉我们您的家庭成员情况", height=100)
            su_hobbies = st.text_area("兴趣爱好", key="su_hobbies", placeholder="您喜欢什么活动？", height=100)
            st.markdown("---")
            st.markdown("<h3 style='color: #f1f5f9;'>🚨 紧急联系人</h3>", unsafe_allow_html=True)
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                su_em_name = st.text_input("联系人姓名", key="su_em_name", placeholder="紧急联系人姓名")
            with col_e2:
                su_em_phone = st.text_input("电话号码", key="su_em_phone", placeholder="联系人电话")
            st.markdown("</div>", unsafe_allow_html=True)
            
            if st.button("🎉 创建账户", use_container_width=True):
                if not su_user or not su_pass or not su_name:
                    st.error("❌ 请填写所有必填字段（标有 * 的字段）")
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
                    try:
                        r = requests.post(f"{API}/auth/patient/signup", json=payload, timeout=5)
                        if r.ok:
                            st.success("✅ 账户创建成功！请登录以继续。")
                            st.session_state.page = "login"
                            st.rerun()
                        else:
                            st.error(f"❌ 注册失败：{r.text}")
                    except requests.exceptions.ConnectionError:
                        st.error("❌ 无法连接到后端服务器。请确保后端服务正在运行（运行：uvicorn api.main:app --reload）")
                    except requests.exceptions.Timeout:
                        st.error("❌ 请求超时，请稍后重试")
                    except Exception as e:
                        st.error(f"❌ 发生错误：{str(e)}")
            st.markdown("<p style='text-align: center; color: #cbd5e1; margin-top: 1rem;'>* 必填字段</p>", unsafe_allow_html=True)

# ==================== 主应用界面 ====================
# 用户已登录，显示相应的主界面
else:
    # ==================== 患者界面 ====================
    if st.session_state.role == "patient":
        # 启动对话：如果是第一次进入，发送系统启动消息获取 AI 问候
        if not st.session_state.conversation_started:
            try:
                initial_greeting = {
                    "user_id": st.session_state.patient_username,
                    "message": "__SYSTEM_START__",
                    "token": st.session_state.token,
                }
                r = requests.post(f"{API}/chat", json=initial_greeting, timeout=10)
                if r.ok:
                    data = r.json()
                    st.session_state.chat_log.append(("MemoryCare", data["reply"]))
                    st.session_state.conversation_started = True
            except requests.exceptions.ConnectionError:
                st.error("❌ 无法连接到后端服务器。请确保后端服务正在运行。")
                st.info("💡 启动后端服务：在终端运行 `uvicorn api.main:app --reload --host 127.0.0.1 --port 8000`")
            except requests.exceptions.Timeout:
                st.warning("⏱️ 请求超时，请稍后重试")
            except Exception as e:
                st.error(f"❌ 启动对话失败：{str(e)}")
                print(f"Error starting conversation: {e}")
        
        col_left, col_right = st.columns([1, 2])
        
        with col_left:
            st.markdown("""
            <div class="custom-card">
                <div class="card-header">
                    <div class="card-icon icon-green">🎯</div>
                    <h3 class="card-title">您的目标</h3>
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
                st.info("🎯 还没有分配目标。您的医生很快就会为您设置一些目标！")
            
            st.markdown(f"""
            <div class="info-box">
                <div class="info-title">👋 欢迎，{st.session_state.patient_username}！</div>
                <div class="info-text">
                    我在这里与您聊天，提醒您服药，并帮助您
                    实现您的目标。让我们今天进行一次愉快的对话吧！
                </div>
            </div>
            """, unsafe_allow_html=True)
        # === 药物仪表板 ===
            st.markdown(f"""
            <div style="text-align: center; background: rgba(30, 27, 75, 0.6); padding: 1rem; border-radius: 12px; border: 1px solid rgba(147, 51, 234, 0.3); margin-bottom: 1rem;">
                <h3 style="color: #a855f7; margin: 0;">📅 {format_chinese_date(datetime.now())}</h3>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("""
            <div class="custom-card">
                <div class="card-header">
                    <div class="card-icon icon-blue">💊</div>
                    <h3 class="card-title">您的药物</h3>
                </div>
            </div>
            """, unsafe_allow_html=True)

            try:
                med_resp = requests.get(f"{API}/patient/medications", params={"token": st.session_state.token}, timeout=5)
                
                if med_resp.ok:
                    meds = med_resp.json().get("medications", [])
                    
                    if meds:
                        for m in meds:
                            st.markdown(f"**{m['name']}** — 每天 {m['times_per_day']} 次")
                            st.caption(f"🕒 {m['specific_times'] or '无指定时间'} | {m['instructions'] or ''}")

                            # 获取今天的日志 - 修复：正确解析日期
                            today_str = datetime.now().strftime("%Y-%m-%d")
                            taken_today = []
                            
                            for log in m['logs']:
                                # 从日志中提取日期部分（YYYY-MM-DD）
                                log_date = log['date'].split()[0] if ' ' in log['date'] else log['date']
                                if log_date == today_str and log.get('taken', True):
                                    taken_today.append(log)
                            
                            taken_count = len(taken_today)
                            remaining = m['times_per_day'] - taken_count
                            
                            # 如果所有剂量都已服用，禁用按钮
                            button_disabled = taken_count >= m['times_per_day']
                            button_text = f"✅ 已完成 ({taken_count}/{m['times_per_day']})" if button_disabled else f"✅ 服用 {m['name']}"
                            
                            if st.button(button_text, key=f"take_{m['name']}", disabled=button_disabled):
                                try:
                                    log_resp = requests.post(
                                        f"{API}/patient/medications/log",
                                        params={"token": st.session_state.token, "med_name": m["name"]},
                                        timeout=5
                                    )
                                    if log_resp.ok:
                                        st.success(f"已标记 {m['name']} 为已服用！")
                                        st.rerun()
                                    else:
                                        st.error(log_resp.json().get("detail", "记录药物失败"))
                                except requests.exceptions.ConnectionError:
                                    st.error("❌ 无法连接到后端服务器")
                                except Exception as e:
                                    st.error(f"❌ 记录失败：{str(e)}")

                            # 显示进度条
                            progress_value = taken_count / m['times_per_day'] if m['times_per_day'] > 0 else 0
                            st.progress(progress_value)
                            
                            if button_disabled:
                                st.caption(f"✅ 所有剂量已完成！({taken_count}/{m['times_per_day']})")
                            else:
                                st.caption(f"今天已服用 {taken_count}/{m['times_per_day']} 次 | 剩余 {remaining} 次")
                            
                            st.markdown("---")
                    else:
                        st.info("💊 还没有分配药物。")
                else:
                    st.error(f"获取药物信息失败：状态码 {med_resp.status_code}")
                    
            except requests.exceptions.ConnectionError:
                st.error("❌ 无法连接到后端服务器。请确保后端服务正在运行。")
            except requests.exceptions.Timeout:
                st.error("❌ 请求超时，请稍后重试")
            except Exception as e:
                st.error(f"❌ 加载药物失败：{str(e)}")


        with col_right:
            st.markdown("""
            <div class="custom-card">
                <div class="card-header">
                    <div class="card-icon icon-purple">💬</div>
                    <h3 class="card-title">与 MemoryCare 聊天</h3>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # 聊天容器，使用 Streamlit 原生聊天消息组件
            chat_container = st.container(height=450)
            
            with chat_container:
                if not st.session_state.chat_log:
                    st.markdown("""
                    <div style="display: flex; align-items: center; justify-content: center; height: 400px;">
                        <div style="text-align: center;">
                            <div style="font-size: 4rem; margin-bottom: 1rem;">💙</div>
                            <h3 style="color: #f1f5f9;">正在加载您的对话...</h3>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    for who, text in st.session_state.chat_log:
                        if who == "您":  # 用户消息标识
                            with st.chat_message("user", avatar="👤"):
                                st.write(text)
                        else:
                            # MemoryCare 助手的回复
                            with st.chat_message("assistant", avatar="💙"):
                                st.write(text)
            
            # 输入表单
            st.markdown("---")
            
            with st.form(key="chat_form", clear_on_submit=True):
                col_msg, col_btn = st.columns([4, 1])
                with col_msg:
                    msg = st.text_input("消息输入", key="chat_input", label_visibility="collapsed", placeholder="说点什么...")
                with col_btn:
                    send_btn = st.form_submit_button("📤 发送", use_container_width=True)
                
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
                    try:
                        r = requests.post(f"{API}/chat", json=payload, timeout=30)
                        if r.ok:
                            data = r.json()
                            st.session_state.chat_log.append(("您", msg))  # 用户消息，使用中文标识
                            st.session_state.chat_log.append(("MemoryCare", data["reply"]))  # AI 助手回复
                            try:
                                g_resp = requests.get(f"{API}/patient/goals", params={"token": st.session_state.token}, timeout=5)
                                if g_resp.ok:
                                    st.session_state.goals = g_resp.json().get("goals", [])
                            except:
                                pass  # 如果获取目标失败，不影响聊天
                            st.rerun()
                        else:
                            st.error(f"❌ 发送消息失败：{r.text}")
                    except requests.exceptions.ConnectionError:
                        st.error("❌ 无法连接到后端服务器。请确保后端服务正在运行。")
                    except requests.exceptions.Timeout:
                        st.error("❌ 请求超时，AI 响应时间较长，请稍后重试")
                    except Exception as e:
                        st.error(f"❌ 发送消息失败：{str(e)}")

    # ==================== 医生界面 ====================
    elif st.session_state.role == "doctor":
        st.markdown("""
        <div class="custom-card">
            <div class="card-header">
                <div class="card-icon icon-orange">👨‍⚕️</div>
                <h3 class="card-title">医生工作台</h3>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 获取所有患者
        try:
            patients_response = requests.get(f"{API}/doctor/patients", params={"token": st.session_state.token}, timeout=5)
            if patients_response.ok:
                patients_data = patients_response.json()
                all_patients = patients_data.get("patients", [])
            else:
                all_patients = []
        except requests.exceptions.ConnectionError:
            all_patients = []
            st.error("❌ 无法连接到后端服务器。请确保后端服务正在运行。")
        except requests.exceptions.Timeout:
            all_patients = []
            st.error("❌ 请求超时，请稍后重试")
        except Exception as e:
            all_patients = []
            st.error(f"❌ 获取患者列表失败：{str(e)}")
        
        st.markdown("<h3 style='color: #f1f5f9;'>选择要管理的患者</h3>", unsafe_allow_html=True)
        
        if all_patients:
            patient_options = ["-- 请选择患者 --"] + [f"{p['full_name']} ({p['username']})" for p in all_patients]
            patient_usernames = {f"{p['full_name']} ({p['username']})": p['username'] for p in all_patients}
            
            selected_patient = st.selectbox(
                "从已注册患者中选择：",
                options=patient_options,
                index=0,
                key="patient_selector"
            )
            
            if selected_patient != "-- 请选择患者 --":
                selected_username = patient_usernames[selected_patient]
                if st.button("✅ 选择此患者", use_container_width=True):
                    st.session_state.patient_username = selected_username
                    st.success(f"✅ 正在管理：**{selected_patient}**")
                    st.rerun()
        else:
            st.warning("⚠️ 系统中没有找到患者。患者需要先注册。")
            st.info("💡 提示：如果您知道用户名，仍然可以手动输入。")
        
        with st.expander("🔍 或手动输入患者用户名"):
            manual_username = st.text_input("患者用户名", placeholder="请手动输入患者用户名")
            if st.button("✅ 手动选择"):
                if manual_username:
                    st.session_state.patient_username = manual_username
                    st.success(f"✅ 正在管理：**{manual_username}**")
                    st.rerun()
                else:
                    st.error("请输入用户名")
        
        if st.session_state.patient_username:
            st.markdown(f"""
            <div class="info-box">
                <div class="info-title">当前管理</div>
                <div class="info-text">患者：<strong>{st.session_state.patient_username}</strong></div>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                <div class="custom-card">
                    <div class="card-header">
                        <div class="card-icon icon-green">🎯</div>
                        <h3 class="card-title">管理目标</h3>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # 获取患者目标
                try:
                    goals_response = requests.get(
                        f"{API}/doctor/patient-goals",
                        params={
                            "patient_username": st.session_state.patient_username,
                            "token": st.session_state.token
                        },
                        timeout=5
                    )
                    if goals_response.ok:
                        patient_goals = goals_response.json().get("goals", [])
                    else:
                        patient_goals = []
                except requests.exceptions.ConnectionError:
                    patient_goals = []
                    st.error("❌ 无法连接到后端服务器")
                except Exception as e:
                    patient_goals = []
                    st.error(f"❌ 获取目标失败：{str(e)}")

                # 显示目标状态标签页
                goal_tab1, goal_tab2 = st.tabs(["📝 分配新目标", "📊 目标状态"])

                with goal_tab1:
                    with st.form("add_goal"):
                        goal_text = st.text_area("目标描述", placeholder="例如：晚饭后散步 10 分钟", height=100)
                        ok = st.form_submit_button("➕ 分配目标", use_container_width=True)
                        if ok and goal_text:
                            try:
                                r = requests.post(
                                    f"{API}/doctor/goals",
                                    params={
                                        "patient_username": st.session_state.patient_username,
                                        "token": st.session_state.token,
                                    },
                                    json={"text": goal_text},
                                    timeout=5
                                )
                                if r.ok:
                                    st.success("🎯 目标分配成功！")
                                    st.rerun()
                                else:
                                    st.error(f"❌ {r.text}")
                            except requests.exceptions.ConnectionError:
                                st.error("❌ 无法连接到后端服务器")
                            except Exception as e:
                                st.error(f"❌ 分配目标失败：{str(e)}")

                with goal_tab2:
                    if patient_goals:
                        active_goals = [g for g in patient_goals if not g['completed']]
                        completed_goals = [g for g in patient_goals if g['completed']]
                        
                        # 显示活跃目标
                        st.markdown("<h4 style='color: #10b981;'>✅ 活跃目标</h4>", unsafe_allow_html=True)
                        if active_goals:
                            for g in active_goals:
                                st.markdown(f"""
                                <div class="goal-item">
                                    <span style="font-size: 1.5rem;">⭕</span>
                                    <span style="flex: 1; color: white; font-weight: 600;">{g['text']}</span>
                                    <span style="color: #e9d5ff; font-size: 0.9rem;">分配时间：{g['created_at'][:10]}</span>
                                </div>
                                """, unsafe_allow_html=True)
                        else:
                            st.info("还没有分配活跃目标。")
                        
                        st.markdown("---")
                        
                        # 显示已完成目标
                        st.markdown("<h4 style='color: #6b7280;'>🎉 已完成目标</h4>", unsafe_allow_html=True)
                        if completed_goals:
                            for g in completed_goals:
                                completed_date = g.get('completed_at_str', g.get('completed_at', '未知')[:10] if g.get('completed_at') else '未知')
                                st.markdown(f"""
                                <div class="goal-item goal-completed">
                                    <span style="font-size: 1.5rem;">✅</span>
                                    <span style="flex: 1; color: white; font-weight: 600;">{g['text']}</span>
                                    <span style="color: #d1d5db; font-size: 0.9rem;">完成时间：{completed_date}</span>
                                </div>
                                """, unsafe_allow_html=True)
                        else:
                            st.info("还没有完成的目标。")
                        
                        # 统计摘要
                        total_goals = len(patient_goals)
                        completion_rate = (len(completed_goals) / total_goals * 100) if total_goals > 0 else 0
                        
                        st.markdown(f"""
                        <div class="info-box" style="margin-top: 1rem;">
                            <div class="info-title">📈 目标进度摘要</div>
                            <div class="info-text">
                                总目标数：<strong>{total_goals}</strong> | 
                                活跃：<strong>{len(active_goals)}</strong> | 
                                已完成：<strong>{len(completed_goals)}</strong> | 
                                完成率：<strong>{completion_rate:.1f}%</strong>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.info("还没有分配目标。请使用'分配新目标'标签页创建一个。")
            
            with col2:
                st.markdown("""
                <div class="custom-card">
                    <div class="card-header">
                        <div class="card-icon icon-blue">💊</div>
                        <h3 class="card-title">添加药物</h3>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                with st.form("add_med"):
                    name = st.text_input("药物名称", placeholder="例如：阿司匹林")
                    tpd = st.number_input("每天次数", min_value=1, max_value=6, value=3)
                    times = st.text_input("具体时间 (时:分)", value="09:00,14:00,20:00")
                    instr = st.text_area("服用说明", value="与大量水一起服用。", height=80)
                    ok = st.form_submit_button("➕ 添加药物", use_container_width=True)
                    if ok and name:
                        try:
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
                                timeout=5
                            )
                            if r.ok:
                                st.success("💊 药物添加成功！")
                            else:
                                st.error(f"❌ {r.text}")
                        except requests.exceptions.ConnectionError:
                            st.error("❌ 无法连接到后端服务器")
                        except Exception as e:
                            st.error(f"❌ 添加药物失败：{str(e)}")
                
                st.markdown("""
                <div class="custom-card">
                    <div class="card-header">
                        <div class="card-icon icon-blue">📊</div>
                        <h3 class="card-title">药物状态</h3>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                try:
                    med_hist_resp = requests.get(
                        f"{API}/doctor/patient-medications",
                        params={"patient_username": st.session_state.patient_username, "token": st.session_state.token},
                        timeout=5
                    )
                    if med_hist_resp.ok:
                        meds = med_hist_resp.json().get("medications", [])
                        if meds:
                            for m in meds:
                                st.markdown(f"**{m['name']}** — 每天 {m['times_per_day']} 次 | {m['specific_times']}")
                                st.caption(f"📝 {m['instructions'] or ''}")

                                logs = m.get('logs', [])
                                recent_logs = [l for l in logs if l['date'] == datetime.now().strftime("%Y-%m-%d")]
                                taken_today = sum(1 for l in recent_logs if l['taken'])
                                st.progress(taken_today / m['times_per_day'])
                                st.caption(f"今天已服用 {taken_today}/{m['times_per_day']} 次")

                                with st.expander("📅 查看历史记录"):
                                    for l in logs[-10:]:
                                        st.write(f"{l['date']} — {'✅' if l['taken'] else '❌'} {l.get('time_taken', '')}")
                        else:
                            st.info("该患者没有找到药物。")
                    else:
                        st.error("获取药物历史记录失败。")
                except requests.exceptions.ConnectionError:
                    st.error("❌ 无法连接到后端服务器")
                except requests.exceptions.Timeout:
                    st.error("❌ 请求超时，请稍后重试")
                except Exception as e:
                    st.error(f"❌ 错误：{str(e)}")


        else:
            st.markdown("""
            <div style="text-align: center; padding: 3rem; background: rgba(30, 27, 75, 0.6); border-radius: 20px; border: 2px solid rgba(147, 51, 234, 0.3); margin-top: 2rem;">
                <div style="font-size: 4rem; margin-bottom: 1rem;">🏥</div>
                <h3 style="color: #f1f5f9;">请选择患者开始</h3>
                <p style="color: #cbd5e1;">请从上方下拉菜单中选择一个患者来管理他们的护理</p>
            </div>
            """, unsafe_allow_html=True)
