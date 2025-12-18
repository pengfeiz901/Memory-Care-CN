# memorycare_app/utils/scheduler.py
"""
药物提醒调度器模块

本模块负责计算药物的下次服用时间，判断当前是否在服药时间窗口内。
支持两种模式：指定具体时间和自动平均分配。
"""

from __future__ import annotations
from datetime import datetime, time
from typing import List, Optional


def _parse_specific_times(csv_times: Optional[str]) -> List[time]:
    """
    解析逗号分隔的时间字符串为 time 对象列表
    
    参数:
        csv_times: 逗号分隔的时间字符串，如 "09:00,14:00,20:00"
        
    返回:
        List[time]: time 对象列表，如 [time(9, 0), time(14, 0), time(20, 0)]
        
    示例:
        _parse_specific_times("09:00,14:00,20:00")
        # 返回 [time(9, 0), time(14, 0), time(20, 0)]
        
    注意:
        - 无效的时间格式会被忽略（不抛出异常）
        - 空字符串或 None 返回空列表
    """
    # 如果输入为空，直接返回空列表
    if not csv_times:
        return []
    
    out = []
    # 按逗号分割时间字符串
    for t in csv_times.split(","):
        t = t.strip()  # 去除前后空格
        try:
            # 按冒号分割小时和分钟
            hh, mm = t.split(":")
            # 转换为 time 对象并添加到列表
            out.append(time(int(hh), int(mm)))
        except:
            # 如果解析失败（格式错误），跳过该时间
            pass
    return out


def next_due_window(now: datetime, times_per_day: int, specific_times: Optional[str]) -> Optional[str]:
    """
    判断当前是否在药物服用时间窗口内（±5 分钟）
    
    参数:
        now: 当前日期时间对象
        times_per_day: 每天需要服用的次数
        specific_times: 可选，逗号分隔的具体时间字符串，如 "09:00,14:00,20:00"
                      如果为 None，系统会根据 times_per_day 自动平均分配时间
        
    返回:
        Optional[str]: 如果在时间窗口内，返回友好的提醒消息字符串
                      如果不在时间窗口内，返回 None
        
    时间窗口:
        - 窗口大小：±5 分钟
        - 例如：如果设定时间为 09:00，则在 08:55-09:05 之间会返回提醒
        
    工作流程:
        1. 如果指定了具体时间，检查当前时间是否接近任何一个指定时间
        2. 如果未指定具体时间，将一天平均分成 times_per_day 个时间段
        3. 检查当前时间是否接近任何一个时间段
        4. 如果在窗口内，返回提醒消息；否则返回 None
        
    示例:
        # 指定时间模式
        next_due_window(datetime(2024, 1, 1, 9, 2), 3, "09:00,14:00,20:00")
        # 返回 "Medication time window right now (~09:00)."
        
        # 自动分配模式
        next_due_window(datetime(2024, 1, 1, 8, 0), 3, None)
        # 可能返回 "Medication time window right now (~08:00)."
    """
    # 如果每天服用次数小于等于 0，无需提醒
    if times_per_day <= 0:
        return None
    
    # 时间窗口大小：5 分钟（±5 分钟）
    window = 5  # minutes

    # 模式 1：如果指定了具体服用时间
    if specific_times:
        # 解析时间字符串为 time 对象列表
        for tt in _parse_specific_times(specific_times):
            # 将当前日期与指定时间组合，创建目标时间点
            # replace 方法将当前时间的小时、分钟、秒、微秒替换为指定值
            dose_dt = now.replace(hour=tt.hour, minute=tt.minute, second=0, microsecond=0)
            
            # 计算当前时间与目标时间的差值（以分钟为单位）
            delta = abs((dose_dt - now).total_seconds()) / 60
            
            # 如果差值在时间窗口内（≤5 分钟），返回提醒消息
            if delta <= window:
                return f"Medication time window right now (~{tt.strftime('%H:%M')})."
    else:
        # 模式 2：未指定具体时间，自动平均分配
        
        # 计算每个时间段之间的分钟间隔
        # 例如：3 次/天 = 每 8 小时一次 = 480 分钟
        minutes_per = int(24 * 60 / times_per_day)
        
        # 生成所有时间段的起始分钟数（从 0 点开始）
        # 例如：3 次/天 = [0, 480, 960] 分钟
        slots = [minutes_per * i for i in range(times_per_day)]
        
        # 将当前时间转换为从 0 点开始的分钟数
        # 例如：08:30 = 8*60 + 30 = 510 分钟
        now_min = now.hour * 60 + now.minute
        
        # 检查当前时间是否接近任何一个时间段
        for sm in slots:
            # 计算当前时间与时间段起始时间的差值（分钟）
            delta = abs(sm - now_min)
            
            # 如果差值在时间窗口内（≤5 分钟）
            if delta <= window:
                # 将分钟数转换回小时和分钟
                hh, mm = divmod(sm, 60)
                # 返回提醒消息
                return f"Medication time window right now (~{hh:02d}:{mm:02d})."
    
    # 不在任何时间窗口内，返回 None
    return None
