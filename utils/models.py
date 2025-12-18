# memorycare_app/utils/models.py
"""
数据库模型定义模块

本模块使用 SQLModel 定义数据库表结构，包含以下四个核心模型：
1. Patient（患者）：存储患者的基本信息和账户信息
2. Medication（药物）：存储患者需要服用的药物信息
3. MedicationLog（药物记录）：记录患者每次服药的情况
4. Goal（目标）：存储医生为患者设定的治疗目标

数据库关系说明：
- Patient（患者）与 Medication（药物）：一对多关系（一个患者可以有多个药物）
- Patient（患者）与 Goal（目标）：一对多关系（一个患者可以有多个目标）
- Medication（药物）与 MedicationLog（药物记录）：一对多关系（一个药物可以有多次服药记录）

使用 SQLModel 的好处：
- 同时支持 ORM（对象关系映射）和 Pydantic 验证
- 类型安全，支持 IDE 自动补全
- 自动生成数据库表结构
"""

from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship


class Patient(SQLModel, table=True):
    """
    患者模型（Patient）
    
    这是系统的核心用户模型，存储所有患者的基本信息。
    每个患者可以有多个药物（Medication）和多个目标（Goal）。
    
    数据库表名：patient
    """
    
    # 主键：患者 ID，自动递增，创建新患者时由数据库自动分配
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # 用户名：用于登录的唯一标识符
    # index=True 表示在数据库中对该字段创建索引，提高查询速度
    # unique=True 表示该字段值必须唯一，不能有重复的用户名
    username: str = Field(index=True, unique=True)
    
    # 密码：患者登录密码（注意：实际应用中应该存储哈希值，而不是明文）
    password: str
    
    # 全名：患者的真实姓名，用于显示和识别
    full_name: str
    
    # 家庭信息：可选字段，存储患者的家庭背景、家庭成员等信息
    # 用于 AI 助手更好地了解患者的生活环境
    family_info: Optional[str] = None
    
    # 紧急联系人姓名：可选字段，用于紧急情况下的联系
    emergency_contact_name: Optional[str] = None
    
    # 紧急联系人电话：可选字段，与紧急联系人姓名配套使用
    emergency_contact_phone: Optional[str] = None
    
    # 兴趣爱好：可选字段，存储患者的兴趣爱好
    # 用于 AI 助手与患者进行更个性化的对话，建立更好的关系
    hobbies: Optional[str] = None

    # 关系字段：一个患者可以有多个药物
    # Relationship 定义 ORM 关系，back_populates="patient" 表示在 Medication 模型中也有对应的 patient 关系
    # 使用字符串 "Medication" 是因为此时 Medication 类还未定义，避免前向引用问题
    medications: List["Medication"] = Relationship(back_populates="patient")
    
    # 关系字段：一个患者可以有多个目标
    # 同样使用字符串 "Goal" 避免前向引用问题
    goals: List["Goal"] = Relationship(back_populates="patient")


class Medication(SQLModel, table=True):
    """
    药物模型（Medication）
    
    存储患者需要服用的药物信息，包括药物名称、服用频率、具体时间等。
    每个药物属于一个患者，可以有多个服药记录（MedicationLog）。
    
    数据库表名：medication
    """
    
    # 主键：药物 ID，自动递增
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # 外键：患者 ID，关联到 Patient 表的 id 字段
    # foreign_key="patient.id" 指定外键关系
    # index=True 创建索引，因为经常需要通过 patient_id 查询某个患者的所有药物
    patient_id: int = Field(foreign_key="patient.id", index=True)
    
    # 药物名称：例如 "阿司匹林"、"维生素 D" 等
    name: str
    
    # 每天服用次数：默认为 1 次，表示该药物每天需要服用几次
    # 例如：3 表示每天 3 次
    times_per_day: int = 1
    
    # 具体服用时间：可选字段，存储具体的服用时间点
    # 格式通常是逗号分隔的时间字符串，例如 "09:00,14:00,20:00"
    # 如果为空，则按照 times_per_day 均匀分配时间
    specific_times: Optional[str] = None
    
    # 服用说明：可选字段，存储药物的服用说明
    # 例如："饭后服用"、"用水送服"、"避免与牛奶同服" 等
    instructions: Optional[str] = None
    
    # 是否激活：布尔值，表示该药物是否还在使用中
    # True 表示患者当前正在服用此药物
    # False 表示该药物已停用（例如疗程结束或医生要求停药）
    active: bool = True
    
    # 开始日期：药物开始服用的日期和时间
    # default_factory=datetime.now 表示创建记录时自动设置为当前时间
    start_date: datetime = Field(default_factory=datetime.now)
    
    # 结束日期：可选字段，药物停止服用的日期和时间
    # 如果为 None，表示该药物仍在服用中
    # 当医生停用药物时，会设置此字段
    end_date: Optional[datetime] = None
    
    # 创建时间：记录创建该药物记录的时间
    # 用于追踪药物信息何时被添加到系统中
    created_at: datetime = Field(default_factory=datetime.now)
    
    # 关系字段：反向关联到所属的患者
    # back_populates="medications" 与 Patient 模型中的 medications 字段对应
    patient: Patient = Relationship(back_populates="medications")
    
    # 关系字段：一个药物可以有多个服药记录
    # 每次患者服药时，都会创建一条 MedicationLog 记录
    logs: List["MedicationLog"] = Relationship(back_populates="medication")

class MedicationLog(SQLModel, table=True):
    """
    药物记录模型（MedicationLog）
    
    记录患者每次服药的情况，包括是否服用、服用时间等。
    每条记录关联到一个具体的药物（Medication）。
    
    数据库表名：medicationlog
    
    用途：
    - 追踪患者的服药依从性（是否按时服药）
    - 生成服药历史报告
    - 帮助医生评估治疗效果
    """
    
    # 主键：记录 ID，自动递增
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # 外键：药物 ID，关联到 Medication 表的 id 字段
    # index=True 创建索引，因为经常需要通过 medication_id 查询某个药物的所有记录
    medication_id: int = Field(foreign_key="medication.id", index=True)
    
    # 日期：记录该服药记录的日期和时间
    # default_factory=datetime.now 表示创建记录时自动设置为当前时间
    # 通常用于记录"应该在什么时候服药"或"实际什么时候服药的"
    date: datetime = Field(default_factory=datetime.now)
    
    # 实际服用时间：可选字段，存储患者实际服用药物的时间
    # 格式通常是 "HH:MM"，例如 "09:15"、"14:30" 等
    # 如果患者按时服药，此字段可能与 date 中的时间一致
    # 如果患者忘记服药或延迟服药，此字段会记录实际时间
    time_taken: Optional[str] = None
    
    # 是否已服用：布尔值，表示患者是否实际服用了药物
    # True 表示已服用，False 表示未服用（忘记或拒绝）
    # 这是最重要的字段，用于判断患者的服药依从性
    taken: bool = False

    # 关系字段：反向关联到所属的药物
    # Optional 表示在某些查询场景下可能不需要加载关联的药物对象
    # back_populates="logs" 与 Medication 模型中的 logs 字段对应
    medication: Optional["Medication"] = Relationship(back_populates="logs")


    



class Goal(SQLModel, table=True):
    """
    目标模型（Goal）
    
    存储医生为患者设定的治疗目标或康复目标。
    例如："每天散步 30 分钟"、"完成记忆训练游戏" 等。
    每个目标属于一个患者，可以标记为已完成。
    
    数据库表名：goal
    
    用途：
    - 帮助患者设定和追踪治疗目标
    - 评估患者的康复进度
    - AI 助手可以根据目标提供个性化的提醒和鼓励
    """
    
    # 主键：目标 ID，自动递增
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # 外键：患者 ID，关联到 Patient 表的 id 字段
    # index=True 创建索引，因为经常需要通过 patient_id 查询某个患者的所有目标
    patient_id: int = Field(foreign_key="patient.id", index=True)
    
    # 目标文本：目标的描述内容
    # 例如："晚饭后散步 10 分钟"、"完成今天的记忆训练"、"按时服用所有药物"
    text: str
    
    # 是否已完成：布尔值，表示该目标是否已经完成
    # False 表示目标还在进行中（活跃目标）
    # True 表示目标已经完成
    completed: bool = False
    
    # 创建时间：目标被创建的时间
    # default_factory=datetime.now 表示创建记录时自动设置为当前时间
    # 用于追踪目标何时被分配给患者
    created_at: datetime = Field(default_factory=datetime.now)
    
    # 完成时间：可选字段，目标完成的时间
    # 如果为 None，表示目标尚未完成
    # 当目标被标记为完成时，会设置此字段为当前时间
    # 用于分析患者完成目标所需的时间，评估康复进度
    completed_at: Optional[datetime] = None

    # 关系字段：反向关联到所属的患者
    # back_populates="goals" 与 Patient 模型中的 goals 字段对应
    patient: Patient = Relationship(back_populates="goals")
