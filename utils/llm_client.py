# memorycare_app/utils/llm_client.py
"""
OpenAI LLM 客户端模块

本模块封装了与 OpenAI API 的交互，提供统一的聊天接口。
支持模型回退机制，如果首选模型不可用，会自动尝试备用模型。
"""

import os
import requests
import logging

# 配置日志记录器
logger = logging.getLogger(__name__)
# 只在根日志记录器未配置时才配置
if not logging.root.handlers:
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

# 确保加载 .env 文件（如果还没有加载）
# 这很重要，因为模块级别的环境变量读取可能在 load_dotenv() 之前执行
_dotenv_loaded = False
try:
    # 尝试导入 load_dotenv 函数
    from dotenv import load_dotenv  # type: ignore
    # 调用 load_dotenv() 加载 .env 文件
    # override=False 表示如果环境变量已存在，则不覆盖它们
    load_dotenv(override=False)
    _dotenv_loaded = True
    logger.debug("✅ 已加载 .env 文件")
except ImportError as e:
    # python-dotenv 未安装，这是正常的（如果 api/main.py 中已经加载了）
    logger.debug(f"dotenv 模块未找到（可能已在其他地方加载）: {e}")
except Exception as e:
    logger.warning(f"⚠️ 加载 .env 文件时出错：{type(e).__name__}: {e}")
    import traceback
    logger.debug(traceback.format_exc())

# 从环境变量获取 OpenAI API 密钥
# 如果未设置，将使用默认值（会导致 API 调用失败）
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "INSERT API KEY")

# 调试日志：记录 API Key 的加载状态（只显示前几个字符以保护隐私）
if OPENAI_API_KEY and OPENAI_API_KEY != "INSERT API KEY":
    api_key_preview = OPENAI_API_KEY[:8] + "..." if len(OPENAI_API_KEY) > 8 else "***"
    logger.info(f"✅ OPENAI_API_KEY 已加载（预览：{api_key_preview}）")
else:
    logger.error("❌ OPENAI_API_KEY 未设置或使用默认值")

# OpenAI API 基础 URL：默认为官方 API 地址
# 可以设置为自定义代理或兼容 OpenAI API 的服务
OPENAI_BASE = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

# 调试日志：记录 Base URL
logger.info(f"📡 OPENAI_BASE_URL = {OPENAI_BASE}")

# 首选模型：从环境变量读取，如果未设置则为空字符串
# 用户可以在 .env 文件中设置 OPENAI_MODEL 来指定首选模型
PREFERRED = os.getenv("OPENAI_MODEL", "").strip()

# 调试日志：记录模型配置
if PREFERRED:
    logger.info(f"🎯 首选模型 OPENAI_MODEL = '{PREFERRED}'")
else:
    logger.warning("⚠️ OPENAI_MODEL 未设置，将使用备用模型")

# 模型回退列表：包含首选模型和备用模型
# 如果首选模型不可用，会依次尝试列表中的其他模型
# 过滤掉空字符串，确保列表中只包含有效的模型名
FALLBACKS = [m for m in [PREFERRED, "qwen-max"] if m]

# 调试日志：记录最终的模型列表
logger.info(f"📋 模型回退列表：{FALLBACKS}")

# 检查所有环境变量
logger.debug("=" * 60)
logger.debug("环境变量检查：")
logger.debug(f"  OPENAI_API_KEY: {'已设置' if OPENAI_API_KEY and OPENAI_API_KEY != 'INSERT API KEY' else '未设置'}")
logger.debug(f"  OPENAI_BASE_URL: {OPENAI_BASE}")
logger.debug(f"  OPENAI_MODEL: '{PREFERRED}' (原始值)")
logger.debug(f"  最终模型列表: {FALLBACKS}")
logger.debug("=" * 60)


def chat(system_text: str, messages: list) -> str:
    """
    调用 OpenAI API 进行对话
    
    参数:
        system_text: 系统提示词，定义 AI 的角色和行为
        messages: 消息列表，格式为 [{"role": "user", "content": "..."}, ...]
                 role 可以是 "user"、"assistant" 或 "system"
        
    返回:
        str: AI 的回复文本
             如果所有模型都不可用或 API 密钥缺失，返回错误提示字符串
        
    工作流程:
        1. 检查 API 密钥是否存在
        2. 遍历模型列表（首选模型 -> 备用模型）
        3. 尝试调用每个模型，直到成功或所有模型都失败
        4. 返回第一个成功的响应，或错误提示
        
    异常处理:
        - 如果某个模型调用失败，会静默继续尝试下一个模型
        - 所有模型都失败时返回友好的错误提示
    """
    logger.debug("=" * 60)
    logger.debug("开始调用 chat() 函数")
    logger.debug(f"系统提示词长度: {len(system_text)} 字符")
    logger.debug(f"消息数量: {len(messages)}")
    
    # 检查 API 密钥：如果未设置，直接返回错误提示
    if not OPENAI_API_KEY or OPENAI_API_KEY == "INSERT API KEY":
        logger.error("❌ API 密钥缺失或未正确设置")
        logger.error(f"   当前 OPENAI_API_KEY 值: '{OPENAI_API_KEY}'")
        return "[OpenAI key missing]"

    # 检查模型列表是否为空
    if not FALLBACKS:
        logger.error("❌ 模型列表为空，没有可用的模型")
        return "[No models configured. Please set OPENAI_MODEL in .env file.]"

    # 准备 HTTP 请求头：包含认证信息和内容类型
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",  # Bearer Token 认证
        "Content-Type": "application/json",  # JSON 内容类型
    }
    
    logger.debug(f"请求 URL: {OPENAI_BASE}/chat/completions")
    logger.debug(f"将尝试 {len(FALLBACKS)} 个模型: {FALLBACKS}")

    # 遍历模型列表，尝试每个模型直到成功
    for idx, model in enumerate(FALLBACKS, 1):
        logger.info(f"🔄 尝试模型 {idx}/{len(FALLBACKS)}: {model}")
        
        # 构建请求体：包含模型名和消息列表
        # 系统提示词作为第一条 system 消息
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_text},  # 系统角色消息
                *messages  # 展开用户和助手的历史消息
            ]
        }
        
        # 使用 JSON 格式输出 body.messages 的所有内容（类似 jq 格式）
        import json
        logger.debug(f"请求体（模型: {model}）:")
        logger.debug(f"  - 消息数量: {len(body['messages'])}")
        logger.debug(f"  - messages 内容 (JSON 格式):")
        logger.debug(json.dumps(body['messages'], indent=2, ensure_ascii=False))
        
        try:
            # 发送 POST 请求到 OpenAI Chat Completions API
            # timeout=60 表示请求超时时间为 60 秒
            logger.debug(f"发送请求到: {OPENAI_BASE}/chat/completions")
            r = requests.post(
                f"{OPENAI_BASE}/chat/completions",
                headers=headers,
                json=body,
                timeout=60
            )
            
            logger.debug(f"响应状态码: {r.status_code}")
            
            # 如果请求成功（状态码 200）
            if r.status_code == 200:
                # 解析 JSON 响应
                data = r.json()
                # 提取 AI 的回复内容
                # choices[0] 是第一个（通常也是唯一的）回复选项
                # message.content 包含实际的文本回复
                reply = data["choices"][0]["message"]["content"]
                logger.info(f"✅ 模型 {model} 调用成功！")
                logger.debug(f"回复长度: {len(reply)} 字符")
                logger.debug(f"回复: {reply}")
                logger.debug("=" * 60)
                return reply
            else:
                # 请求失败（如模型不可用、配额不足等），继续尝试下一个模型
                error_detail = ""
                try:
                    error_data = r.json()
                    error_detail = error_data.get("error", {}).get("message", "未知错误")
                    error_type = error_data.get("error", {}).get("type", "未知类型")
                    logger.warning(f"❌ 模型 {model} 调用失败:")
                    logger.warning(f"   状态码: {r.status_code}")
                    logger.warning(f"   错误类型: {error_type}")
                    logger.warning(f"   错误信息: {error_detail}")
                except:
                    logger.warning(f"❌ 模型 {model} 调用失败: 状态码 {r.status_code}, 响应: {r.text[:200]}")
                
                # 继续尝试下一个模型
                logger.debug(f"继续尝试下一个模型...")
                continue
                
        except requests.exceptions.Timeout:
            logger.error(f"⏱️ 模型 {model} 请求超时（60秒）")
            continue
        except requests.exceptions.ConnectionError as e:
            logger.error(f"🔌 模型 {model} 连接错误: {str(e)}")
            continue
        except requests.exceptions.RequestException as e:
            logger.error(f"🌐 模型 {model} 请求异常: {type(e).__name__}: {str(e)}")
            continue
        except Exception as e:
            # 发生其他异常（如网络错误、超时等），继续尝试下一个模型
            logger.error(f"💥 模型 {model} 发生未预期的异常: {type(e).__name__}: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            continue

    # 所有模型都失败，返回友好的错误提示
    logger.error("=" * 60)
    logger.error("❌ 所有模型都调用失败！")
    logger.error(f"   尝试的模型: {FALLBACKS}")
    logger.error(f"   API Base URL: {OPENAI_BASE}")
    logger.error(f"   API Key: {'已设置' if OPENAI_API_KEY and OPENAI_API_KEY != 'INSERT API KEY' else '未设置'}")
    logger.error("=" * 60)
    return "[All configured models unavailable in this project. Please set OPENAI_MODEL to one you can use.]"
