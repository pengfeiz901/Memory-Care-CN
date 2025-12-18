# memorycare_app/utils/memmachine_client.py
"""
MemMachine 客户端模块

本模块封装了与 MemMachine 持久化记忆服务的交互。
MemMachine 是一个外部服务，用于存储和检索用户的长期记忆。

核心功能：
1. 存储情景记忆（episodic memory）：对话、事件等临时性记忆
2. 存储档案记忆（profile memory）：用户偏好、个人信息等永久性记忆
3. 检索记忆：根据查询条件搜索相关记忆
"""

import os
import uuid
import json
from typing import List, Dict, Any, Optional
import requests

# MemMachine 服务的基础 URL
# 从环境变量 MEMMACHINE_BASE_URL 读取，如果未设置则使用默认值 localhost:8080
BASE_URL = os.getenv("MEMMACHINE_BASE_URL", "http://localhost:8080")


class MemMachine:
    """
    MemMachine 客户端类
    
    提供与 MemMachine 服务交互的所有方法，包括存储和检索记忆。
    """
    
    def __init__(self, base_url: Optional[str] = None):
        """
        初始化 MemMachine 客户端
        
        参数:
            base_url: 可选，MemMachine 服务的 URL
                     如果未提供，使用环境变量或默认值
        """
        # 使用提供的 base_url，或回退到环境变量/默认值
        self.base_url = base_url or BASE_URL

    def health(self) -> Dict[str, Any]:
        """
        检查 MemMachine 服务的健康状态
        
        返回:
            Dict[str, Any]: 服务健康状态信息
            
        异常:
            如果服务不可用，会抛出 requests.HTTPError
        """
        # 发送 GET 请求到健康检查端点
        r = requests.get(f"{self.base_url}/health", timeout=10)
        # 如果状态码不是 2xx，抛出异常
        r.raise_for_status()
        # 返回 JSON 响应
        return r.json()

    def remember(self, user_id: str, text: str, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        存储一条情景记忆（episodic memory）
        
        情景记忆用于存储临时性的事件和对话，如：
        - 用户今天说了什么
        - 发生了什么事情
        - 对话历史
        
        参数:
            user_id: 用户唯一标识符（通常是用户名）
            text: 要存储的记忆内容文本
            tags: 可选，标签列表，用于分类和检索，如 ["medication_log", "emotional"]
            
        返回:
            Dict[str, Any]: MemMachine 返回的响应数据
            
        异常:
            如果存储失败，会抛出 requests.HTTPError
        """
        # 构建 MemMachine API 请求负载
        payload = {
            # 会话信息：标识这次记忆存储的上下文
            "session": {
                "group_id": user_id,  # 用户组 ID，用于组织相关记忆
                "agent_id": ["memorycare_app"],  # 应用标识符
                "user_id": [user_id],  # 用户 ID 列表
                #"session_id": str(uuid.uuid4())  # 唯一会话 ID
                "session_id": user_id  # 唯一会话 ID
            },
            "producer": user_id,  # 记忆的生产者（应用名称）
            "produced_for": user_id,  # 记忆的目标用户
            "episode_content": text,  # 记忆的实际内容
            "episode_type": "memory_entry",  # 记忆类型
            "metadata": {
                "tags": tags or [],  # 标签列表，用于分类
                "actual_user_id": user_id  # 实际用户 ID（用于过滤）
            }
        }

        # 发送 POST 请求到 MemMachine 的记忆存储端点
        print(f"[INFO - remember()] Storing memory for {user_id} ...")
        print(f"[INFO - remember()] Payload: {json.dumps(payload, indent=4)}")
        r = requests.post(f"{self.base_url}/v1/memories", json=payload, timeout=20)
        print(f"[INFO - remember()] Response: {r.text}")
        # 检查响应状态，如果不是 2xx 则抛出异常
        r.raise_for_status()
        # 返回 JSON 响应
        return r.json()

    def remember_profile(self, user_id: str, key: str, value: str, category: Optional[str] = None) -> Dict[str, Any]:
        """
        存储一条档案记忆（profile memory）
        
        档案记忆用于存储永久性的用户信息，如：
        - 用户偏好（喜欢什么、不喜欢什么）
        - 个人信息（家庭成员、兴趣爱好）
        - 医疗信息（药物、过敏史）
        
        参数:
            user_id: 用户唯一标识符
            key: 记忆的键名，如 "favorite_food"、"emergency_contact"
            value: 记忆的值，如 "pizza"、"John - 123-456-7890"
            category: 可选，记忆分类，如 "personal"、"medical"、"preference"
            
        返回:
            Dict[str, Any]: 包含 "ok" 键的字典，表示存储是否成功
                           如果失败，可能包含 "error" 键
        """
        # 构建档案记忆的请求负载
        payload = {
            "session": {
                "group_id": "memorycare_group",  # 使用固定的组 ID 用于档案记忆
                "agent_id": ["memorycare_app"],
                "user_id": [user_id],
                #"session_id": str(uuid.uuid4())
                "session_id": user_id
            },
            "producer": user_id,
            "produced_for": user_id,
            "episode_content": f"{key}: {value}",  # 将键值对存储为文本内容
            "episode_type": category or "profile_info",  # 使用分类作为类型
            "metadata": {
                "type": "profile",  # 标记为档案类型
                "key": key,  # 存储键名
                "value": value,  # 存储值
                "category": category or "personal",  # 分类
                "actual_user_id": user_id  # 实际用户 ID
            }
        }
        print(f"[INFO - remember_profile()] Storing profile memory for {user_id} ...")
        print(f"[INFO - remember_profile()] Payload: {json.dumps(payload, indent=4)}")
        
        try:
            # 发送 POST 请求到档案记忆端点
            r = requests.post(f"{self.base_url}/v1/memories/profile", json=payload, timeout=20)
            print(f"[INFO - remember_profile()] Response: {r.text}")
            
            # 检查响应状态码
            if r.status_code not in (200, 201):
                # 如果失败，打印警告信息
                print("[WARN] profile write failed:", r.text)
            
            # 返回成功状态
            return {"ok": r.status_code in (200, 201)}
        except Exception as e:
            # 捕获异常并返回错误信息
            print("[ERROR] profile write exception:", e)
            return {"ok": False, "error": str(e)}

    def retrieve(self, user_id: str, query: Optional[str] = None, top_k: int = 10) -> list:
        """
        检索用户的情景记忆
        
        根据查询条件搜索并返回相关的记忆。支持语义搜索，可以理解查询的意图。
        
        参数:
            user_id: 用户唯一标识符
            query: 可选，搜索查询文本，如 "medication"、"family"
                  如果为 None，返回所有记忆
            top_k: 返回的最大记忆数量，默认 10
                   注意：实际请求时会请求 top_k * 3 条，然后过滤后返回 top_k 条
            
        返回:
            list: 记忆对象列表，每个对象包含记忆内容和元数据
                  如果检索失败或没有匹配的记忆，返回空列表
                  
        记忆过滤:
            - 只返回属于指定用户的记忆（通过 actual_user_id 过滤）
            - 防止用户看到其他用户的记忆
            
        响应格式处理:
            MemMachine 返回的格式可能是嵌套的：
            {"status": 0, "content": {"episodic_memory": [[], [{...}, {...}], [""]]}}
            本方法会处理多种可能的响应格式
        """
        import uuid

        # 如果查询为空，使用默认查询
        if not query:
            query = "all memories"

        # 构建搜索请求负载
        payload = {
            "session": {
                "group_id": user_id,
                "agent_id": ["memorycare_app"],
                "user_id": [user_id],
                #"session_id": str(uuid.uuid4())
                "session_id": user_id
            },
            "query": query,  # 搜索查询文本
            "limit": top_k * 3,  # 请求更多结果以便过滤后仍有足够数量
        }

        url = f"{self.base_url}/v1/memories/search"
        print(f"[INFO - retrieve()] Retrieving memories for {user_id} ...")
        print(f"[INFO - retrieve()] Payload: {json.dumps(payload, indent=4)}")

        try:
            # 发送 POST 请求到搜索端点
            r = requests.post(url, json=payload, timeout=20)
            r.raise_for_status()
            data = r.json()

            results = []

            # 处理 MemMachine 的嵌套响应格式
            # 格式：{"content": {"episodic_memory": [[], [{...}, {...}], [""]]}}
            # 实际记忆在中间列表中（索引 1）
            if (
                isinstance(data, dict)
                and "content" in data
                and "episodic_memory" in data["content"]
            ):
                episodic = data["content"]["episodic_memory"]
                #print(f"[RETRIEVE DEBUG] Episodic: {json.dumps(episodic, indent=4)}")

                # episodic 是 [[], [{...}, {...}], [""]] 格式
                if isinstance(episodic, list) and len(episodic) > 1:
                    # 同时获取 episodic[0] 和 episodic[1] 的内容，合并到同一个列表中
                    results = []
                    if isinstance(episodic[0], list):
                        results.extend(episodic[0])
                    if len(episodic) > 1 and isinstance(episodic[1], list):
                        results.extend(episodic[1])
                    print(f"[RETRIEVE DEBUG] Combined results from episodic[0] and episodic[1]: {json.dumps(results, indent=4)}")

            # 回退处理：如果响应已经是字典列表格式
            elif isinstance(data, list):
                results = data
                print(f"[RETRIEVE DEBUG] Data: {data}")
            # 回退处理：如果响应包含 "results" 键
            elif isinstance(data, dict) and "results" in data:
                results = data["results"]
                print(f"[RETRIEVE DEBUG] Results: {results}")
            else:
                # 无法识别的响应格式
                print("[WARN] Unrecognized episodic response shape:", data)
                return []
            
            # 过滤记忆：只返回属于当前用户的记忆
            filtered = []
            for mem in results:
                if isinstance(mem, dict):
                    # 调试信息：打印记忆内容预览
                    content_preview = mem.get("content", "")[:50]
                    # 获取用户元数据
                    metadata = mem.get("user_metadata", {})
                    # 获取存储时的实际用户 ID
                    stored_user = metadata.get("actual_user_id")
                    
                    # 调试输出（开发时使用）
                    print(f"[RETRIEVE DEBUG] Content: '{content_preview}...'")
                    #print(f"[RETRIEVE DEBUG]   Metadata: {metadata}")
                    #print(f"[RETRIEVE DEBUG]   Stored user: {stored_user}")
                    #print(f"[RETRIEVE DEBUG]   Requested user: {user_id}")
                    #print(f"[RETRIEVE DEBUG]   Match: {stored_user == user_id}")
                    
                    # 只包含属于当前用户的记忆
                    if stored_user == user_id:
                        filtered.append(mem)
                        print(f"[RETRIEVE DEBUG]   ✓ INCLUDED")
                    else:
                        # 过滤掉其他用户的记忆
                        print(f"[RETRIEVE DEBUG]   ✗ FILTERED OUT")
        
            print(f"[RETRIEVE] After filtering: {len(filtered)} memories for {user_id}")
            
            # 返回前 top_k 条记忆
            return filtered[:top_k]

        except Exception as e:
            # 捕获异常并返回空列表
            print("[ERROR] Retrieval exception:", e)
            return []
    
    def retrieve_profile(self, user_id: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        检索用户的档案记忆（永久性信息）
        
        参数:
            user_id: 用户唯一标识符
            category: 可选，记忆分类过滤，如 "personal"、"medical"
                     如果为 None，返回所有档案记忆
            
        返回:
            List[Dict[str, Any]]: 档案记忆对象列表
                                 每个对象包含键值对信息和元数据
                                 如果检索失败，返回空列表
        """
        # 构建档案记忆搜索请求负载
        payload = {
            "session": {
                "group_id": "memorycare_group",  # 使用固定的组 ID
                "agent_id": ["memorycare_app"],
                "user_id": [user_id],
                #"session_id": str(uuid.uuid4())
                "session_id": user_id
            },
            "query": "profile information",  # 搜索查询
            "filter": {
                "produced_for_id": user_id,  # 过滤条件：只返回该用户的记忆
                "additionalProp1": {}  # 额外的过滤属性（占位符）
            },
            "limit": 50  # 最多返回 50 条档案记忆
        }
        
        url = f"{self.base_url}/v1/memories/profile/search"
        print(f"[INFO - retrieve_profile()] Retrieving profile memories for {user_id} ...")
        print(f"[INFO - retrieve_profile()] Payload: {json.dumps(payload, indent=4)}")
        
        try:
            # 发送 POST 请求到档案记忆搜索端点
            r = requests.post(url, json=payload, timeout=20)
            r.raise_for_status()
            data = r.json()
            
            # 处理多种可能的响应格式（类似情景记忆的处理）
            # 格式 1：嵌套格式 {"content": {"profile_memory": [[], [{...}], [""]]}}
            if isinstance(data, dict) and "content" in data:
                if "profile_memory" in data["content"]:
                    pm = data["content"]["profile_memory"]
                    print(f"[RETRIEVE DEBUG] Profile: {json.dumps(pm, indent=4)}")

                    # 如果是嵌套列表格式，提取中间列表
                    if isinstance(pm, list) and len(pm) > 1 and isinstance(pm[1], list):
                        # 过滤：只返回属于当前用户的记忆
                        return [m for m in pm[1] if isinstance(m, dict) and m.get("produced_for_id") == user_id]
                    elif isinstance(pm, list):
                        # 如果已经是列表格式，直接过滤
                        return [m for m in pm if isinstance(m, dict)]
            
            # 格式 2：包含 "results" 键
            if isinstance(data, dict) and "results" in data:
                return [m for m in data["results"] if m.get("produced_for_id") == user_id]
            
            # 格式 3：直接是列表格式
            if isinstance(data, list):
                return [m for m in data if isinstance(m, dict) and m.get("produced_for_id") == user_id]
            
            # 无法识别的响应格式
            print("[WARN] Unrecognized profile response:", data)
            return []
        except Exception as e:
            # 捕获异常并返回空列表
            print("[ERROR] profile retrieval exception:", e)
            return []
    
    def store_dual_memory(self, user_id: str, episodic_text: str, profile_data: Optional[Dict[str, Any]] = None, tags: Optional[List[str]] = None):
        """
        同时存储情景记忆和档案记忆
        
        这是一个便捷方法，用于在一次操作中同时存储两种类型的记忆。
        例如：用户注册时，既需要记录注册事件（情景记忆），
        也需要存储个人信息（档案记忆）。
        
        参数:
            user_id: 用户唯一标识符
            episodic_text: 情景记忆的文本内容（事件、对话等）
            profile_data: 可选，档案记忆的字典数据
                         格式：{"key1": "value1", "key2": "value2", "category": "personal"}
                         注意：字典中的 "category" 键会被用作所有档案记忆的分类
            tags: 可选，情景记忆的标签列表
            
        使用示例:
            mm.store_dual_memory(
                user_id="alice",
                episodic_text="Alice signed up on 2024-01-01",
                profile_data={
                    "full_name": "Alice Smith",
                    "hobbies": "reading, hiking",
                    "category": "personal"
                },
                tags=["signup", "profile_creation"]
            )
        """
        # 步骤 1：存储情景记忆（事件记录）
        print(f"[INFO - store_dual_memory()] Storing dual memory for {user_id} ...")
        print(f"[INFO - store_dual_memory()] Episodic text: {episodic_text}")
        print(f"[INFO - store_dual_memory()] Profile data: {json.dumps(profile_data, indent=4)}")
        print(f"[INFO - store_dual_memory()] Tags: {tags}")
        self.remember(user_id=user_id, text=episodic_text, tags=tags)
        
        # 步骤 2：如果提供了档案数据，存储档案记忆
        if profile_data:
            # 遍历字典中的每个键值对
            for key, value in profile_data.items():
                # 跳过 "category" 键（它用于设置分类，不是要存储的数据）
                # 跳过空值
                if key != "category" and value:
                    # 获取分类，如果没有则使用默认值 "personal"
                    category = profile_data.get("category", "personal")
                    # 存储档案记忆
                    self.remember_profile(
                        user_id=user_id,
                        key=key,
                        value=str(value),  # 确保值为字符串
                        category=category
                    )
