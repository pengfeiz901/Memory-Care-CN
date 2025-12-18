# memorycare_app/utils/db.py
"""
数据库连接和初始化模块

本模块负责数据库引擎的创建、会话管理和表结构的初始化。
使用 SQLite 作为数据库，SQLModel 作为 ORM 框架。
"""

from sqlmodel import SQLModel, create_engine, Session

# 数据库连接 URL：使用 SQLite 数据库，文件名为 app.db
# SQLite 是轻量级嵌入式数据库，适合单机应用
DB_URL = "sqlite:///app.db"

# 创建数据库引擎：用于连接数据库和执行 SQL 操作
# echo=False 表示不在控制台输出 SQL 语句（设为 True 可用于调试）
engine = create_engine(DB_URL, echo=False)


def get_session() -> Session:
    """
    获取数据库会话对象
    
    返回:
        Session: SQLModel 会话对象，用于执行数据库操作
        
    使用示例:
        with get_session() as session:
            patient = session.get(Patient, patient_id)
    """
    return Session(engine)


def create_db_and_tables():
    """
    创建数据库和所有表结构
    
    此函数会检查数据库文件是否存在，如果不存在则创建。
    然后根据模型中定义的表结构创建所有数据表。
    
    注意：
        - 此函数应该在应用启动时调用一次
        - 如果表已存在，不会重复创建
        - 不会删除或修改现有表结构（需要手动迁移）
    """
    # 导入所有模型类，确保 SQLModel 能够识别所有表定义
    # 延迟导入避免循环依赖
    from .models import Patient, Medication, Goal, MedicationLog
    
    # 根据所有已注册的 SQLModel 类创建对应的数据表
    # 如果表已存在，此操作不会报错
    SQLModel.metadata.create_all(engine)
