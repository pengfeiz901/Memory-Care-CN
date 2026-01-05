# main.py 数据来源分析表

本文档详细说明了 `api/main.py` 中每个操作或信息是从 **SQL 数据库**还是从 **MemMachine 记忆系统**获取的。

## 表格说明

- **SQL 数据库**：使用 SQLModel/SQLite，存储结构化数据（患者信息、药物、目标、日志等）
- **MemMachine**：外部记忆服务，存储非结构化的对话记忆和用户档案信息

---

## 完整数据来源对照表

| 路由/函数 | 操作/信息 | 数据来源 | 具体说明 | 代码行数 |
|---------|---------|---------|---------|---------|
| **GET /health** | MemMachine 健康检查 | MemMachine | 检查 MemMachine 服务状态 | 388 |
| **POST /auth/doctor/login** | 医生登录验证 | 无 | 仅验证硬编码凭证，不涉及数据库或记忆系统 | 433-436 |
| **POST /auth/patient/signup** | 检查用户名是否存在 | SQL 数据库 | 查询 `Patient` 表检查用户名重复 | 449 |
| | 创建患者记录 | SQL 数据库 | 插入新 `Patient` 记录 | 456-468 |
| | 存储注册事件 | MemMachine | 存储情景记忆（episodic） | 508-513 |
| | 存储个人信息 | MemMachine | 存储档案记忆（profile）：姓名、家庭信息、兴趣爱好等 | 482-504 |
| | 存储紧急联系人 | MemMachine | 单独存储紧急联系人档案记忆 | 499-504 |
| **POST /auth/patient/login** | 验证患者凭证 | SQL 数据库 | 查询 `Patient` 表验证用户名和密码 | 567-569 |
| | 记录登录事件 | MemMachine | 存储登录事件到情景记忆 | 570-574 |
| **GET /doctor/patients** | 获取所有患者列表 | SQL 数据库 | 查询 `Patient` 表获取所有患者 | 635 |
| **POST /doctor/medications** | 查询患者信息 | SQL 数据库 | 根据用户名查询 `Patient` 表 | 709 |
| | 检查重复药物 | SQL 数据库 | 查询 `Medication` 表检查同名激活药物 | 712-716 |
| | 创建药物记录 | SQL 数据库 | 插入新 `Medication` 记录 | 721-730 |
| | 存储药物事件 | MemMachine | 存储医生添加药物的事件到情景记忆 | 736-741 |
| | 存储药物信息 | MemMachine | 存储药物信息到档案记忆（供 AI 参考） | 732-741 |
| **GET /doctor/patient-goals** | 查询患者信息 | SQL 数据库 | 根据用户名查询 `Patient` 表 | 813 |
| | 获取所有目标 | SQL 数据库 | 查询 `Goal` 表获取患者的所有目标 | 816 |
| **GET /doctor/patient-medications** | 查询患者信息 | SQL 数据库 | 根据用户名查询 `Patient` 表 | 899 |
| | 获取所有药物 | SQL 数据库 | 查询 `Medication` 表获取患者的所有药物 | 902 |
| | 获取服用历史 | SQL 数据库 | 查询 `MedicationLog` 表获取每个药物的日志 | 905 |
| **POST /doctor/goals** | 查询患者信息 | SQL 数据库 | 根据用户名查询 `Patient` 表 | 972 |
| | 创建目标记录 | SQL 数据库 | 插入新 `Goal` 记录 | 975-977 |
| | 存储目标事件 | MemMachine | 存储医生分配目标的事件到情景记忆 | 988-993 |
| | 存储目标信息 | MemMachine | 存储目标到档案记忆（供 AI 参考） | 983-993 |
| **GET /patient/goals** | 验证患者身份 | 无 | 通过 Token 验证（不涉及数据库查询） | 1059 |
| | 查询患者信息 | SQL 数据库 | 根据 Token 中的用户名查询 `Patient` 表 | 1063 |
| | 获取未完成目标 | SQL 数据库 | 查询 `Goal` 表获取 `completed=False` 的目标 | 1064 |
| **GET /patient/medications** | 验证患者身份 | 无 | 通过 Token 验证 | 1141 |
| | 查询患者信息 | SQL 数据库 | 根据 Token 中的用户名查询 `Patient` 表 | 1145 |
| | 检查并重置过期药物 | SQL 数据库 | 调用 `check_and_reset_medications` 函数 | 1146 |
| | 获取激活药物 | SQL 数据库 | 查询 `Medication` 表获取 `active=True` 的药物 | 1147 |
| | 获取服用历史 | SQL 数据库 | 查询 `MedicationLog` 表获取每个药物的日志 | 1150 |
| **POST /patient/medications/log** | 验证患者身份 | 无 | 通过 Token 验证 | 1174 |
| | 查询患者信息 | SQL 数据库 | 根据 Token 中的用户名查询 `Patient` 表 | 1182 |
| | 查询药物信息 | SQL 数据库 | 查询 `Medication` 表验证药物存在且激活 | 1185-1189 |
| | 检查今日服用记录 | SQL 数据库 | 查询 `MedicationLog` 表检查今日已记录次数 | 1200-1203 |
| | 创建服用日志 | SQL 数据库 | 插入新 `MedicationLog` 记录 | 1211-1219 |
| | 记录服药事件 | MemMachine | 存储服药事件到情景记忆 | 1223-1227 |
| **POST /remember** | 手动存储记忆 | MemMachine | 直接调用 `mm.remember()` 存储情景记忆 | 1279 |
| **POST /chat** | 检索情景记忆 | MemMachine | 调用 `mm.retrieve()` 检索相关对话和事件记忆 | 1321, 1326 |
| | 检索语义记忆 | MemMachine | 调用 `mm.retrieve_semantic()` 检索用户语义信息 | 1330 |
| | 查询患者信息 | SQL 数据库 | 根据用户名查询 `Patient` 表 | 1340 |
| | 检查并重置过期药物 | SQL 数据库 | 调用 `check_and_reset_medications` 函数 | 1343 |
| | 获取激活药物 | SQL 数据库 | 查询 `Medication` 表获取 `active=True` 的药物 | 1347 |
| | 获取未完成目标 | SQL 数据库 | 查询 `Goal` 表获取 `completed=False` 的目标 | 1350 |
| | 获取今日服用日志 | SQL 数据库 | 查询 `MedicationLog` 表计算今日药物状态 | 1359-1362 |
| | 补充档案信息（家庭信息） | SQL 数据库 | 从 `Patient` 表读取 `family_info` 字段 | 1415-1416 |
| | 补充档案信息（兴趣爱好） | SQL 数据库 | 从 `Patient` 表读取 `hobbies` 字段 | 1418-1419 |
| | 补充档案信息（紧急联系人） | SQL 数据库 | 从 `Patient` 表读取紧急联系人信息 | 1421-1427 |
| | 提取并存储新事实 | MemMachine | 调用 LLM 提取对话中的事实，存储到情景记忆 | 1516-1528 |
| | 检测目标完成 | SQL 数据库 | 查询 `Goal` 表，更新完成状态 | 1560-1568 |
| | 记录目标完成事件 | MemMachine | 存储目标完成事件到情景记忆 | 1573 |
| | 提取档案信息 | MemMachine | 调用 LLM 提取永久性事实，存储到档案记忆 | 1595-1616 |
| | 记录情感检查 | MemMachine | 如果检测到情感关键词，存储到情景记忆 | 1625-1629 |
| **check_and_reset_medications** | 查询激活药物 | SQL 数据库 | 查询 `Medication` 表获取 `active=True` 的药物 | 125-128 |
| | 更新药物状态 | SQL 数据库 | 如果药物过期，更新 `active=False` | 134-142 |

---

## 数据来源分类总结

### 主要从 SQL 数据库获取的信息

1. **患者基本信息**
   - 用户名、密码、全名
   - 家庭信息、兴趣爱好
   - 紧急联系人姓名和电话

2. **药物管理**
   - 药物名称、服用次数、服用时间
   - 药物说明、激活状态
   - 药物开始/结束日期

3. **目标管理**
   - 目标文本、完成状态
   - 创建时间、完成时间

4. **服用日志**
   - 每日服用记录
   - 服用时间、是否已服用

### 主要从 MemMachine 获取的信息

1. **情景记忆（Episodic Memory）**
   - 历史对话内容
   - 事件记录（登录、注册、服药、目标完成等）
   - 情感检查记录

2. **档案记忆（Profile Memory）**
   - 用户偏好（喜欢什么、不喜欢什么）
   - 个人信息（从对话中学习到的）
   - 关系信息（家庭成员、朋友等）
   - 医疗信息（药物信息、目标信息，作为补充）

### 混合使用场景

**`/chat` 端点**是最复杂的混合场景：

1. **从 MemMachine 获取**：
   - 历史对话记忆（情景记忆）
   - 用户偏好和档案信息（档案记忆）

2. **从 SQL 数据库获取**：
   - 患者基本信息（作为档案记忆的备份）
   - 当前激活的药物列表
   - 今日药物服用状态
   - 未完成的目标列表

3. **存储到 MemMachine**：
   - 从对话中提取的新事实（情景记忆）
   - 学习到的用户偏好（档案记忆）
   - 目标完成事件（情景记忆）
   - 情感检查记录（情景记忆）

---

## 设计模式说明

### 为什么使用双重存储？

1. **SQL 数据库**：存储结构化、需要精确查询和更新的数据
   - 患者注册信息（需要唯一性约束）
   - 药物处方（需要精确的时间管理）
   - 目标管理（需要状态跟踪）
   - 服用日志（需要精确的时间记录）

2. **MemMachine**：存储非结构化、语义化的记忆
   - 对话历史（语义搜索）
   - 用户偏好（从对话中学习）
   - 事件记录（时间线记忆）
   - 档案信息（永久性事实）

### 数据同步策略

- **注册时**：同时写入数据库和 MemMachine
- **聊天时**：从 MemMachine 检索记忆，从数据库获取结构化信息，然后合并
- **学习时**：从对话中提取新信息，只存储到 MemMachine（不写回数据库）

---

## 关键函数说明

### `check_and_reset_medications(patient_id)`
- **数据来源**：SQL 数据库
- **操作**：查询和更新 `Medication` 表
- **用途**：自动将过期的药物标记为非激活状态

### `extract_and_route_memories(user_id, user_message, assistant_reply)`
- **数据来源**：无（使用 LLM 分析）
- **存储目标**：MemMachine
- **用途**：从对话中提取事实信息，决定存储到哪个用户的记忆

### `should_attempt_extraction(message)`
- **数据来源**：无（纯逻辑判断）
- **用途**：快速判断消息是否可能包含值得存储的信息，避免不必要的 LLM 调用

---

## 总结

- **SQL 数据库**：负责结构化数据的精确管理（CRUD 操作）
- **MemMachine**：负责语义化记忆的存储和检索（用于 AI 对话上下文）
- **混合使用**：在 `/chat` 端点中，两者结合使用，提供完整的个性化对话体验

---

## 🐳 Docker 部署注意事项

当使用 Docker 部署时，需要注意以下几点：

### 环境变量配置

在 Docker 环境中，环境变量通过 `.env` 文件挂载到容器中：

- `OPENAI_API_KEY` - 通过环境变量注入到后端容器
- `OPENAI_MODEL` - 通过环境变量注入到后端容器
- `MEMMACHINE_BASE_URL` - 后端容器中配置 MemMachine 服务地址

### 服务依赖关系

MemoryCare 依赖外部的 MemMachine 服务来存储和检索记忆：

- **MemMachine 服务**：必须在 MemoryCare 之前启动
- **启动顺序**：先启动 MemMachine → 再启动 MemoryCare Docker 容器
- **连接地址**：Docker 容器通过 `http://172.17.0.1:8080` 访问宿主机上的 MemMachine 服务

#### 安装和启动 MemMachine 服务

MemMachine 服务需要单独安装和启动：

1. **克隆或访问 MemMachine 仓库**
   ```bash
   cd /memverge/MeetUp/MemMachine-MemMachine-dab4fdf
   ```

2. **配置环境变量**
   ```bash
   # 复制示例环境文件
   cp sample_configs/env.dockercompose .env
   
   # 编辑 .env 文件，添加你的 OpenAI API 密钥
   # OPENAI_API_KEY=your_openai_api_key_here
   ```

3. **配置 MemMachine 服务**
   ```bash
   # 复制示例配置文件
   cp sample_configs/episodic_memory_config.sample configuration.yml
   
   # 编辑 configuration.yml 文件，更新以下内容：
   # - 替换 <YOUR_API_KEY> 为你的 OpenAI API 密钥
   # - 替换 <YOUR_PASSWORD_HERE> 为你的 Neo4j 密码
   # - 确保 host 设置为 'postgres' 和 'neo4j'（Docker 网络中的服务名）
   ```

4. **启动 MemMachine 服务**
   ```bash
   # 使用启动脚本（推荐）
   ./memmachine-compose.sh
   
   # 或者直接使用 docker-compose
   docker-compose up -d
   ```

5. **验证 MemMachine 服务运行状态**
   ```bash
   curl http://localhost:8080/health
   ```

### 服务间通信

在 Docker Compose 环境中：

- **后端服务**（backend）：运行在 `http://localhost:8000`
- **前端服务**（frontend）：运行在 `http://localhost:8501`
- **MemMachine 服务**：需要单独启动，后端通过 `http://172.17.0.1:8080` 访问

### 数据持久化

- `app.db` 数据库文件通过 Docker 卷挂载到宿主机
- `.env` 配置文件通过 Docker 卷挂载到容器中

### 端口映射

- 容器内后端端口：8000 → 宿主机端口：8000
- 容器内前端端口：8501 → 宿主机端口：8501

### 启动脚本

使用 `docker-compose.sh` 脚本可以一键启动所有服务：

```bash
# 1. 确保 MemMachine 服务正在运行
curl http://localhost:8080/health

# 2. 给启动脚本添加执行权限
chmod +x docker-compose.sh

# 3. 启动所有服务
./docker-compose.sh
```