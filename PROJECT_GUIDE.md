# 📚 MemoryCare 项目开发指南

> **零基础用户快速上手指南** - 从理解项目到修改代码的完整教程

---

## 📖 目录

1. [项目概述](#项目概述)
2. [技术架构](#技术架构)
3. [项目结构详解](#项目结构详解)
4. [核心概念理解](#核心概念理解)
5. [如何修改代码](#如何修改代码)
6. [常见修改场景](#常见修改场景)
7. [调试技巧](#调试技巧)

---

## 🎯 项目概述

### 项目是什么？

MemoryCare 是一个**智能护理助手应用**，专门为痴呆症和阿尔茨海默病患者设计。它的核心特点是：

- **会记住的 AI**：不像普通聊天机器人，它会记住患者的所有信息
- **个性化对话**：根据每个患者的特点进行个性化交流
- **药物管理**：帮助患者按时服药
- **目标追踪**：帮助患者完成治疗目标

### 项目组成

项目分为两部分：
1. **后端（API）**：处理所有业务逻辑、数据库操作、AI 对话
2. **前端（UI）**：用户界面，患者和医生通过网页使用

---

## 🏗️ 技术架构

### 整体架构图

```
┌─────────────────┐
│   Streamlit UI  │  ← 前端界面（用户看到的网页）
│  (streamlit_app)│
└────────┬────────┘
         │ HTTP 请求
         ▼
┌─────────────────┐
│   FastAPI 后端   │  ← 后端服务器（处理所有逻辑）
│   (api/main.py) │
└────────┬────────┘
         │
    ┌────┴────┬──────────┬─────────────┐
    ▼         ▼          ▼             ▼
┌────────┐ ┌──────┐ ┌──────────┐ ┌──────────┐
│ SQLite │ │MemMachine│ │ OpenAI  │ │ 数据库   │
│ 数据库  │ │记忆服务  │ │  AI服务  │ │ 模型     │
└────────┘ └──────┘ └──────────┘ └──────────┘
```

### 技术栈说明

| 技术 | 用途 | 为什么用它 |
|------|------|-----------|
| **FastAPI** | 后端框架 | 快速、现代、自动生成 API 文档 |
| **Streamlit** | 前端框架 | 简单易用，快速构建界面 |
| **SQLModel** | 数据库 ORM | 类型安全，易于操作数据库 |
| **SQLite** | 数据库 | 轻量级，无需单独安装数据库服务器 |
| **MemMachine** | 记忆服务 | 提供持久化记忆功能 |
| **OpenAI** | AI 服务 | 提供智能对话能力 |

---

## 📁 项目结构详解

### 完整目录结构

```
Memory-Care/
├── api/                    # 后端 API 代码
│   ├── __init__.py        # Python 包初始化文件
│   └── main.py            # ⭐ 后端主文件（最重要的文件）
│
├── ui/                     # 前端界面代码
│   └── streamlit_app.py   # ⭐ 前端主文件（用户界面）
│
├── utils/                  # 工具模块（被其他文件调用的功能）
│   ├── models.py          # 数据模型（定义数据库表结构）
│   ├── db.py              # 数据库连接和初始化
│   ├── auth.py            # 用户认证（登录、Token）
│   ├── llm_client.py      # OpenAI API 客户端
│   ├── memmachine_client.py  # MemMachine 客户端
│   └── scheduler.py       # 药物提醒调度器
│
├── app.db                  # SQLite 数据库文件（自动生成）
├── requirements.txt        # Python 依赖包列表
├── README.md              # 项目说明文档
└── PROJECT_GUIDE.md       # 本文件（开发指南）
```

### 各文件职责说明

#### 1. `api/main.py` - 后端核心文件 ⭐⭐⭐

**作用**：处理所有后端逻辑，提供 API 接口

**包含内容**：
- API 路由定义（如 `/chat`、`/auth/patient/login`）
- 业务逻辑处理
- 数据库操作
- AI 对话生成
- 记忆存储和检索

**关键函数**：
- `chat_with_memory()` - 处理 AI 对话（最复杂）
- `patient_signup()` - 患者注册
- `add_med()` - 添加药物
- `add_goal()` - 添加目标

#### 2. `ui/streamlit_app.py` - 前端界面文件 ⭐⭐⭐

**作用**：构建用户界面，与后端 API 通信

**包含内容**：
- 登录/注册界面
- 患者聊天界面
- 医生管理界面
- 药物和目标显示

**关键部分**：
- 会话状态管理（`st.session_state`）
- 页面路由（根据登录状态显示不同页面）
- API 调用（使用 `requests` 库）

#### 3. `utils/models.py` - 数据模型 ⭐⭐

**作用**：定义数据库表结构

**包含的类**：
- `Patient` - 患者信息表
- `Medication` - 药物表
- `MedicationLog` - 药物服用日志表
- `Goal` - 治疗目标表

**如何理解**：每个类对应数据库中的一张表，类的属性对应表的列

#### 4. `utils/db.py` - 数据库连接 ⭐

**作用**：管理数据库连接

**关键函数**：
- `get_session()` - 获取数据库会话
- `create_db_and_tables()` - 创建数据库和表

#### 5. `utils/auth.py` - 认证模块 ⭐

**作用**：处理用户登录和 Token 管理

**关键函数**：
- `issue_doctor_token()` - 为医生颁发 Token
- `issue_patient_token()` - 为患者颁发 Token
- `whoami()` - 验证 Token 并返回用户信息

#### 6. `utils/llm_client.py` - AI 客户端 ⭐⭐

**作用**：与 OpenAI API 通信，生成 AI 回复

**关键函数**：
- `chat()` - 发送消息给 OpenAI，获取回复

#### 7. `utils/memmachine_client.py` - 记忆服务客户端 ⭐⭐

**作用**：与 MemMachine 服务通信，存储和检索记忆

**关键函数**：
- `remember()` - 存储情景记忆
- `remember_profile()` - 存储档案记忆
- `retrieve()` - 检索情景记忆
- `retrieve_profile()` - 检索档案记忆

#### 8. `utils/scheduler.py` - 调度器 ⭐

**作用**：计算药物服用时间窗口

**关键函数**：
- `next_due_window()` - 判断当前是否在服药时间窗口内

---

## 🧠 核心概念理解

### 1. 两种记忆类型

#### 情景记忆（Episodic Memory）
- **是什么**：临时性的事件和对话记录
- **例子**："今天早上吃了早餐"、"昨天和女儿通了电话"
- **特点**：会随时间积累，用于理解上下文

#### 档案记忆（Profile Memory）
- **是什么**：永久性的用户信息
- **例子**："我喜欢散步"、"我的女儿叫 Sarah"、"紧急联系人：John"
- **特点**：不会改变，用于个性化对话

### 2. 数据流向

#### 用户发送消息的完整流程：

```
1. 用户在网页输入消息
   ↓
2. Streamlit 前端发送 HTTP 请求到后端
   ↓
3. FastAPI 后端接收请求
   ↓
4. 从 MemMachine 检索相关记忆
   ↓
5. 从数据库获取患者信息（药物、目标等）
   ↓
6. 构建提示词，调用 OpenAI API
   ↓
7. OpenAI 返回 AI 回复
   ↓
8. 提取新的事实信息，存储到 MemMachine
   ↓
9. 检测目标完成情况
   ↓
10. 返回回复给前端
    ↓
11. Streamlit 显示回复给用户
```

### 3. 会话状态（Session State）

**什么是会话状态？**
- Streamlit 在页面刷新时会重置所有变量
- `st.session_state` 可以在刷新之间保持数据
- 用于存储登录状态、对话历史等

**常用会话变量**：
```python
st.session_state.role          # 用户角色（patient/doctor）
st.session_state.token         # 认证 Token
st.session_state.chat_log      # 对话历史
st.session_state.patient_username  # 当前患者用户名
```

### 4. API 请求和响应

**前端如何调用后端？**

```python
# 示例：发送聊天消息
response = requests.post(
    "http://127.0.0.1:8000/chat",  # API 地址
    json={                          # 请求数据
        "user_id": "alice",
        "message": "你好",
        "token": "pat_xxx"
    }
)
data = response.json()  # 获取响应数据
reply = data["reply"]   # 提取 AI 回复
```

---

## ✏️ 如何修改代码

### 修改前的准备

1. **理解需求**：明确要改什么功能
2. **找到相关文件**：根据功能定位到对应文件
3. **阅读现有代码**：理解当前实现逻辑
4. **制定修改计划**：想清楚如何修改

### 修改步骤

#### 步骤 1：定位要修改的文件

| 要修改的功能 | 主要文件 | 辅助文件 |
|------------|---------|---------|
| 用户界面（按钮、布局） | `ui/streamlit_app.py` | - |
| API 接口（添加新接口） | `api/main.py` | - |
| 数据库表结构 | `utils/models.py` | `utils/db.py` |
| 认证逻辑 | `utils/auth.py` | `api/main.py` |
| AI 对话行为 | `api/main.py` | `utils/llm_client.py` |
| 记忆存储逻辑 | `utils/memmachine_client.py` | `api/main.py` |

#### 步骤 2：理解代码结构

**修改 API 接口示例**：

```python
# 在 api/main.py 中添加新接口

@app.post("/your-new-endpoint")  # 定义路由
def your_new_function(payload: YourModel):  # 定义处理函数
    """
    函数说明
    """
    # 1. 验证用户身份
    info = whoami(payload.token)
    if not info:
        raise HTTPException(401, "Unauthorized")
    
    # 2. 处理业务逻辑
    # ... 你的代码 ...
    
    # 3. 返回结果
    return {"ok": True, "data": result}
```

**修改前端界面示例**：

```python
# 在 ui/streamlit_app.py 中添加新界面元素

if st.button("新按钮"):  # 添加按钮
    # 调用后端 API
    response = requests.post(
        f"{API}/your-new-endpoint",
        json={"token": st.session_state.token}
    )
    if response.ok:
        st.success("操作成功！")
```

#### 步骤 3：测试修改

1. **重启服务**：修改代码后需要重启
2. **检查错误**：查看终端是否有错误信息
3. **功能测试**：实际使用功能，验证是否正常

---

## 🔧 常见修改场景

### 场景 1：添加新的患者信息字段

**需求**：在患者注册时添加"年龄"字段

**步骤**：

1. **修改数据模型** (`utils/models.py`)：
```python
class Patient(SQLModel, table=True):
    # ... 现有字段 ...
    age: Optional[int] = None  # 添加年龄字段
```

2. **修改注册接口** (`api/main.py`)：
```python
class PatientSignup(BaseModel):
    # ... 现有字段 ...
    age: Optional[int] = None  # 添加年龄到请求模型

@app.post("/auth/patient/signup")
def patient_signup(payload: PatientSignup):
    # ... 现有代码 ...
    p = Patient(
        # ... 现有字段 ...
        age=payload.age,  # 添加年龄赋值
    )
```

3. **修改前端注册表单** (`ui/streamlit_app.py`)：
```python
# 在注册表单中添加
su_age = st.number_input("年龄", key="su_age", min_value=0, max_value=150)
# 在提交时包含
payload = {
    # ... 现有字段 ...
    "age": su_age,
}
```

4. **更新数据库**：
   - 删除 `app.db` 文件（或使用数据库迁移工具）
   - 重启应用，会自动创建新表结构

### 场景 2：修改 AI 对话风格

**需求**：让 AI 更正式或更友好

**位置**：`api/main.py` 中的 `chat_with_memory()` 函数

**修改系统提示词**：
```python
# 找到这段代码
system = (
    "You are MemoryCare, a compassionate companion..."
)

# 修改为
system = (
    "You are MemoryCare, a professional and caring companion. "
    "Use formal language but remain warm and supportive..."
)
```

### 场景 3：添加新的 API 接口

**需求**：添加获取患者统计信息的接口

**步骤**：

1. **在 `api/main.py` 中添加**：
```python
@app.get("/patient/stats")
def get_patient_stats(token: str = Query(...)):
    """
    获取患者统计信息
    """
    # 1. 验证身份
    me = whoami(token)
    if not me or me["role"] != "patient":
        raise HTTPException(401, "Patient auth required")
    
    # 2. 查询数据
    with get_session() as s:
        patient = s.exec(select(Patient).where(
            Patient.username == me["username"]
        )).first()
        
        # 统计药物
        meds_count = len(s.exec(select(Medication).where(
            Medication.patient_id == patient.id
        )).all())
        
        # 统计目标
        goals_count = len(s.exec(select(Goal).where(
            Goal.patient_id == patient.id
        )).all())
    
    # 3. 返回结果
    return {
        "ok": True,
        "stats": {
            "medications": meds_count,
            "goals": goals_count
        }
    }
```

2. **在前端调用** (`ui/streamlit_app.py`)：
```python
# 在患者界面添加
if st.button("查看统计"):
    response = requests.get(
        f"{API}/patient/stats",
        params={"token": st.session_state.token}
    )
    if response.ok:
        stats = response.json()["stats"]
        st.write(f"药物数量: {stats['medications']}")
        st.write(f"目标数量: {stats['goals']}")
```

### 场景 4：修改界面样式

**位置**：`ui/streamlit_app.py` 开头的 CSS 部分

**示例：修改按钮颜色**：
```python
# 找到这段 CSS
.stButton>button {
    background: linear-gradient(135deg, #a855f7 0%, #ec4899 100%);
    # 修改为
    background: linear-gradient(135deg, #3b82f6 0%, #06b6d4 100%);
}
```

### 场景 5：添加新的记忆类型

**需求**：添加"医疗记录"类型的记忆

**位置**：`api/main.py` 中的记忆提取函数

**修改**：
```python
# 在 extract_and_route_memories() 函数的提示词中
Categories: personal, family, medical, preference, routine, memory, location, medical_record
# 添加新类别

# 在存储时使用新类别
mm.remember(
    user_id=user_id,
    text=text,
    tags=["medical_record"]  # 使用新标签
)
```

---

## 🐛 调试技巧

### 1. 查看日志输出

**后端日志**：
- 启动后端时，终端会显示所有日志
- 查找 `[DEBUG]`、`[ERROR]`、`[WARN]` 标记

**前端日志**：
- Streamlit 会在终端显示错误
- 使用 `st.write()` 或 `print()` 输出调试信息

### 2. 使用调试工具

**检查 API 是否正常**：
```bash
# 在浏览器访问
http://127.0.0.1:8000/health

# 或使用 curl
curl http://127.0.0.1:8000/health
```

**查看 API 文档**：
```bash
# 启动后端后访问
http://127.0.0.1:8000/docs
```

### 3. 常见错误及解决

| 错误 | 可能原因 | 解决方法 |
|------|---------|---------|
| `ModuleNotFoundError` | 缺少依赖包 | `pip install -r requirements.txt` |
| `Connection refused` | 后端未启动 | 启动后端服务 |
| `401 Unauthorized` | Token 无效 | 重新登录 |
| `404 Not Found` | API 路径错误 | 检查路由定义 |
| 数据库错误 | 表结构不匹配 | 删除 `app.db` 重新创建 |

### 4. 添加调试代码

**在后端添加调试**：
```python
print(f"[DEBUG] 变量值: {variable}")  # 打印变量
print(f"[DEBUG] 请求数据: {req.dict()}")  # 打印请求
```

**在前端添加调试**：
```python
st.write("调试信息:", variable)  # 显示在界面上
with st.expander("调试详情"):
    st.json(data)  # 显示 JSON 数据
```

---

## 📝 代码修改检查清单

修改代码后，检查以下事项：

- [ ] 语法正确（没有拼写错误）
- [ ] 导入的模块都存在
- [ ] 变量名拼写正确
- [ ] 函数参数类型匹配
- [ ] 数据库操作有错误处理
- [ ] API 调用有错误处理
- [ ] 测试了新功能
- [ ] 没有破坏现有功能

---

## 🚀 下一步学习

### 推荐学习资源

1. **FastAPI 官方文档**：https://fastapi.tiangolo.com
2. **Streamlit 官方文档**：https://docs.streamlit.io
3. **SQLModel 文档**：https://sqlmodel.tiangolo.com
4. **Python 基础**：如果对 Python 不熟悉，先学习基础语法

### 进阶修改建议

1. **添加单元测试**：为关键功能编写测试
2. **优化性能**：缓存常用数据，减少数据库查询
3. **增强安全性**：密码加密、输入验证
4. **改进 UI**：添加动画、优化布局
5. **添加新功能**：语音输入、数据分析等

---

## 💡 快速参考

### 常用代码片段

**发送 POST 请求**：
```python
response = requests.post(
    f"{API}/endpoint",
    json={"key": "value"},
    params={"token": token}
)
```

**发送 GET 请求**：
```python
response = requests.get(
    f"{API}/endpoint",
    params={"token": token, "param": value}
)
```

**数据库查询**：
```python
with get_session() as s:
    result = s.exec(select(Model).where(Model.field == value)).all()
```

**存储记忆**：
```python
mm.remember(
    user_id="username",
    text="记忆内容",
    tags=["tag1", "tag2"]
)
```

**调用 AI**：
```python
reply = chat(
    system_prompt,
    [{"role": "user", "content": user_message}]
)
```

---

## ❓ 常见问题

**Q: 如何添加新的数据库表？**
A: 在 `utils/models.py` 中定义新模型类，重启应用会自动创建表。

**Q: 如何修改 API 响应格式？**
A: 修改 `api/main.py` 中对应路由函数的返回值。

**Q: 如何添加新的页面？**
A: 在 `ui/streamlit_app.py` 中添加新的条件分支和界面代码。

**Q: 记忆存储在哪里？**
A: 存储在 MemMachine 服务中，需要 MemMachine 服务运行。

**Q: 如何重置数据库？**
A: 删除 `app.db` 文件，重启应用。

---

## 📞 获取帮助

如果遇到问题：

1. 查看代码注释（所有文件都有详细中文注释）
2. 检查终端错误信息
3. 查看 API 文档（`http://127.0.0.1:8000/docs`）
4. 阅读相关技术文档

---

**祝您开发顺利！** 🎉


