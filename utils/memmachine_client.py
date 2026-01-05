# memorycare_app/utils/memmachine_client.py
"""
MemMachine 客户端模块

本模块封装了与 MemMachine 持久化记忆服务的交互。
MemMachine 是一个外部服务，用于存储和检索用户的长期记忆。

核心功能：
1. 存储情景记忆（episodic memory）：对话、事件等临时性记忆
2. 存储语义记忆（semantic memory）：用户偏好、个人信息等永久性记忆
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
        r = requests.get(f"{self.base_url}/api/v2/health", timeout=10)
        # 如果状态码不是 2xx，抛出异常
        r.raise_for_status()
        # 返回 JSON 响应
        return r.json()

    def remember(self, user_id: str, text: str, tags: Optional[List[str]] = None, types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        存储记忆
        
        根据 types 参数决定存储到哪种类型的记忆中：
        - 如果 types 为空或未提供，记忆将存储到所有类型（情景和语义）
        - 如果 types 只包含 "episodic"，记忆将仅存储到情景记忆
        - 如果 types 只包含 "semantic"，记忆将仅存储到语义记忆
        - 如果 types 包含两者，记忆将存储到两种类型
        
        参数:
            user_id: 用户唯一标识符（通常是用户名）
            text: 要存储的记忆内容文本
            tags: 可选，标签列表，用于分类和检索，如 ["medication_log", "emotional"]
            types: 可选，记忆类型列表，如 ["episodic"], ["semantic"], 或 ["episodic", "semantic"]
                   如果未提供或为空，则存储到所有类型
                   
        返回:
            Dict[str, Any]: MemMachine 返回的响应数据
            
        异常:
            如果存储失败，会抛出 requests.HTTPError
        """
        # 确定要使用的记忆类型
        if types is None or len(types) == 0:
            # 如果未提供类型或为空，则存储到所有类型
            used_types = ["episodic", "semantic"]
        else:
            # 使用提供的类型
            used_types = types
            
        # 构建 MemMachine API 请求负载 for v2
        payload = {
            "org_id": "memorycare",  # 组织 ID
            "project_id": user_id,  # 项目 ID，使用用户 ID as project
            "types": used_types,
            "messages": [
                {
                    "content": text,  # 记忆的实际内容
                    "producer": user_id,  # 记忆的生产者（应用名称）
                    "produced_for": user_id,  # 记忆的目标用户
                    "role": "",
                    "metadata": {
                        "tags": ", ".join(tags or []),  # 标签字符串，用于分类 (v2 API expects string)
                        "actual_user_id": user_id  # 实际用户 ID（用于过滤）
                    }
                }
            ]
        }

        # 发送 POST 请求到 MemMachine 的记忆存储端点
        print(f"[INFO - remember()] Storing memory for {user_id} ...")
        print(f"[INFO - remember()] Payload: {json.dumps(payload, indent=4)}")
        r = requests.post(f"{self.base_url}/api/v2/memories", json=payload, timeout=20)
        print(f"[INFO - remember()] Response: {r.text}")
        # 检查响应状态，如果不是 2xx 则抛出异常
        r.raise_for_status()
        # 返回 JSON 响应
        return r.json()

    def remember_semantic(self, user_id: str, key: str, value: str, category: Optional[str] = None) -> Dict[str, Any]:
        """
        存储一条语义记忆（semantic memory）
        
        语义记忆用于存储永久性的用户信息，如：
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
        # 构建语义记忆的请求负载 for v2
        payload = {
            "org_id": "memorycare",  # 组织 ID
            "project_id": user_id,  # 项目 ID，使用用户 ID as project
            "types": [
                "semantic"
            ],
            "messages": [
                {
                    "content": f"{key}: {value}",  # 将键值对存储为文本内容
                    "producer": user_id,
                    "produced_for": user_id,
                    "role": "",
                    "metadata": {
                        "key": key,  # 存储键名
                        "value": value,  # 存储值
                        "category": category or "personal",  # 分类
                        "actual_user_id": user_id  # 实际用户 ID
                    }
                }
            ]
        }
        print(f"[INFO - remember_semantic()] Storing semantic memory for {user_id} ...")
        print(f"[INFO - remember_semantic()] Payload: {json.dumps(payload, indent=4)}")
        
        try:
            # 发送 POST 请求到语义记忆端点
            r = requests.post(f"{self.base_url}/api/v2/memories", json=payload, timeout=20)
            print(f"[INFO - remember_semantic()] Response: {r.text}")
            
            # 检查响应状态码
            if r.status_code in (200, 201):
                # 返回成功状态
                return {"ok": True}
            else:
                # 如果失败，打印警告信息
                print("[WARN] semantic write failed:", r.text)
                return {"ok": False}
        except Exception as e:
            # 捕获异常并返回错误信息
            print("[ERROR] semantic write exception:", e)
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

        # 构建搜索请求负载 for v2
        payload = {
            "org_id": "memorycare",  # 组织 ID
            "project_id": user_id,  # 项目 ID，使用用户 ID as project
            "query": query,  # 搜索查询文本
            "top_k": top_k * 3,  # 请求更多结果以便过滤后仍有足够数量
            "filter": f"metadata.actual_user_id={user_id}",  # Filter to only return memories for this user
            "types": [
                "episodic"
            ]
        }

        url = f"{self.base_url}/api/v2/memories/search"
        print(f"[INFO - retrieve()] Retrieving memories for {user_id} ...")
        print(f"[INFO - retrieve()] Payload: {json.dumps(payload, indent=4)}")

        try:
            # 发送 POST 请求到搜索端点
            r = requests.post(url, json=payload, timeout=20)
            r.raise_for_status()
            data = r.json()

            results = []

            # 处理 MemMachine v2 response format
            # Format: {"status": 0, "content": {"episodic_memory": {"long_term_memory": {"episodes": [...]}, "short_term_memory": {"episodes": [...]}}}}
            if (
                isinstance(data, dict)
                and "content" in data
                and "episodic_memory" in data["content"]
            ):
                episodic_memory = data["content"]["episodic_memory"]
                long_term_episodes = episodic_memory.get("long_term_memory", {}).get("episodes", [])
                short_term_episodes = episodic_memory.get("short_term_memory", {}).get("episodes", [])
                
                # Combine both long term and short term episodes
                all_episodes = long_term_episodes + short_term_episodes
                results = all_episodes
                print(f"[RETRIEVE DEBUG] Episodes: {json.dumps(results, indent=4)}")

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
            
            # 过滤记忆：只返回属于当前用户的记忆 (additional filtering in case server-side filter didn't work)
            filtered = []
            for mem in results:
                if isinstance(mem, dict):
                    # 调试信息：打印记忆内容预览
                    content_preview = mem.get("content", "")[:50]
                    # 获取元数据
                    metadata = mem.get("metadata", {})
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
    
    def retrieve_semantic(self, user_id: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        检索用户的语义记忆（永久性信息）
        
        参数:
            user_id: 用户唯一标识符
            category: 可选，记忆分类过滤，如 "personal"、"medical"
                     如果为 None，返回所有语义记忆
            
        返回:
            List[Dict[str, Any]]: 语义记忆对象列表
                                 每个对象包含键值对信息和元数据
                                 如果检索失败，返回空列表
        """
        # 构建语义记忆搜索请求负载 for v2
        payload = {
            "org_id": "memorycare",  # 组织 ID
            "project_id": user_id,  # 项目 ID，使用用户 ID as project
            "query": "",  # 搜索查询
            "top_k": 50,  # 最多返回 50 条语义记忆
            "filter": f"metadata.actual_user_id={user_id}",  # Filter to only return semantic memories for this user
            "types": [
                "semantic"
            ]
        }
        
        url = f"{self.base_url}/api/v2/memories/search"
        print(f"[INFO - retrieve_semantic()] Retrieving semantic memories for {user_id} ...")
        print(f"[INFO - retrieve_semantic()] Payload: {json.dumps(payload, indent=4)}")
        
        try:
            # 发送 POST 请求到语义记忆搜索端点
            r = requests.post(url, json=payload, timeout=20)
            r.raise_for_status()
            data = r.json()
            
            # 处理多种可能的响应格式（类似情景记忆的处理）
            # 格式 1：v2 format {"status": 0, "content": {"episodic_memory": {...}, "semantic_memory": [...]}}
            if isinstance(data, dict) and "content" in data:
                if "semantic_memory" in data["content"]:
                    semantic_memories = data["content"]["semantic_memory"]
                    print(f"[RETRIEVE DEBUG] Semantic Memories: {json.dumps(semantic_memories, indent=4)}")

                    # 过滤：只返回属于当前用户的语义记忆
                    return [m for m in semantic_memories if isinstance(m, dict) and 
                           m.get("metadata", {}).get("actual_user_id") == user_id and 
                           m.get("metadata", {}).get("type") == "semantic"]
            
            # 格式 2：包含 "results" 键
            if isinstance(data, dict) and "results" in data:
                return [m for m in data["results"] if 
                       m.get("metadata", {}).get("actual_user_id") == user_id and 
                       m.get("metadata", {}).get("type") == "semantic"]
            
            # 格式 3：直接是列表格式
            if isinstance(data, list):
                return [m for m in data if isinstance(m, dict) and 
                       m.get("metadata", {}).get("actual_user_id") == user_id and 
                       m.get("metadata", {}).get("type") == "semantic"]
            
            # 无法识别的响应格式
            print("[WARN] Unrecognized semantic response:", data)
            return []
        except Exception as e:
            # 捕获异常并返回空列表
            print("[ERROR] semantic retrieval exception:", e)
            return []

