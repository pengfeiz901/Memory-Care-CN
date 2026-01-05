# ⚡ MemoryCare 快速参考卡片

> 快速查找常用信息和代码片段

---

## 📁 文件速查表

| 文件 | 作用 | 修改频率 |
|------|------|---------|
| `api/main.py` | 后端核心，所有 API 接口 | ⭐⭐⭐ 最常修改 |
| `ui/streamlit_app.py` | 前端界面 | ⭐⭐⭐ 最常修改 |
| `utils/models.py` | 数据库表结构 | ⭐⭐ 添加字段时修改 |
| `utils/auth.py` | 用户认证 | ⭐ 很少修改 |
| `utils/db.py` | 数据库连接 | ⭐ 很少修改 |
| `utils/llm_client.py` | OpenAI 客户端 | ⭐ 很少修改 |
| `utils/memmachine_client.py` | 记忆服务客户端 | ⭐⭐ 修改记忆逻辑时 |
| `utils/scheduler.py` | 药物提醒 | ⭐ 很少修改 |

---

## 🔑 核心概念速记

### 记忆类型
- **情景记忆**：临时事件（"今天吃了药"）
- **语义记忆**：永久信息（"我喜欢散步"）
  - 包含原档案记忆的所有功能
  - 通过types参数控制记忆类型

### 用户角色
- **patient**：患者（使用聊天、查看药物）
- **doctor**：医生（管理患者、分配目标）

### 数据流向
```
用户输入 → Streamlit → FastAPI → MemMachine/OpenAI → 返回 → Streamlit → 显示
```

---

## 💻 常用代码片段

### 1. 前端调用后端 API

```python
# POST 请求
response = requests.post(
    f"{API}/endpoint",
    json={"key": "value"},
    params={"token": st.session_state.token}
)

# GET 请求
response = requests.get(
    f"{API}/endpoint",
    params={"token": st.session_state.token, "param": "value"}
)

# 处理响应
if response.ok:
    data = response.json()
    result = data["key"]
else:
    st.error("操作失败")
```

### 2. 后端 API 路由

```python
@app.post("/your-endpoint")
def your_function(payload: YourModel, token: str = Query(...)):
    # 验证身份
    info = whoami(token)
    if not info:
        raise HTTPException(401, "Unauthorized")
    
    # 业务逻辑
    # ...
    
    # 返回结果
    return {"ok": True, "data": result}
```

### 3. 数据库操作

```python
# 查询
with get_session() as s:
    patient = s.exec(select(Patient).where(
        Patient.username == username
    )).first()

# 创建
with get_session() as s:
    new_item = Model(field=value)
    s.add(new_item)
    s.commit()

# 更新
with get_session() as s:
    item = s.get(Model, id)
    item.field = new_value
    s.add(item)
    s.commit()
```

### 4. 记忆操作

```python
# 存储情景记忆（默认行为）
mm.remember(
    user_id="username",
    text="记忆内容",
    tags=["tag1", "tag2"]
)

# 显式存储情景记忆（使用types参数）
mm.remember(
    user_id="username",
    text="记忆内容",
    tags=["tag1", "tag2"],
    types=["episodic"]  # 只存储为情景记忆
)

# 存储语义记忆（原档案记忆）
mm.remember(
    user_id="username",
    text="favorite_food: pizza",  # 格式：key: value
    tags=["preference"],
    types=["semantic"]  # 只存储为语义记忆
)

# 同时存储情景和语义记忆
mm.remember(
    user_id="username",
    text="记忆内容",
    tags=["tag1", "tag2"],
    types=["episodic", "semantic"]  # 同时存储为两种类型
)

# 检索情景记忆
memories = mm.retrieve(user_id="username", query="关键词", top_k=10)

# 检索语义记忆（原档案记忆）
semantic_memories = mm.retrieve_semantic(user_id="username")
```

### 5. AI 对话

```python
reply = chat(
    system_prompt,  # 系统提示词
    [{"role": "user", "content": user_message}]  # 消息列表
)
```

---

## 🎯 常见修改场景速查

### 添加新字段到患者表

1. `utils/models.py` - 添加字段到 `Patient` 类
2. `api/main.py` - 更新 `PatientSignup` 模型和注册函数
3. `ui/streamlit_app.py` - 更新注册表单
4. 删除 `app.db` 重新创建

### 添加新 API 接口

1. `api/main.py` - 添加路由函数
2. `ui/streamlit_app.py` - 添加前端调用代码

### 修改 AI 对话风格

1. `api/main.py` - 找到 `chat_with_memory()` 函数
2. 修改 `system` 变量的提示词内容

### 修改界面样式

1. `ui/streamlit_app.py` - 找到 CSS 部分（文件开头）
2. 修改对应的样式类

---

## 🐛 调试命令

```bash
# 检查MemMachine 健康
curl http://127.0.0.1:8080/health

# 查看 MemMachine API 文档
# 浏览器访问: http://127.0.0.1:8080/docs

# 查看数据库（需要 SQLite 工具）
sqlite3 data/app.db
.tables
SELECT * FROM patient;
```

## 💾 数据库问题解决

### 在 macOS 上部署时遇到 "unable to open database file" 错误

**问题原因**: Docker 容器在 macOS 上挂载单个 SQLite 文件时可能出现权限或路径问题，导致 SQLite 无法正确创建或访问数据库文件。

**解决方案**:
1. 修改 `docker-compose.yml` 将挂载单个文件改为挂载整个目录：
   ```yaml
   volumes:
     - ./data:/app/data  # 挂载整个数据目录而不是单个文件
     - ./.env:/app/.env
   ```

2. 修改 `utils/db.py` 中的数据库 URL：
   ```python
   DB_URL = "sqlite:///data/app.db"  # 指向数据目录中的数据库文件
   ```

3. 创建数据目录：
   ```bash
   mkdir -p data
   ```

4. 重建并启动容器：
   ```bash
   sudo docker compose down
   sudo docker compose build
   sudo docker compose up -d
   ```

---

## 📍 关键位置速查

### 后端关键函数位置

| 功能 | 文件 | 函数名 |
|------|------|--------|
| AI 对话 | `api/main.py` | `chat_with_memory()` |
| 患者注册 | `api/main.py` | `patient_signup()` |
| 患者登录 | `api/main.py` | `patient_login()` |
| 添加药物 | `api/main.py` | `add_med()` |
| 添加目标 | `api/main.py` | `add_goal()` |
| 记忆提取 | `api/main.py` | `extract_and_route_memories()` |

### 前端关键位置

| 功能 | 文件 | 位置 |
|------|------|------|
| 登录界面 | `ui/streamlit_app.py` | `st.session_state.page == "login"` |
| 患者聊天 | `ui/streamlit_app.py` | `st.session_state.role == "patient"` |
| 医生界面 | `ui/streamlit_app.py` | `st.session_state.role == "doctor"` |
| 会话状态 | `ui/streamlit_app.py` | 文件开头初始化部分 |

---


## 📞 获取帮助

- 详细文档：查看 `PROJECT_GUIDE.md`
- 代码注释：所有文件都有详细中文注释

---

**提示**：保存此文件到书签，方便快速查阅！


