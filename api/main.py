# ~/memmachine-project/memorycare_app/api/main.py
import os, uuid, random, json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlmodel import select

from utils.db import create_db_and_tables, get_session
from utils.models import Patient, Medication, Goal, MedicationLog
from utils.auth import issue_doctor_token, issue_patient_token, whoami
from utils.memmachine_client import MemMachine
from utils.llm_client import chat
from utils.scheduler import next_due_window

load_dotenv()

app = FastAPI(title="MemoryCare API")
create_db_and_tables()
mm = MemMachine()

DEMENTIA_SYSTEM_PROMPT = """You are MemoryCare Assistant, a warm and compassionate AI companion designed to help people with memory challenges.

## Your Personality
- Friendly, encouraging, and naturally conversational
- Think of yourself as a caring friend, not a database
- Offer helpful thoughts and suggestions even when you don't have stored memories
- Be genuinely interested in the person and their life

## How to Use Memories
- When you have relevant stored memories, weave them naturally into conversation
- Use phrases like: "You mentioned..." or "I remember you told me..."
- CRITICAL: Only reference facts that are explicitly in the Memory Context below
- Never confuse this user with information about other people

## When You Don't Have Memories
- Still be helpful and conversational!
- Offer general advice, ask engaging questions, or make thoughtful suggestions
- Example: If asked about hiking without stored preferences, say something like:
  "A hike sounds wonderful! Fresh air and nature can be so refreshing. Do you have any favorite trails, or would you like suggestions for your area?"
- Don't just say "I don't have that information" - be a real companion

## Important Rules
- NEVER mix up user identities - only use memories from THIS user
- If Memory Context mentions other people (like "Jason likes pie"), that's information ABOUT Jason stored BY this user, not about this user themselves
- The user you're talking to is: {user_name}
- Keep responses warm, brief (2-4 sentences), and clear
- Never say "you forgot" or make the user feel bad about memory gaps

## Memory Context for {user_name}
{memory_context}

Remember: Be their companion, not just their memory bank. Even without stored memories, you can still be helpful, warm, and engaging.
"""

# ============================
#        SCHEMAS
# ============================

class DoctorLogin(BaseModel):
    username: str
    password: str

class PatientSignup(BaseModel):
    username: str
    password: str
    full_name: str
    family_info: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    hobbies: Optional[str] = None

class PatientLogin(BaseModel):
    username: str
    password: str

class MedicationIn(BaseModel):
    patient_username: str
    name: str
    times_per_day: int = 1
    specific_times: Optional[str] = None
    instructions: Optional[str] = None
    active: bool = True

class GoalIn(BaseModel):
    text: str

class ChatRequest(BaseModel):
    user_id: str
    message: str
    token: Optional[str] = None
    message_count: Optional[int] = 0
    medication_taken: Optional[Dict[str, Any]] = {}

class RememberRequest(BaseModel):
    user_id: str
    text: str

# HELPER FUNCTION FOR MEDICATION RESET #
def check_and_reset_medications(patient_id: int):
    """
    检查并重置药物状态
    
    此函数会检查患者的所有激活药物，如果药物的结束日期已过，
    则自动将药物标记为非激活状态。
    
    参数:
        patient_id: 患者数据库 ID（整数）
        
    工作流程:
        1. 获取患者所有激活的药物
        2. 检查每个药物的结束日期
        3. 如果结束日期早于今天，将 active 设为 False
        4. 提交更改到数据库
    """
    # 获取数据库会话（使用上下文管理器确保会话正确关闭）
    with get_session() as s:
        # 获取今天的日期（不包含时间部分）
        today = datetime.now().date()
        
        # 步骤 1: 查询患者所有激活的药物
        # 条件：患者 ID 匹配且药物处于激活状态
        meds = s.exec(select(Medication).where(
            Medication.patient_id == patient_id,  # 匹配患者 ID
            Medication.active == True  # 只查询激活的药物
        )).all()  # 获取所有匹配的记录
        
        # 步骤 2: 遍历每个药物，检查是否过期
        for med in meds:
            # 检查药物的结束日期
            # 如果药物有结束日期（end_date 不为 None）且结束日期早于今天
            if med.end_date and med.end_date.date() < today:
                # 将药物标记为非激活状态
                med.active = False
                # 将修改后的药物对象添加到会话（标记为需要更新）
                s.add(med)
        
        # 步骤 3: 提交所有更改到数据库
        # 这会将所有标记为需要更新的记录写入数据库
        s.commit()

# FILTER FUNCTION FOR MEMORY EXTRACTION AND ROUTING #
def extract_and_route_memories(user_id: str, user_message: str, assistant_reply: str) -> List[Dict[str, Any]]:
    """
    Extracts facts and determines which user they should be stored under.
    Returns list of {user_id, text, tags} to store.
    """
    
    routing_prompt = f"""You are analyzing a conversation to extract and route factual information.

                CRITICAL CONTEXT: 
                - The person speaking is: {user_id}
                - Extract ONLY facts about {user_id} or information {user_id} is sharing
                - Store everything from {user_id}'s first-person perspective

                RULES:
                1. Extract facts in FIRST-PERSON from {user_id}'s perspective
                2. If {user_id} mentions someone else (like "Jason likes pie"), store it as: "Jason likes pie" (it's {user_id}'s memory about Jason)
                3. ALWAYS route to {user_id} - this is {user_id}'s conversation
                4. DO NOT STORE if:
                - It's just a question
                - It's a greeting or small talk
                - The assistant is offering suggestions (don't store assistant's ideas as facts)

                CURRENT USER SPEAKING: {user_id}

                User ({user_id}) said: "{user_message}"
                Assistant replied: "{assistant_reply}"

                Output format (one per line):
                STORE_FOR:{user_id}|[category]|First-person fact
                NO_STORAGE (if nothing to store)

                Categories: personal, family, medical, preference, routine, memory, location

                Examples where user is "molly":
                - If molly says "I like hiking":
                STORE_FOR:molly|[preference]|I like hiking

                - If molly says "Jason likes to eat pie":
                STORE_FOR:molly|[memory]|Jason likes to eat pie
                (This is molly's knowledge about Jason, stored under molly)

                - If molly asks "should I go on a hike?":
                NO_STORAGE
                (Just a question, no facts to store)

                - If molly says "I need to find a place to hike":
                STORE_FOR:molly|[preference]|I like hiking
                (Implies molly likes hiking)

                Your extraction:"""

    try:
        # 步骤 1: 调用 LLM 分析对话，提取事实信息
        # 使用专门的系统提示词，指导 LLM 进行记忆路由分析
        extraction = chat(
            "You are a memory routing specialist.",  # 系统提示词：定义 LLM 角色
            [{"role": "user", "content": routing_prompt}]  # 用户消息：包含完整的路由提示词
        )
        
        # 步骤 2: 检查 LLM 是否返回 "NO_STORAGE"（表示没有需要存储的信息）
        # 转换为大写进行比较，避免大小写问题
        if "NO_STORAGE" in extraction.upper():
            return []  # 如果没有需要存储的信息，返回空列表
        
        # 步骤 3: 解析 LLM 返回的结构化数据
        memories_to_store = []  # 初始化存储列表
        # 将 LLM 返回的文本按行分割（每行代表一条记忆）
        for line in extraction.strip().split("\n"):
            # 去除每行的首尾空白字符
            line = line.strip()
            # 跳过空行或包含 "NO_STORAGE" 的行
            if not line or "NO_STORAGE" in line:
                continue
            
            # 步骤 4: 解析格式化的记忆行
            # 格式：STORE_FOR:user_id|[category]|fact_text
            if line.startswith("STORE_FOR:"):
                try:
                    # 使用 "|" 作为分隔符，最多分割成 3 部分
                    # parts[0]: "STORE_FOR:user_id"
                    # parts[1]: "[category]"
                    # parts[2]: "fact_text"
                    parts = line.split("|", 2)
                    print(f"[DEBUG] line: {line}, parts: {parts}")
                    
                    # 提取目标用户 ID：去除 "STORE_FOR:" 前缀并去除空白
                    target_user = parts[0].replace("STORE_FOR:", "").strip()
                    # 提取分类：去除方括号并去除空白
                    category = parts[1].strip().replace("[", "").replace("]", "")
                    # 提取事实文本：去除空白
                    fact = parts[2].strip()
                    
                    # 步骤 5: 验证事实文本的有效性
                    # 要求：非空且至少包含 3 个词（确保是有意义的事实）
                    if fact and len(fact.split()) >= 3:
                        # 将解析出的记忆添加到列表
                        print(f"[DEBUG] should_attempt_extraction() - fact: {fact}")
                        memories_to_store.append({
                            "user_id": target_user,  # 目标用户 ID
                            "text": fact,  # 事实文本（第一人称视角）
                            "category": category  # 记忆分类
                        })
                except Exception as e:
                    # 如果解析某行时出错，打印警告但继续处理其他行
                    print(f"[WARN] Failed to parse line: {line} | {e}")
                    continue  # 跳过当前行，继续处理下一行
        
        # 步骤 6: 返回所有成功解析的记忆列表
        print(f"[DEBUG] memories_to_store: {memories_to_store}")
        return memories_to_store
        
    except Exception as e:
        # 如果整个提取过程出错（如 LLM 调用失败），记录错误并返回空列表
        print(f"[ERROR] Memory routing failed: {e}")
        return []  # 返回空列表，不影响主流程
    

def should_attempt_extraction(message: str) -> bool:
    """
    Quick heuristic to decide if message might contain storable information.
    Avoids expensive LLM calls for obvious questions and small talk.
    
    Returns True if message likely contains facts worth storing.
    Returns False for questions, greetings, or brief responses.
    """
    message_lower = message.lower().strip()
    
    # 1. Filter out very short messages (unlikely to contain meaningful info)
    word_count = len(message.split())
    #if word_count < 3:
    #    print(f"[DEBUG] should_attempt_extraction() - word_count < 3: {word_count}")
    #    return False
    
    # 2. Filter out questions - these are requests for information, not statements of fact
    question_words = [
        # English question words
        "what", "who", "when", "where", "why", "how",
        "which", "whose", "whom",
        "do you", "can you", "could you", "would you", "will you",
        "should you", "are you", "is there", "did you",
        "tell me", "show me", "help me", "explain",
        # Chinese question words (中文疑问词)
        "什么", "谁", "何时", "哪里", "为什么", "怎么", "怎样",
        "哪个", "哪些", "谁的",
        "你能", "你会", "你能告诉我", "你能帮我", "你能", "你会",
        "告诉我", "给我看", "帮我", "解释一下", "解释",
        "请问", "问一下", "想知道", "想了解"
    ]
    
    if any(message_lower.startswith(q) for q in question_words):
        print(f"[DEBUG] question_words return False")
        return False
    
    if message.endswith("?"):
        print(f"[DEBUG] message.endswith('?') return False")
        return False
    
    # 3. Filter out greetings and social pleasantries
    greetings = [
        # English greetings
        "hello", "hi ", "hi,", "hey", "hey there",
        "good morning", "good afternoon", "good evening", "good night",
        "thanks", "thank you", "thank", "thx",
        "ok", "okay", "sure", "yes", "no", "yeah", "yep", "nope",
        "bye", "goodbye", "see you", "talk later",
        # Chinese greetings (中文问候语)
        "你好", "您好", "早上好", "下午好", "晚上好", "晚安",
        "谢谢", "多谢", "感谢",
        "好的", "可以", "行", "是的", "不是", "对", "不对",
        "再见", "拜拜", "回头见", "待会见"
    ]
    
    if any(message_lower.startswith(g) for g in greetings):
        print(f"[DEBUG] greetings return False")
        return False
    
    # 4. Filter out system/meta requests
    meta_requests = [
        # English meta requests
        "clear", "delete", "reset", "forget",
        "remember this", "save this", "store this",  # explicit commands handled differently
        # Chinese meta requests (中文系统请求)
        "清除", "删除", "重置", "忘记",
        "记住这个", "保存这个", "存储这个"
    ]
    
    if any(meta in message_lower for meta in meta_requests):
        print(f"[DEBUG] meta_requests return False")
        return False
    
    # 5. POSITIVE SIGNALS - Strong indicators of factual information
    info_indicators = [
        # Identity and personal info
        "i am", "i'm", "my name is", "i was born", "i live in",
        # Chinese: 身份和个人信息
        "我是", "我叫", "我出生", "我住在", "我来自",
        
        # Preferences and opinions
        "i like", "i love", "i enjoy", "i prefer", "i hate", "i don't like",
        "my favorite", "i want", "i need",
        # Chinese: 偏好和观点
        "我喜欢", "我爱", "我享受", "我更喜欢", "我讨厌", "我不喜欢",
        "我最喜欢", "我想要", "我需要",
        
        # Relationships and family
        "my ", "my wife", "my husband", "my son", "my daughter",
        "my brother", "my sister", "my friend", "my mother", "my father",
        # Chinese: 关系和家庭
        "我的", "我妻子", "我丈夫", "我儿子", "我女儿",
        "我兄弟", "我姐妹", "我朋友", "我母亲", "我父亲", "我妈妈", "我爸爸",
        
        # Activities and routines
        "i work", "i go to", "i take", "i eat", "i drink", "i play",
        "i watch", "i read", "i listen", "i exercise",
        "every day", "every morning", "every night", "usually",
        # Chinese: 活动和日常
        "我工作", "我去", "我吃", "我喝", "我玩", "我看", "我读", "我听", "我锻炼",
        "每天", "每天早上", "每天晚上", "通常", "经常",
        
        # Medical and health (important for dementia care)
        "i have", "i take medication", "my doctor", "i'm allergic",
        # Chinese: 医疗和健康
        "我有", "我吃药", "我服药", "我的医生", "我过敏",
        
        # Past experiences and memories
        "i used to", "i remember", "i grew up", "when i was",
        "i worked at", "i went to", "i met",
        # Chinese: 过去的经历和记忆
        "我以前", "我记得", "我长大", "当我", "我在", "我去过", "我见过"
    ]
    
    if any(indicator in message_lower for indicator in info_indicators):
        print(f"[DEBUG] ****** info_indicators return True")
        return True
    
    # 6. Check for proper nouns (names, places) - often indicates factual content
    # Simple heuristic: words that start with capital letters (excluding first word)
    words = message.split()
    if len(words) > 1:
        capitalized_count = sum(1 for word in words[1:] if word and word[0].isupper())
        if capitalized_count >= 1:  # Has at least one proper noun
            print(f"proper nouns return True")
            return True
    
    # 7. Default behavior for medium-length declarative statements
    # If it's 5+ words and doesn't match filters above, might be worth checking
    if word_count >= 5 and not message.endswith("?"):
        print(f"[DEBUG] word_count >= 5 and not message.endswith('?') return True")
        return True
    
    # 8. Default: don't extract (be conservative to save API calls)
    print(f"[DEBUG] default return False")
    return False

# ============================
#        ROUTES
# ============================

# FASTAPI routes #
@app.get("/health")
def health() -> Dict[str, Any]:
    """
    健康检查端点
    
    用于检查 API 服务器和 MemMachine 服务的运行状态。
    通常用于监控、负载均衡器健康检查或系统诊断。
    
    返回:
        Dict[str, Any]: 包含以下字段的字典：
            - ok (bool): 操作是否成功
            - memmachine: MemMachine 服务的健康状态信息
    
    异常:
        HTTPException(500): 如果 MemMachine 服务不可用或发生其他错误
    
    示例响应:
        {
            "ok": True,
            "memmachine": {
                "status": "healthy",
                ...
            }
        }
    """
    try:
        return {"ok": True, "memmachine": mm.health()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------------------- AUTH --------------------
@app.post("/auth/doctor/login")
def doctor_login(payload: DoctorLogin):
    """
    医生登录端点
    
    验证医生凭证并颁发认证 Token。目前仅支持硬编码的医生账户。
    
    参数:
        payload (DoctorLogin): 包含以下字段的请求体：
            - username (str): 医生用户名（当前仅支持 "doctor"）
            - password (str): 医生密码（当前仅支持 "doctor"）
    
    返回:
        Dict[str, Any]: 包含以下字段的字典：
            - ok (bool): 操作是否成功
            - token (str): 认证 Token，用于后续 API 调用的身份验证
            - role (str): 用户角色，固定为 "doctor"
    
    异常:
        HTTPException(401): 如果用户名或密码不正确
    
    注意:
        - Token 有效期为 8 小时
        - Token 格式：以 "doc_" 开头的随机字符串
        - 生产环境应使用更安全的认证机制（如 JWT + 密码哈希）
    
    示例请求:
        POST /auth/doctor/login
        {
            "username": "doctor",
            "password": "doctor"
        }
    
    示例响应:
        {
            "ok": True,
            "token": "doc_abc123...",
            "role": "doctor"
        }
    """
    token = issue_doctor_token(payload.username, payload.password)
    if not token:
        raise HTTPException(401, "Invalid doctor credentials")
    return {"ok": True, "token": token, "role": "doctor"}

@app.post("/auth/patient/signup")
def patient_signup(payload: PatientSignup):
    """
    患者注册端点
    
    创建新患者账户，将信息存储到数据库和 MemMachine。
    同时创建情景记忆（注册事件）和档案记忆（个人信息）。
    """
    # 步骤 1: 检查用户名是否已存在
    with get_session() as s:
        # 查询数据库中是否已有相同用户名的患者
        existing = s.exec(select(Patient).where(Patient.username == payload.username)).first()
        # 如果用户名已存在，返回 409 冲突错误
        if existing:
            raise HTTPException(409, "Username already exists")
        
        # 步骤 2: 创建新患者记录
        # 使用请求数据创建 Patient 对象
        p = Patient(
            username=payload.username,  # 用户名（唯一标识）
            password=payload.password,  # 密码（注意：生产环境应使用哈希加密）
            full_name=payload.full_name,  # 全名
            family_info=payload.family_info,  # 家庭信息（可选）
            emergency_contact_name=payload.emergency_contact_name,  # 紧急联系人姓名（可选）
            emergency_contact_phone=payload.emergency_contact_phone,  # 紧急联系人电话（可选）
            hobbies=payload.hobbies,  # 兴趣爱好（可选）
        )
        # 将新患者添加到数据库会话
        s.add(p)
        # 提交事务，将数据写入数据库
        s.commit()

    # 步骤 3: 为患者颁发认证 Token
    # Token 用于后续 API 调用的身份验证
    token = issue_patient_token(payload.username)

    # 步骤 4: 准备记忆数据
    # 情景记忆：记录注册事件（临时性记忆）
    episodic_text = (
        f"{payload.full_name} signed up for MemoryCare on {datetime.now().strftime('%Y-%m-%d')}."
    )
    
    # 档案记忆：存储个人信息（永久性记忆）
    # 使用 or 运算符提供默认值，确保所有字段都有值
    profile_data = {
        "full_name": payload.full_name,  # 全名
        "family_info": payload.family_info or "Not provided",  # 家庭信息，如果为空则使用默认文本
        "emergency_contact_name": payload.emergency_contact_name or "Not provided",  # 紧急联系人姓名
        "emergency_contact_phone": payload.emergency_contact_phone or "Not provided",  # 紧急联系人电话
        "hobbies": payload.hobbies or "Not shared",  # 兴趣爱好
        "category": "personal_info"  # 分类标记，用于记忆组织
    }
    
    # 步骤 5: 如果有紧急联系人信息，单独存储一条合并的档案记忆
    # 这样可以在需要时快速检索紧急联系人信息
    if payload.emergency_contact_name:
        profile_data["emergency_contact_name"] = payload.emergency_contact_name
    if payload.emergency_contact_phone:
        profile_data["emergency_contact_phone"] = payload.emergency_contact_phone
        # 存储合并的紧急联系人信息到档案记忆
        # 格式："{姓名} - Phone: {电话}"
        mm.remember_profile(
            user_id=payload.username,  # 用户 ID
            key="emergency_contact",  # 记忆键名
            value=f"{payload.emergency_contact_name or 'Unknown'} - Phone: {payload.emergency_contact_phone}",  # 合并的值
            category="emergency_info"  # 分类为紧急信息
        )
    
    # 步骤 6: 同时存储情景记忆和档案记忆
    # store_dual_memory 会同时调用 remember() 和 remember_profile()
    mm.store_dual_memory(
        user_id=payload.username,  # 用户 ID
        episodic_text=episodic_text,  # 情景记忆文本
        profile_data=profile_data,  # 档案记忆数据
        tags=["signup", "profile_creation"]  # 标签，用于记忆分类和检索
    )
    
    # 步骤 7: 返回成功响应，包含 Token 和角色信息
    return {"ok": True, "token": token, "role": "patient"}

@app.post("/auth/patient/login")
def patient_login(payload: PatientLogin):
    """
    患者登录端点
    
    验证患者凭证，记录登录事件到记忆系统，并颁发认证 Token。
    
    参数:
        payload (PatientLogin): 包含以下字段的请求体：
            - username (str): 患者用户名（注册时创建的唯一标识符）
            - password (str): 患者密码（注意：当前为明文比较，生产环境应使用哈希）
    
    返回:
        Dict[str, Any]: 包含以下字段的字典：
            - ok (bool): 操作是否成功
            - token (str): 认证 Token，用于后续 API 调用的身份验证
            - role (str): 用户角色，固定为 "patient"
    
    异常:
        HTTPException(401): 如果用户名不存在或密码不正确
    
    工作流程:
        1. 从数据库查询患者记录
        2. 验证用户名和密码
        3. 将登录事件记录到 MemMachine 情景记忆
        4. 颁发认证 Token
        5. 返回 Token 和角色信息
    
    注意:
        - Token 有效期为 8 小时
        - Token 格式：以 "pat_" 开头的随机字符串
        - 登录事件会自动存储到记忆系统，用于追踪患者活动
        - 生产环境应使用密码哈希（如 bcrypt）而不是明文比较
    
    示例请求:
        POST /auth/patient/login
        {
            "username": "patient123",
            "password": "password123"
        }
    
    示例响应:
        {
            "ok": True,
            "token": "pat_xyz789...",
            "role": "patient"
        }
    """
    with get_session() as s:
        p = s.exec(select(Patient).where(Patient.username == payload.username)).first()
        if not p or p.password != payload.password:
            raise HTTPException(401, "Invalid credentials")
    mm.remember(
        user_id=payload.username,
        text=f"Patient logged in on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        tags=["login", "activity"]
    )
    token = issue_patient_token(payload.username)
    return {"ok": True, "token": token, "role": "patient"}

# -------------------- DOCTOR ROUTES --------------------
@app.get("/doctor/patients")
def list_patients(token: str = Query(...)):
    """
    获取所有患者列表端点（医生专用）
    
    返回系统中所有已注册患者的简要信息列表。
    仅限医生角色访问，用于医生选择要管理的患者。
    
    参数:
        token (str): 医生认证 Token，通过查询参数传递
                    格式：Query(...) 表示必填参数
    
    返回:
        Dict[str, Any]: 包含以下字段的字典：
            - ok (bool): 操作是否成功
            - patients (List[Dict]): 患者列表，每个患者包含：
                - username (str): 患者用户名
                - full_name (str): 患者全名
                - id (int): 患者数据库 ID
    
    异常:
        HTTPException(401): 如果 Token 无效或用户不是医生角色
    
    用途:
        - 医生界面显示患者下拉列表
        - 医生选择要管理的患者
        - 患者管理功能
    
    注意:
        - 返回所有患者，不进行分页（如果患者数量很大，应考虑添加分页）
        - 仅返回基本信息，不包含敏感信息（如密码）
    
    示例请求:
        GET /doctor/patients?token=doc_abc123...
    
    示例响应:
        {
            "ok": True,
            "patients": [
                {
                    "username": "patient1",
                    "full_name": "张三",
                    "id": 1
                },
                {
                    "username": "patient2",
                    "full_name": "李四",
                    "id": 2
                }
            ]
        }
    """
    info = whoami(token)
    if not info or info["role"] != "doctor":
        raise HTTPException(401, "Doctor auth required")
    with get_session() as s:
        patients = s.exec(select(Patient)).all()
        return {"ok": True, "patients": [{"username": p.username, "full_name": p.full_name, "id": p.id} for p in patients]}

@app.post("/doctor/medications")
def add_med(payload: MedicationIn, token: str = Query(...), duration_days: int = Query(7)):
    """
    添加药物端点（医生专用）
    
    医生为指定患者添加新的药物处方。系统会：
    1. 验证医生身份
    2. 检查患者是否存在
    3. 检查是否已有同名的激活药物（防止重复）
    4. 创建药物记录
    5. 将药物信息存储到记忆系统（情景记忆和档案记忆）
    
    参数:
        payload (MedicationIn): 包含以下字段的请求体：
            - patient_username (str): 患者用户名
            - name (str): 药物名称（如 "阿司匹林"）
            - times_per_day (int): 每天服用次数（如 3 表示每天 3 次）
            - specific_times (str): 具体服用时间，逗号分隔（如 "09:00,14:00,20:00"）
            - instructions (str): 服用说明（如 "饭后服用"、"用水送服"）
            - active (bool): 是否激活（True 表示正在服用）
        token (str): 医生认证 Token，通过查询参数传递
        duration_days (int): 药物持续时间（天数），默认 7 天，通过查询参数传递
    
    返回:
        Dict[str, Any]: 包含以下字段的字典：
            - ok (bool): 操作是否成功
            - message (str): 成功消息
    
    异常:
        HTTPException(401): 如果 Token 无效或用户不是医生角色
        HTTPException(404): 如果患者不存在
        HTTPException(400): 如果已存在同名的激活药物
    
    工作流程:
        1. 验证医生身份
        2. 查询患者记录
        3. 检查是否已有同名激活药物（防止重复添加）
        4. 创建 Medication 记录（自动设置 start_date 和 created_at）
        5. 将药物信息存储到记忆系统：
           - 情景记忆：记录医生添加药物的事件
           - 档案记忆：存储药物信息作为永久性医疗记录
    
    注意:
        - 药物名称会自动转换为小写并替换空格为下划线作为档案记忆的键名
        - 药物信息会永久存储到患者的档案记忆中，供 AI 助手参考
        - 如果患者已有同名激活药物，会拒绝添加新记录
    
    示例请求:
        POST /doctor/medications?token=doc_abc123...&duration_days=30
        {
            "patient_username": "patient1",
            "name": "阿司匹林",
            "times_per_day": 3,
            "specific_times": "09:00,14:00,20:00",
            "instructions": "饭后服用，用水送服",
            "active": true
        }
    
    示例响应:
        {
            "ok": True,
            "message": "Medication added"
        }
    """
    info = whoami(token)
    if not info or info["role"] != "doctor":
        raise HTTPException(401, "Doctor auth required")
    start = datetime.now()
    end = start + timedelta(days=duration_days)
    
    with get_session() as s:
        patient = s.exec(select(Patient).where(Patient.username == payload.patient_username)).first()
        if not patient:
            raise HTTPException(404, "Patient not found")
        existing = s.exec(select(Medication).where(
            Medication.patient_id == patient.id,
            Medication.name == payload.name,
            Medication.active == True
        )).first()

        if existing:
            raise HTTPException(400, f"Active medication '{payload.name}' already exists")
        
        med = Medication(
            patient_id=patient.id,
            name=payload.name,
            times_per_day=payload.times_per_day,
            specific_times=payload.specific_times,
            instructions=payload.instructions,
            active=payload.active,
        )
        s.add(med)
        s.commit()
    episodic_text = f"Doctor added new medication '{payload.name}' on {datetime.now().strftime('%Y-%m-%d')}."
    profile_data = {
        f"medication_{payload.name.lower().replace(' ', '_')}": f"{payload.name} - {payload.times_per_day}x daily at {payload.specific_times}",
        "category": "medical_info"
    }
    mm.store_dual_memory(
        user_id=payload.patient_username,
        episodic_text=episodic_text,
        profile_data=profile_data,
        tags=["medication", "doctor_action"]
    )
    return {"ok": True, "message": "Medication added"}

@app.get("/doctor/patient-goals")
def get_patient_goals(patient_username: str = Query(...), token: str = Query(...)):
    """
    获取患者目标列表端点（医生专用）
    
    返回指定患者的所有目标（包括已完成和未完成的），用于医生查看患者的治疗进度。
    
    参数:
        patient_username (str): 患者用户名，通过查询参数传递
        token (str): 医生认证 Token，通过查询参数传递
    
    返回:
        Dict[str, Any]: 包含以下字段的字典：
            - ok (bool): 操作是否成功
            - goals (List[Dict]): 目标列表，每个目标包含：
                - id (int): 目标 ID
                - patient_id (int): 患者 ID
                - text (str): 目标描述文本
                - completed (bool): 是否已完成
                - created_at (datetime): 创建时间
                - completed_at (datetime): 完成时间（如果已完成）
                - completed_at_str (str): 完成时间的格式化字符串（用于前端显示）
    
    异常:
        HTTPException(401): 如果 Token 无效或用户不是医生角色
        HTTPException(404): 如果患者不存在
    
    用途:
        - 医生界面显示患者的所有目标
        - 查看目标完成情况
        - 评估患者康复进度
    
    注意:
        - 返回所有目标（包括已完成和未完成）
        - completed_at_str 字段是为了方便前端显示而添加的格式化字符串
        - 如果目标未完成，completed_at_str 为 None
    
    示例请求:
        GET /doctor/patient-goals?patient_username=patient1&token=doc_abc123...
    
    示例响应:
        {
            "ok": True,
            "goals": [
                {
                    "id": 1,
                    "patient_id": 1,
                    "text": "每天散步 30 分钟",
                    "completed": false,
                    "created_at": "2024-01-01T10:00:00",
                    "completed_at": null,
                    "completed_at_str": null
                },
                {
                    "id": 2,
                    "patient_id": 1,
                    "text": "完成记忆训练",
                    "completed": true,
                    "created_at": "2024-01-01T10:00:00",
                    "completed_at": "2024-01-05T15:30:00",
                    "completed_at_str": "2024-01-05 15:30"
                }
            ]
        }
    """
    info = whoami(token)
    if not info or info["role"] != "doctor":
        raise HTTPException(401, "Doctor auth required")
    with get_session() as s:
        patient = s.exec(select(Patient).where(Patient.username == patient_username)).first()
        if not patient:
            raise HTTPException(404, "Patient not found")
        all_goals = s.exec(select(Goal).where(Goal.patient_id == patient.id)).all()
        return {"ok": True, "goals": [
            {**g.model_dump(), "completed_at_str": g.completed_at.strftime("%Y-%m-%d %H:%M") if g.completed_at else None}
            for g in all_goals
        ]}

@app.get("/doctor/patient-medications")
def doctor_view_meds(patient_username: str = Query(...), token: str = Query(...)):
    """
    获取患者药物列表及服用历史端点（医生专用）
    
    返回指定患者的所有药物信息及其服用历史记录，用于医生监控患者的服药依从性。
    
    参数:
        patient_username (str): 患者用户名，通过查询参数传递
        token (str): 医生认证 Token，通过查询参数传递
    
    返回:
        Dict[str, Any]: 包含以下字段的字典：
            - ok (bool): 操作是否成功
            - medications (List[Dict]): 药物列表，每个药物包含：
                - name (str): 药物名称
                - times_per_day (int): 每天服用次数
                - specific_times (str): 具体服用时间
                - instructions (str): 服用说明
                - logs (List[Dict]): 服用历史记录列表，每条记录包含：
                    - date (str): 日期（格式：YYYY-MM-DD）
                    - time_taken (str): 实际服用时间（格式：HH:MM）
                    - taken (bool): 是否已服用
    
    异常:
        HTTPException(401): 如果 Token 无效或用户不是医生角色
        HTTPException(404): 如果患者不存在
    
    用途:
        - 医生查看患者的所有药物（包括已停用的）
        - 监控患者服药依从性
        - 分析服药历史数据
        - 评估治疗效果
    
    注意:
        - 返回所有药物（包括激活和已停用的）
        - 每条药物都包含完整的服用历史记录
        - 日期格式化为字符串以便前端显示
        - 如果药物没有服用记录，logs 为空列表
    
    示例请求:
        GET /doctor/patient-medications?patient_username=patient1&token=doc_abc123...
    
    示例响应:
        {
            "ok": True,
            "medications": [
                {
                    "name": "阿司匹林",
                    "times_per_day": 3,
                    "specific_times": "09:00,14:00,20:00",
                    "instructions": "饭后服用",
                    "logs": [
                        {
                            "date": "2024-01-10",
                            "time_taken": "09:15",
                            "taken": true
                        },
                        {
                            "date": "2024-01-10",
                            "time_taken": "14:30",
                            "taken": true
                        },
                        {
                            "date": "2024-01-10",
                            "time_taken": null,
                            "taken": false
                        }
                    ]
                }
            ]
        }
    """
    info = whoami(token)
    if not info or info["role"] != "doctor":
        raise HTTPException(401, "Doctor auth required")
    with get_session() as s:
        patient = s.exec(select(Patient).where(Patient.username == patient_username)).first()
        if not patient:
            raise HTTPException(404, "Patient not found")
        meds = s.exec(select(Medication).where(Medication.patient_id == patient.id)).all()
        data = []
        for m in meds:
            logs = s.exec(select(MedicationLog).where(MedicationLog.medication_id == m.id)).all()
            data.append({
                "name": m.name,
                "times_per_day": m.times_per_day,
                "specific_times": m.specific_times,
                "instructions": m.instructions,
                "logs": [{"date": l.date.strftime("%Y-%m-%d"), "time_taken": l.time_taken, "taken": l.taken} for l in logs]
            })
        return {"ok": True, "medications": data}
    
@app.post("/doctor/goals")
def add_goal(payload: GoalIn, patient_username: str = Query(...), token: str = Query(...)):
    """
    添加目标端点（医生专用）
    
    医生为指定患者分配新的治疗目标或康复目标。系统会：
    1. 验证医生身份
    2. 检查患者是否存在
    3. 创建目标记录
    4. 将目标信息存储到记忆系统（情景记忆和档案记忆）
    
    参数:
        payload (GoalIn): 包含以下字段的请求体：
            - text (str): 目标描述文本（如 "每天散步 30 分钟"、"完成记忆训练"）
        patient_username (str): 患者用户名，通过查询参数传递
        token (str): 医生认证 Token，通过查询参数传递
    
    返回:
        Dict[str, Any]: 包含以下字段的字典：
            - ok (bool): 操作是否成功
            - message (str): 成功消息
    
    异常:
        HTTPException(401): 如果 Token 无效或用户不是医生角色
        HTTPException(404): 如果患者不存在
    
    工作流程:
        1. 验证医生身份
        2. 查询患者记录
        3. 创建 Goal 记录（自动设置 created_at，completed 默认为 False）
        4. 将目标信息存储到记忆系统：
           - 情景记忆：记录医生分配目标的事件
           - 档案记忆：存储目标作为活跃目标（使用时间戳作为键名的一部分）
    
    注意:
        - 新创建的目标默认为未完成状态（completed=False）
        - 目标会永久存储到患者的档案记忆中
        - 档案记忆的键名包含时间戳，确保每个目标都有唯一标识
        - AI 助手可以根据这些目标提供个性化的提醒和鼓励
    
    示例请求:
        POST /doctor/goals?patient_username=patient1&token=doc_abc123...
        {
            "text": "每天晚饭后散步 10 分钟"
        }
    
    示例响应:
        {
            "ok": True,
            "message": "Goal assigned"
        }
    """
    info = whoami(token)
    if not info or info["role"] != "doctor":
        raise HTTPException(401, "Doctor auth required")

    with get_session() as s:
        patient = s.exec(select(Patient).where(Patient.username == patient_username)).first()
        if not patient:
            raise HTTPException(404, "Patient not found")
        goal = Goal(patient_id=patient.id, text=payload.text)
        s.add(goal)
        s.commit()
    
    # EPISODIC MEMORY: Record goal assignment
    episodic_text = f"Doctor assigned new goal on {datetime.now().strftime('%Y-%m-%d')}: {payload.text}"
    
    # PROFILE MEMORY: Store as active goal
    profile_data = {
        f"active_goal_{datetime.now().strftime('%Y%m%d_%H%M%S')}": payload.text,
        "category": "goals"
    }
    
    mm.store_dual_memory(
        user_id=patient_username,
        episodic_text=episodic_text,
        profile_data=profile_data,
        tags=["goal", "doctor_action"]
    )
    
    return {"ok": True, "message": "Goal assigned"}


# -------------------- PATIENT ROUTES --------------------
@app.get("/patient/goals")
def list_goals(token: str = Query(...)):
    """
    获取患者目标列表端点（患者专用）
    
    返回当前登录患者的所有未完成目标，用于患者界面显示。
    
    参数:
        token (str): 患者认证 Token，通过查询参数传递
    
    返回:
        Dict[str, Any]: 包含以下字段的字典：
            - ok (bool): 操作是否成功
            - goals (List[Dict]): 未完成目标列表，每个目标包含：
                - id (int): 目标 ID
                - patient_id (int): 患者 ID
                - text (str): 目标描述文本
                - completed (bool): 是否已完成（固定为 False，因为只返回未完成的）
                - created_at (datetime): 创建时间
                - completed_at (datetime): 完成时间（固定为 None）
    
    异常:
        HTTPException(401): 如果 Token 无效或用户不是患者角色
    
    用途:
        - 患者界面显示当前活跃的目标
        - 患者查看需要完成的任务
        - 激励患者完成目标
    
    注意:
        - 只返回未完成的目标（completed=False）
        - 已完成的目标不会显示给患者
        - 使用 model_dump() 将 SQLModel 对象转换为字典
    
    示例请求:
        GET /patient/goals?token=pat_xyz789...
    
    示例响应:
        {
            "ok": True,
            "goals": [
                {
                    "id": 1,
                    "patient_id": 1,
                    "text": "每天散步 30 分钟",
                    "completed": false,
                    "created_at": "2024-01-01T10:00:00",
                    "completed_at": null
                },
                {
                    "id": 3,
                    "patient_id": 1,
                    "text": "完成记忆训练",
                    "completed": false,
                    "created_at": "2024-01-05T10:00:00",
                    "completed_at": null
                }
            ]
        }
    """
    me = whoami(token)
    if not me or me["role"] != "patient":
        raise HTTPException(401, "Patient auth required")
    with get_session() as s:
        p = s.exec(select(Patient).where(Patient.username == me["username"])).first()
        goals = s.exec(select(Goal).where(Goal.patient_id == p.id, Goal.completed == False)).all()
        return {"ok": True, "goals": [g.model_dump() for g in goals]}

@app.get("/patient/medications")
def list_medications(token: str = Query(...)):
    """
    获取患者药物列表端点（患者专用）
    
    返回当前登录患者的所有激活药物及其服用历史记录。
    在返回前会自动检查并重置过期的药物状态。
    
    参数:
        token (str): 患者认证 Token，通过查询参数传递
    
    返回:
        Dict[str, Any]: 包含以下字段的字典：
            - ok (bool): 操作是否成功
            - medications (List[Dict]): 激活药物列表，每个药物包含：
                - name (str): 药物名称
                - times_per_day (int): 每天服用次数
                - specific_times (str): 具体服用时间
                - instructions (str): 服用说明
                - logs (List[Dict]): 服用历史记录列表，每条记录包含：
                    - date (str): 日期（格式：YYYY-MM-DD）
                    - time_taken (str): 实际服用时间（格式：HH:MM）
                    - taken (bool): 是否已服用
    
    异常:
        HTTPException(401): 如果 Token 无效或用户不是患者角色
    
    工作流程:
        1. 验证患者身份
        2. 查询患者记录
        3. 检查并重置过期的药物状态（调用 check_and_reset_medications）
        4. 查询所有激活的药物
        5. 为每个药物查询服用历史记录
        6. 返回格式化后的药物列表
    
    用途:
        - 患者界面显示当前需要服用的药物
        - 显示药物服用进度
        - 患者查看服药历史
    
    注意:
        - 只返回激活的药物（active=True）
        - 已停用的药物不会显示
        - 会自动检查并重置过期的药物（如果 end_date 已过，会设置为 inactive）
        - 日期格式化为字符串以便前端显示
    
    示例请求:
        GET /patient/medications?token=pat_xyz789...
    
    示例响应:
        {
            "ok": True,
            "medications": [
                {
                    "name": "阿司匹林",
                    "times_per_day": 3,
                    "specific_times": "09:00,14:00,20:00",
                    "instructions": "饭后服用",
                    "logs": [
                        {
                            "date": "2024-01-10",
                            "time_taken": "09:15",
                            "taken": true
                        },
                        {
                            "date": "2024-01-10",
                            "time_taken": "14:30",
                            "taken": true
                        }
                    ]
                }
            ]
        }
    """
    me = whoami(token)
    if not me or me["role"] != "patient":
        raise HTTPException(401, "Patient auth required")
    with get_session() as s:
        patient = s.exec(select(Patient).where(Patient.username == me["username"])).first()
        check_and_reset_medications(patient.id)
        meds = s.exec(select(Medication).where(Medication.patient_id == patient.id, Medication.active == True)).all()
        result = []
        for m in meds:
            logs = s.exec(select(MedicationLog).where(MedicationLog.medication_id == m.id)).all()
            result.append({
                "name": m.name,
                "times_per_day": m.times_per_day,
                "specific_times": m.specific_times,
                "instructions": m.instructions,
                "logs": [{"date": l.date.strftime("%Y-%m-%d"), "time_taken": l.time_taken, "taken": l.taken} for l in logs]
            })
        return {"ok": True, "medications": result}

@app.post("/patient/medications/log")
def log_medication(med_name: str = Query(...), token: str = Query(...)):
    """
    记录药物服用端点
    
    患者标记某个药物已服用，系统会：
    1. 验证患者身份
    2. 检查药物是否存在且激活
    3. 检查今日是否已记录足够次数（防止重复记录）
    4. 创建服用日志
    5. 将事件存储到记忆系统
    """
    # 步骤 1: 验证患者身份
    # whoami() 函数根据 Token 返回用户信息
    me = whoami(token)
    # 如果 Token 无效或用户不是患者角色，返回 401 未授权错误
    if not me or me["role"] != "patient":
        raise HTTPException(401, "Patient auth required")
    
    # 步骤 2: 查询患者和药物信息
    with get_session() as s:
        # 根据 Token 中的用户名查询患者记录t2
        patient = s.exec(select(Patient).where(Patient.username == me["username"])).first()
        # 查询患者指定的激活药物
        # 条件：患者 ID 匹配、药物名称匹配、药物处于激活状态
        med = s.exec(select(Medication).where(
            Medication.patient_id == patient.id,  # 匹配患者 ID
            Medication.name == med_name,  # 匹配药物名称
            Medication.active == True  # 只查询激活的药物
        )).first()
        
        # 如果药物不存在，返回 404 错误
        if not med:
            raise HTTPException(404, "Medication not found")
        
        # 步骤 3: 检查今天的服用记录
        # 获取今天的日期（不包含时间）
        today = datetime.now().date()
        # 查询今天该药物的所有日志
        # datetime.combine() 创建今天 00:00:00 的时间点，用于查询今天的所有记录
        today_logs = s.exec(select(MedicationLog).where(
            MedicationLog.medication_id == med.id,  # 匹配药物 ID
            MedicationLog.date >= datetime.combine(today, datetime.min.time())  # 日期 >= 今天 00:00:00
        )).all()
        
        # 步骤 4: 防止重复记录（防止超过每日服用次数）
        # 如果今天的日志数量已经达到或超过每日服用次数，拒绝记录
        if len(today_logs) >= med.times_per_day:
            raise HTTPException(400, f"Already logged {med.times_per_day} doses today")
        
        # 步骤 5: 创建新的服用日志记录
        log_entry = MedicationLog(
            medication_id=med.id,  # 关联的药物 ID
            taken=True,  # 标记为已服用
            time_taken=datetime.now().strftime("%H:%M")  # 记录服用时间（格式：HH:MM）
        )
        # 将日志添加到数据库会话
        s.add(log_entry)
        # 提交事务，将日志写入数据库
        s.commit()
    
    # 步骤 6: 将药物服用事件存储到记忆系统
    # 这样 AI 可以在对话中提及患者的服药情况
    mm.remember(
        user_id=me["username"],  # 用户 ID
        text=f"Took {med_name} at {datetime.now().strftime('%H:%M')} on {datetime.now().strftime('%Y-%m-%d')}",  # 记忆文本
        tags=["medication_log"]  # 标签，用于记忆分类
    )
    
    # 步骤 7: 返回成功响应
    return {"ok": True, "message": f"Logged {med_name} as taken."}

# -------------------- MEMORY & CHAT --------------------
@app.post("/remember")
def remember(req: RememberRequest) -> Dict[str, Any]:
    """
    手动记忆存储端点
    
    允许手动将文本信息存储到 MemMachine 情景记忆中。
    通常用于存储重要事件、对话摘要或其他需要记住的信息。
    
    参数:
        req (RememberRequest): 包含以下字段的请求体：
            - user_id (str): 用户 ID（患者用户名）
            - text (str): 要存储的记忆文本内容
    
    返回:
        Dict[str, Any]: 包含以下字段的字典：
            - ok (bool): 操作是否成功
            - saved (bool): 记忆是否成功保存
    
    异常:
        HTTPException(500): 如果 MemMachine 服务不可用或发生其他错误
    
    用途:
        - 手动记录重要事件
        - 存储对话摘要
        - 补充记忆信息
        - 调试和测试记忆系统
    
    注意:
        - 存储的是情景记忆（episodic memory），用于记录事件和对话
        - 记忆会永久存储，供后续对话检索使用
        - 建议在存储前对文本进行清理和格式化
    
    示例请求:
        POST /remember
        {
            "user_id": "patient1",
            "text": "患者今天完成了记忆训练游戏，表现很好"
        }
    
    示例响应:
        {
            "ok": True,
            "saved": true
        }
    """
    try:
        saved = mm.remember(user_id=req.user_id, text=req.text)
        return {"ok": True, "saved": saved}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Existing chat_with_memory function remains unchanged



# -------------------- chat with persistent memory --------------------
@app.post("/chat")
def chat_with_memory(req: ChatRequest):
    """
    带持久化记忆的聊天端点（核心功能）
    
    这是应用的核心功能，提供基于 MemMachine 持久化记忆的智能对话。
    完整工作流程：
    1. 检索用户的历史记忆（情景记忆和档案记忆）
    2. 获取患者信息（药物、目标等）
    3. 构建个性化提示词
    4. 调用 OpenAI 生成 AI 回复
    5. 自动提取和存储新的事实信息
    6. 检测目标完成情况
    7. 提取档案信息
    8. 记录情感检查
    """
    # 从请求中提取用户 ID（用户名）
    user_id = req.user_id
    
    # 检查是否是系统发起的对话（首次问候）
    # "__SYSTEM_START__" 是特殊消息，用于触发初始问候
    is_system_start = req.message == "__SYSTEM_START__"
    
    # 从请求中获取消息计数（用于追踪对话进度，未来功能扩展）
    message_count = req.dict().get("message_count", 0)
    # 从请求中获取药物服用追踪信息（用于未来功能扩展）
    medication_taken = req.dict().get("medication_taken", {})

    # 步骤 1: 检索情景记忆（临时性的事件和对话记录）
    # 如果不是系统启动，使用用户消息作为查询关键词进行语义搜索
    # 如果是系统启动，检索所有记忆
    # top_k=12 表示最多返回 12 条最相关的记忆
    episodic_memories = mm.retrieve(user_id=user_id, query=req.message if not is_system_start else "all memories", top_k=12)

    # 如果第一次检索没有结果，使用通用查询再次尝试，并增加返回数量
    if not episodic_memories:
        episodic_memories = mm.retrieve(user_id=user_id, query="all memories", top_k=20)
    
    # 步骤 2: 检索档案记忆（永久性的用户信息，如偏好、家庭成员等）
    profile_memories = mm.retrieve_profile(user_id=user_id)

    # 调试输出：打印检索到的记忆数量，便于排查问题
    print(f"[DEBUG] Episodic memories for user_id: {user_id}, message: {req.message}, is_system_start: {is_system_start}, count: {len(episodic_memories)}")
    print(f"[DEBUG] Profile memories for user_id: {user_id}, count: {len(profile_memories)}")

    # 步骤 3: 从数据库获取患者信息和相关数据
    print(f"[DEBUG] Getting patient information and related data for user_id: {user_id}")
    with get_session() as s:
        # 查询患者记录：根据用户名查找患者
        patient = s.exec(select(Patient).where(Patient.username == user_id)).first()
        # 如果患者存在，检查并重置过期的药物状态
        if patient:
            check_and_reset_medications(patient.id)

        # 查询患者的所有激活药物：只获取 active=True 的药物
        # 如果患者不存在，返回空列表
        meds = s.exec(select(Medication).where(Medication.patient_id == patient.id, Medication.active == True)).all() if patient else []
        # 查询患者的所有未完成目标：只获取 completed=False 的目标
        # 如果患者不存在，返回空列表
        goals = s.exec(select(Goal).where(Goal.patient_id == patient.id, Goal.completed == False)).all() if patient else []

    # 步骤 4: 计算每个药物的今日服用状态
    print(f"[DEBUG] Calculating medication status for user_id: {user_id}")
    med_status_lines = []  # 存储每个药物的状态文本
    for m in meds:  # 遍历每个激活的药物
        # 获取今天的日期字符串，格式为 YYYY-MM-DD
        today_str = datetime.now().strftime("%Y-%m-%d")
        # 查询今天该药物的所有服用日志
        # datetime.combine() 用于创建今天 00:00:00 的时间点，用于查询今天的所有记录
        logs = s.exec(select(MedicationLog).where(
            MedicationLog.medication_id == m.id,  # 匹配药物 ID
            MedicationLog.date >= datetime.combine(datetime.now().date(), datetime.min.time())  # 日期 >= 今天 00:00:00
        )).all()
        
        # 统计今天已服用的次数（日志数量）
        taken_count = len(logs)
        # 计算今天还需要服用的次数
        remaining = m.times_per_day - taken_count
        
        # 根据剩余次数生成状态文本
        if remaining > 0:
            # 还有未服用的剂量，显示警告图标和剩余次数
            med_status_lines.append(f"⚠️ {m.name}: {taken_count}/{m.times_per_day} taken, {remaining} remaining today")
        else:
            # 所有剂量都已完成，显示完成图标
            med_status_lines.append(f"✅ {m.name}: All doses complete ({m.times_per_day}/{m.times_per_day})")

    # 将所有药物的状态文本合并成一行，用换行符分隔
    # 如果没有药物，显示 "No active medications"
    medication_status = "\n".join(med_status_lines) if med_status_lines else "No active medications"


    # 步骤 5: 处理情景记忆，提取文本内容
    episodic_lines = []  # 存储提取出的记忆文本
    for r in episodic_memories:  # 遍历每条检索到的记忆
        # 记忆可能是字典格式（包含多个字段）或字符串格式
        if isinstance(r, dict):
            # 从字典中提取内容，尝试多个可能的键名（兼容不同的响应格式）
            # 按优先级尝试：content -> episode_content -> text
            content = r.get("content") or r.get("episode_content") or r.get("text", "")
            # 如果提取到内容，添加到列表
            if content:
                episodic_lines.append(content)
        elif isinstance(r, str):
            # 如果记忆本身就是字符串，直接添加
            episodic_lines.append(r)
    # 将所有记忆文本格式化：每行前面加 "- "，用换行符连接
    # strip() 去除首尾空白，如果没有记忆则显示 "No recent memories."
    episodic_snippets = "\n" + "\n".join(f"- {m}" for m in episodic_lines if m).strip() if episodic_lines else "No recent memories."
    print(f"[DEBUG] episodic_snippets: {episodic_snippets}")
    
    # 步骤 6: 处理档案记忆，提取永久性用户信息
    profile_lines = []  # 存储档案信息文本
    for p in profile_memories:  # 遍历每条档案记忆
        if isinstance(p, dict):
            # 从字典中提取内容，尝试多个可能的键名
            content = p.get("episode_content", "") or p.get("content", "") or p.get("text", "")
            if content:
                profile_lines.append(content)
    print(f"[DEBUG] profile_lines: {profile_lines}")

    # 步骤 7: 从数据库补充档案信息（作为备份，确保信息完整）
    # 即使 MemMachine 中没有档案记忆，也能从数据库获取基本信息
    if patient:
        # 添加家庭信息
        if patient.family_info:
            profile_lines.append(f"Family: {patient.family_info}")
        # 添加兴趣爱好
        if patient.hobbies:
            profile_lines.append(f"Hobbies: {patient.hobbies}")
        # 添加紧急联系人信息
        if patient.emergency_contact_name:
            # 先创建基本联系人信息
            emergency_info = (f"Emergency Contact: {patient.emergency_contact_name}")
            # 如果有电话，追加电话信息
            if patient.emergency_contact_phone:
                emergency_info += f" - Phone: {patient.emergency_contact_phone}"
            profile_lines.append(emergency_info)
    print(f"[DEBUG] profile_lines_with_db: {profile_lines}")
    
    # 将所有档案信息格式化：每行前面加 "- "，用换行符连接
    # 如果没有档案信息，显示 "No profile information."
    profile_snippets = "\n".join(f"- {p}" for p in profile_lines if p).strip() or "No profile information."
    
    print(f"[DEBUG] Profile snippets:\n{profile_snippets}")

    # 步骤 8: 准备其他上下文信息
    # 获取兴趣爱好，如果患者不存在或没有设置，使用默认文本
    hobbies = patient.hobbies if patient and patient.hobbies else "No hobbies listed"
    print(f"[DEBUG] hobbies: {hobbies}")
    # 将所有目标文本用逗号连接，如果没有目标则显示 "None right now."
    goals_line = ", ".join([g.text for g in goals]) if goals else "None right now."
    print(f"[DEBUG] goals_line: {goals_line}")
    
    # 步骤 9: 准备药物提醒信息（检查是否有药物即将到期）
    print(f"[DEBUG] Preparing medication reminder information for user_id: {user_id}")
    now = datetime.now()  # 获取当前时间
    due_lines = []  # 存储即将到期的药物提醒
    for m in meds:  # 遍历每个药物
        # 调用调度器函数，检查当前是否在服药时间窗口内（±5分钟）
        msg = next_due_window(now, m.times_per_day, m.specific_times)
        if msg:  # 如果在时间窗口内，msg 不为空
            # 添加药物名称、提醒消息和服用说明
            due_lines.append(f"{m.name}: {msg} {m.instructions or ''}")

    # 步骤 10: 准备紧急联系人信息（用于 AI 上下文）
    print(f"[DEBUG] Preparing emergency contact information for user_id: {user_id}")
    emergency_contact = ""  # 初始化为空字符串
    if patient:  # 如果患者存在
        # 如果同时有姓名和电话，创建完整信息
        if patient.emergency_contact_name and patient.emergency_contact_phone:
            emergency_contact = f"Emergency Contact: {patient.emergency_contact_name} - Phone: {patient.emergency_contact_phone}"
        # 如果只有姓名，只显示姓名
        elif patient.emergency_contact_name:
            emergency_contact = f"Emergency Contact: {patient.emergency_contact_name}" 

    # 步骤 11: 根据对话类型创建系统提示词和用户上下文
    if is_system_start:
        # 如果是系统启动（首次问候），使用简化的提示词
        system = (
            "You are MemoryCare, a compassionate AI companion. This is the FIRST message - greet the user warmly! "
            "Welcome them by name, ask how they're feeling today, and mention you're here to support them. "
            "Be friendly, warm, and conversational. Start the conversation naturally."
        )
        # 用户负载：只包含基本信息，用于生成欢迎消息
        user_payload = (
            f"Start a warm, welcoming conversation with {patient.full_name if patient else user_id}. "
            f"Their hobbies include: {hobbies}. "
            f"Greet them warmly and ask how they're doing today."
        )
    else:
        # 如果是正常对话，使用完整的提示词
        system = (
            "You are MemoryCare, a compassionate companion for dementia or Alzheimer's patients. "
            "Talk like a warm, caring friend. Use the profile information provided to give personalized responses. "
            "When asked about family, hobbies, or personal details, USE THE PROFILE INFORMATION to answer. "
            "Ask about their day, feelings, family, hobbies, and routines naturally. "
            "Encourage them kindly, and celebrate when they share progress."
        )
        
        # 用户负载：包含完整的上下文信息
        user_payload = (
            f"User said: {req.message}\n\n"  # 用户的实际消息
            f"=== MEDICATION STATUS TODAY ===\n{medication_status}\n\n"  # 今日药物状态
            f"=== PROFILE INFORMATION (Use this to answer questions) ===\n{profile_snippets}\n\n"  # 档案信息
            f"=== RECENT MEMORIES ===\n{episodic_snippets}\n\n"  # 最近记忆
            f"Additional Info:\n"  # 其他补充信息
            f"- Full Name: {patient.full_name if patient else 'Unknown'}\n"  # 全名
            f"- Hobbies: {hobbies}\n"  # 兴趣爱好
            f"- Goals: {goals_line}\n"  # 当前目标
            f"- Medications: {', '.join([m.name for m in meds]) if meds else 'None'}\n"  # 药物列表
            f"- {emergency_contact if emergency_contact else 'Emergency Contact: Not provided'}\n"  # 紧急联系人
        )
        print(f"[DEBUG] user_payload before chat(): {user_payload}")

    # 步骤 12: 调用 OpenAI API 生成 AI 回复
    # system: 系统提示词，定义 AI 的角色和行为
    # [{"role": "user", "content": user_payload}]: 用户消息列表
    reply = chat(system, [{"role": "user", "content": user_payload}])

    # ==========================================
    # 步骤 13: 记忆提取和存储（后处理）
    # ==========================================
    
    # 子步骤 13.1: 提取事实信息并存储到记忆系统
    try:
        # 首先判断消息是否可能包含值得存储的事实信息
        # 这个判断可以避免对明显的问题或问候语进行昂贵的 LLM 调用
        if should_attempt_extraction(req.message):
            # 调用 LLM 分析对话，提取事实信息并确定存储路由
            # 返回格式: [{"user_id": "...", "text": "...", "category": "..."}, ...]
            routed_memories = extract_and_route_memories(
                user_id=user_id,  # 当前用户 ID
                user_message=req.message,  # 用户消息
                assistant_reply=reply  # AI 回复（用于上下文分析）
            )

            # 遍历提取出的每条记忆，存储到 MemMachine
            for mem in routed_memories:
                mm.remember(
                    user_id=mem["user_id"],  # 目标用户 ID（通常是当前用户）
                    text=mem["text"],  # 记忆文本（第一人称视角）
                    tags=[mem["category"]]  # 记忆分类标签
                )
            # 调试输出：显示存储了多少条记忆
            print(f"[DEBUG] Stored {len(routed_memories)} extracted memories.")
        else:
            # 如果消息不包含值得存储的信息，跳过提取步骤
            print("[DEBUG] Skipped extraction (message not factual enough).")
    except Exception as e:
        # 如果提取过程出错，记录错误但不中断对话流程
        print(f"[ERROR] Memory extraction failed: {e}")
    # Goal completion detection (same as before)

    if goals and not is_system_start:
        completion_check_prompt = (
            "You are helping to track progress for a dementia patient. "
            "Given the user's latest message below and their active goals, "
            "determine if they clearly achieved or completed any of the goals. "
            "Respond strictly in JSON list format of completed goal texts.\n\n"
            f"Active goals: {[g.text for g in goals]}\n"
            f"User message: {req.message}"
        )
        try:
            result = chat(
                "You are a JSON parser that outputs only JSON list of completed goals.",
                [{"role": "user", "content": completion_check_prompt}],
            )
            completed = []
            try:
                completed = json.loads(result)
            except Exception:
                pass

            if completed:
                with get_session() as s:
                    patient = s.exec(select(Patient).where(Patient.username == user_id)).first()
                    active = s.exec(select(Goal).where(Goal.patient_id == patient.id, Goal.completed == False)).all()
                    for g in active:
                        if any(g.text.lower() == c.lower() for c in completed):
                            g.completed = True
                            g.completed_at = datetime.utcnow()
                            s.add(g)
                    s.commit()

                    remaining = s.exec(select(Goal).where(Goal.patient_id == patient.id, Goal.completed == False)).all()
                    remaining_text = ", ".join([g.text for g in remaining]) or "No active goals now 🎉"

                    mm.remember(user_id=user_id, text=f"Goal completed on {datetime.now().strftime('%Y-%m-%d')}: {', '.join(completed)}", tags=["goal_completion", "achievement"])
                    
                    reply += (
                        f"\n🎉 That's wonderful! Congratulations on completing: {', '.join(completed)}. "
                        f"You're doing great! Active goals now: {remaining_text}"
                    )
        except Exception as e:
            print("Goal check failed:", e)

    # 子步骤 13.3: 提取档案信息（永久性事实，如偏好、关系等）
    # 只在正常对话时进行，系统启动时不需要
    if not is_system_start:
        # 构建档案信息提取的提示词
        profile_extraction_prompt = (
            "Extract any NEW permanent facts about the user from this conversation. "
            "Look for: preferences, likes/dislikes, relationships, routines, medical info. "
            "Return ONLY a JSON object with keys as fact names and values as facts. "
            "If no new profile facts, return empty object {}.\n\n"
            f"User: {req.message}\nAssistant: {reply}"  # 提供对话上下文
        )
        try:
            # 调用 LLM 提取档案信息
            profile_result = chat("You extract profile facts and return only JSON.", [{"role": "user", "content": profile_extraction_prompt}])
            # 初始化档案事实字典
            new_profile_facts = {}
            try:
                # 尝试解析 JSON 格式的结果
                new_profile_facts = json.loads(profile_result)
            except Exception:
                # 如果解析失败，保持空字典
                pass
            
            # 如果有提取到新的档案事实
            if new_profile_facts:
                # 遍历每个事实，存储到档案记忆
                for key, value in new_profile_facts.items():
                    # 只存储非空字符串值
                    if value and isinstance(value, str):
                        mm.remember_profile(
                            user_id=user_id,  # 用户 ID
                            key=key,  # 事实键名（如 "favorite_food"）
                            value=value,  # 事实值（如 "pizza"）
                            category="learned_preferences"  # 分类为学习到的偏好
                        )
        except Exception as e:
            # 如果提取过程出错，记录错误但不中断对话
            print("Profile extraction failed:", e)
        
        # 子步骤 13.4: 情感检查（检测用户是否表达了情感状态）
        # 检查用户消息中是否包含情感相关关键词
        if any(word in req.message.lower() for word in ["feeling", "today", "tired", "happy", "sad", "enjoyed", "worried", "anxious"]):
            # 如果包含情感关键词，将整个消息作为情感检查记录存储
            mm.remember(
                user_id=user_id,
                text=f"Emotional check-in on {datetime.now().strftime('%Y-%m-%d')}: {req.message}",
                tags=["emotional", "wellbeing"]  # 标记为情感和健康相关
            )

    # 步骤 14: 返回响应给前端
    return {
        "ok": True,  # 操作成功标志
        "reply": reply,  # AI 生成的回复文本
        "episodic_memories_used": len(episodic_lines),  # 使用的情景记忆数量（用于调试）
        "profile_facts_available": len(profile_lines),  # 可用的档案事实数量（用于调试）
        "goals": [g.text for g in goals],  # 当前活跃的目标列表（前端可能用于显示）
    }