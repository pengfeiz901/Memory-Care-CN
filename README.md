## ⚙️ 环境变量

```bash
# .env 文件需要配置
# OpenAI API 配置
OPENAI_API_KEY=[Your API Key]
OPENAI_BASE_URL=[LLM BASE URL]
OPENAI_MODEL=[LLM MODEL]

# MemMachine 服务配置（根据实际情况选择一种）

# 目标服务配置（根据实际情况选择一种）
# 选项1：本地容器网络（当目标服务在同一个docker-compose中）
# TARGET_SERVICE_HOST=target-service
# TARGET_SERVICE_PORT=8080
# TARGET_SERVICE_PROTOCOL=http

# 选项2：本地宿主机（当目标服务运行在宿主机上）
MEMMACHINE_SERVICE_HOST=host.docker.internal
MEMMACHINE_SERVICE_PORT=8080
MEMMACHINE_SERVICE_PROTOCOL=http

# 选项3：远程服务器
# MEMMACHINE_SERVICE_HOST=api.example.com
# MEMMACHINE_SERVICE_PORT=8080
# MEMMACHINE_SERVICE_PROTOCOL=http

# 选项4：完整的URL（直接覆盖所有上述设置）
# MEMMACHINE_SERVICE_FULL_URL=http://192.168.1.100:8080

# MemMachine 配置（如果 MemMachine 不在本地 8080 端口, 请修改为实际地址）
MEMMACHINE_BASE_URL=$MEMMACHINE_SERVICE_PROTOCOL://$MEMMACHINE_SERVICE_HOST:$MEMMACHINE_SERVICE_PORT
```

# 1. 配置环境变量（创建 .env 文件）
参考上面的例子，创建一个 .env 文件，配置好环境变量。

# 2. 安装 MemMachine
参考安装步骤 - https://ai.feishu.cn/wiki/DbdNwIFmdieADrkuge8cBZe1nXb?from=from_copylink


# 3. 🔄 Agent 启动流程

### 方式一：传统方式启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量（创建 .env 文件）

# 3. 启动 MemMachine 服务

# 4. 启动后端（终端 1）
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000

# 5. 启动前端（终端 2）
streamlit run ui/streamlit_app.py
```

### 方式二：Docker 方式启动（推荐）
一键启动所有服务
```bash
chmod +x docker-compose.sh
./docker-compose.sh
```

**访问地址：**
- 前端应用：http://localhost:8501
- 后端 API：http://localhost:8000
- MemMachine API：http://localhost:8080
- MemMachine API 文档：http://localhost:8080/docs

**Docker 相关命令：**
```bash
# 查看服务状态
docker-compose ps

# 查看服务日志
docker-compose logs -f

# 停止服务
docker-compose down

# 重启服务
docker-compose restart
```

**常见问题解决：**
- 如果启动失败，检查是否已有服务占用8000端口：
  ```bash
  sudo netstat -tulpn | grep :8000
  # 如有占用，终止相应进程
  sudo kill <PID>
  ```
- 如果遇到 Docker 权限问题：
  ```bash
  # 将用户添加到 docker 组
  sudo groupadd docker 2>/dev/null; sudo usermod -aG docker $USER
  # 或使用 sudo 运行脚本
  sudo ./docker-compose.sh
  ```
- 如果出现与 MemMachine 服务连接相关的错误：
  ```bash
  # 确保 MemMachine 服务正在运行
  curl http://localhost:8080/health
  # 如果服务未运行，请先启动 MemMachine 服务
  # 然后重新启动 MemoryCare Docker 容器
  ```

- MemMachine 服务安装和启动：
  ```bash
  # 1. 进入 MemMachine 目录
  cd [MemMachine code folder]
  
  # 2. 启动 MemMachine 服务
  ./memmachine-compose.sh  # 推荐使用脚本
  # 或 docker-compose up -d
  
  # 3. 验证服务状态
  curl http://localhost:8080/api/v2/health
  ```

---

### ⚡ 快速参考
**常用代码片段速查**：查看 [QUICK_REFERENCE.md](./QUICK_REFERENCE.md)

包含内容：
- ✅ 文件速查表
- ✅ 常用代码片段（复制即用）
- ✅ 常见修改场景速查
- ✅ 关键位置索引
- ✅ 调试命令

**适合人群**：
- 🎯 零基础开发者：从理解项目到上手修改
- 🔧 有经验的开发者：快速查找代码位置和示例
- 📝 代码维护者：快速定位和修改功能

---

TODO List:
- 支持医生端注册新用户
- 优化前端界面，改善用户体验

---

# 💙 MemoryCare - AI Companion for Dementia & Alzheimer's Care

> **Dementia care powered by memories that last—because every moment matters**

[![MemMachine](https://img.shields.io/badge/Powered%20by-MemMachine-purple)](https://github.com/memverge/memmachine)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.36+-red)](https://streamlit.io)


## 🎥 Demo Video

**Watch MemoryCare in Action**: https://youtu.be/eRqnBM146YU

## ℹ️Introduction

MemoryCare transforms dementia and Alzheimer's care by creating an AI companion that truly remembers. Using **MemMachine's persistent memory layer**, our agent learns about each patient over time, recalls personal details naturally in conversation, and helps them maintain independence through medication reminders and goal tracking. While especially useful for patients with dementia or Alzheimer's, MemoryCare can prove useful for any and all people.

**Built for the MemVerge "Memories That Last" AI Agents Hackathon**

---

## 🎯 The Problem We're Solving

People with dementia face:
- **Memory loss** that makes daily routines challenging
- **Medication non-adherence** due to forgetting doses
- **Loss of independence** and social isolation
- **Caregiver burden** from constant monitoring needs

Traditional chatbots forget everything between sessions. **MemoryCare doesn't.**

---

## ✨ Key Features

### 🧠 **Dual Memory Architecture**
- **Episodic Memory**: Conversation history, daily events, medication logs
- **Profile Memory**: Permanent facts (family, hobbies, preferences, emergency contacts)
- **Smart Routing**: Automatically determines whose memory to store when multiple people are mentioned

### 💬 **Intelligent Conversational AI**
- Warm, empathetic companion that adapts to each patient
- Natural memory integration ("You mentioned your daughter Sarah visits on Sundays...")
- Emotional check-ins and wellbeing monitoring
- Automatic goal completion detection

### 💊 **Medication Management**
- Daily dose tracking with progress visualization
- Smart reminders based on scheduled times
- Doctor-controlled prescription management
- Medication history and adherence reports

### 🎯 **Goal Tracking System**
- Doctor-assigned therapeutic goals
- Automatic completion detection from natural conversation
- Progress monitoring and celebration of achievements

### 👨‍⚕️ **Care Provider Dashboard**
- Patient management and monitoring
- Goal assignment and tracking
- Medication oversight with adherence data
- Multi-patient support

---


### 🎮 **Usage Guide**
**For Patients**
1. **Sign Up**: Create an account with your name, hobbies, family info, and emergency contact
2. **Chat Naturally**: Talk with the AI companion about your day, feelings, or concerns
3. **Track Medications**: Mark medications as taken through the sidebar dashboard
4. **View Goals**: See therapeutic goals assigned by your doctor

**For Doctors**

1. **Login**: Use credentials doctor / doctor
2. **Select Patient**: Choose from registered patient
3. **Assign Goals**: Set therapeutic goals like "Take a 10-minute walk daily"
4. **Prescribe Medications**: Add medications with dosage schedules
5. **Monitor Progress**: View medication adherence and goal completion rates

### 🚧 **Possible Future Enhancements**

1. **Dates**: Setup date management for mediccations so the doctor can assign meds for certain dates/time periods.
2. **Voice Interface**: Set up speech to text for accessibility.
3. **Advanced Analytics**: Cognitive decline detection from conversation patterns.

### 🤝 **Team & Acknowledgments**
- **Team**:
    - Viranshu Paruparla (viranshu-shaileshkumar.paruparla.585@my.csun.edu)
    - Krish Patel (patelkrishm@gmail.com)
- **Built for**: MemVerge AI Agents Hackathon
- **Powered by**: MemMachine, OpenAI GPT-4, FastAPI, Streamlit
- **Inspiration**: Dedicated to families affected by Alzheimer's and dementia

## Special thanks to the MemVerge team for creating MemMachine and hosting this innovative hackathon.


