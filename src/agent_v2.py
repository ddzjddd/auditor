"""
重构后的Agent核心
- 标准化工具调用机制
- 状态管理
- 结果摘要
- 错误处理
"""
import os
import json
import sys
import uuid
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum
import orjson
import httpx


def _make_json_serializable(obj: Any) -> Any:
    """确保对象可JSON序列化"""
    if isinstance(obj, dict):
        return {k: _make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_make_json_serializable(item) for item in obj]
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, (Path,)):
        return str(obj)
    else:
        # 对于其他类型，尝试转换为字符串
        try:
            # 尝试序列化，如果失败则转换为字符串
            json.dumps(obj)
            return obj
        except (TypeError, ValueError):
            return str(obj)

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_config
from utils.logger import setup_logging, get_logger
from utils.summarizer import summarize_tool_result
from utils.retry import RetryableError, NonRetryableError
from tools.schemas import TOOL_ARGS_MODELS

# 导入工具
from tools.slither_runner import slither_scan
from tools.mythril_runner import mythril_scan
from tools.forge_runner import forge_compile
from tools.chain_state import read_chain_state
from tools.read_file import read_file
from tools.echidna_runner import echidna_test
from tools.semgrep_runner import semgrep_scan
from tools.analyzer_runner import analyzer_scan
from tools.hardhat_network_runner import hardhat_simulate
from rag.retriever import rag_search


class AuditState(Enum):
    """审计状态"""
    INIT = "init"
    COLLECTING = "collecting"
    SCANNING = "scanning"
    ANALYZING = "analyzing"
    REPORTING = "reporting"
    COMPLETED = "completed"
    FAILED = "failed"


class ToolCall:
    """工具调用记录"""
    def __init__(self, name: str, args: dict, result: Optional[dict] = None):
        self.id = str(uuid.uuid4())
        self.name = name
        self.args = args
        self.result = result
        self.timestamp = time.time()
        self.duration: Optional[float] = None


class AuditSession:
    """审计会话（状态管理）"""
    def __init__(self, task: str, trace_id: Optional[str] = None):
        self.id = trace_id or str(uuid.uuid4())
        self.task = task
        self.state = AuditState.INIT
        self.messages: List[Dict[str, str]] = []
        self.tool_calls: List[ToolCall] = []
        self.iteration = 0
        self.start_time = time.time()
        self.logger = get_logger(self.id)
    
    def add_message(self, role: str, content: str):
        """添加消息"""
        self.messages.append({"role": role, "content": content})
    
    def add_tool_call(self, tool_call: ToolCall):
        """添加工具调用记录"""
        self.tool_calls.append(tool_call)
        self.logger.info(
            f"工具调用: {tool_call.name}",
            tool_name=tool_call.name,
            tool_args=tool_call.args
        )
    
    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "id": self.id,
            "task": self.task,
            "state": self.state.value,
            "iteration": self.iteration,
            "tool_calls_count": len(self.tool_calls),
            "duration": time.time() - self.start_time
        }


class AuditAgent:
    """智能合约审计Agent"""
    
    def __init__(self):
        self.config = get_config()
        self.logger = setup_logging()
        
        # 加载提示词
        prompts_dir = Path("src/prompts")
        system_prompt_path = prompts_dir / "system_audit.txt"
        tool_schema_path = prompts_dir / "tool_schema.json"
        
        if not system_prompt_path.exists():
            raise FileNotFoundError(f"系统提示词文件不存在: {system_prompt_path}")
        if not tool_schema_path.exists():
            raise FileNotFoundError(f"工具schema文件不存在: {tool_schema_path}")
        
        base_system_prompt = system_prompt_path.read_text(encoding="utf-8")
        self.tool_schema = json.loads(tool_schema_path.read_text(encoding="utf-8"))
        
        # 工具注册表
        self.tools = {
            "slither_scan": slither_scan,
            "mythril_scan": mythril_scan,
            "forge_compile": forge_compile,
            "read_chain_state": read_chain_state,
            "rag_search": rag_search,
            "read_file": read_file,
            "echidna_test": echidna_test,
            "semgrep_scan": semgrep_scan,
            "analyzer_scan": analyzer_scan,
            "hardhat_simulate": hardhat_simulate,
        }
        
        # 格式化工具信息
        tools_info = self._format_tools_info()
        self.system_prompt = base_system_prompt + f"\n\n可用工具列表：\n{tools_info}\n\n调用工具时，请严格按照上述参数名称和类型。"
    
    def _format_tools_info(self) -> str:
        """格式化工具信息供LLM使用"""
        tools_info = []
        for tool in self.tool_schema:
            name = tool["name"]
            desc = tool["description"]
            params = tool.get("parameters", {}).get("properties", {})
            required = tool.get("parameters", {}).get("required", [])
            
            param_list = []
            for param_name, param_info in params.items():
                param_type = param_info.get("type", "string")
                param_desc = param_info.get("description", "")
                is_required = param_name in required
                req_mark = "（必需）" if is_required else "（可选）"
                param_list.append(f"  - {param_name} ({param_type}): {param_desc} {req_mark}")
            
            tools_info.append(f"{name}: {desc}\n参数:\n" + "\n".join(param_list))
        
        return "\n\n".join(tools_info)
    
    def _call_llm(self, messages: List[Dict[str, str]], tools_enabled: bool = True) -> str:
        """调用LLM"""
        config = self.config
        
        # 构建请求
        payload = {
            "model": config.model_name,
            "messages": messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens
        }
        
        # 如果支持function calling，添加工具定义
        # 注意：这里简化处理，实际应该根据LLM类型选择
        if tools_enabled and hasattr(self, '_format_tools_for_llm'):
            payload["tools"] = self._format_tools_for_llm()
        
        headers = {"Authorization": f"Bearer {config.deepseek_api_key}"}
        
        try:
            with httpx.Client(timeout=60) as client:
                r = client.post(
                    f"{config.deepseek_base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                r.raise_for_status()
                data = r.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            self.logger.error(f"LLM调用失败: {e}")
            raise
    
    def _extract_tool_call(self, text: str) -> Optional[Dict[str, Any]]:
        """
        从LLM输出中提取工具调用
        支持两种格式：
        1. ```tool\n{...}\n``` (旧格式)
        2. JSON格式的工具调用
        """
        import re
        
        # 方法1: 提取 ```tool ... ``` 块
        tool_block_pattern = r"```tool\n(.*?)\n```"
        match = re.search(tool_block_pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass
        
        # 方法2: 尝试提取JSON对象
        json_pattern = r'\{[^{}]*"name"[^{}]*"args"[^{}]*\}'
        matches = re.findall(json_pattern, text, re.DOTALL)
        for match in matches:
            try:
                parsed = json.loads(match)
                if "name" in parsed and "args" in parsed:
                    return parsed
            except json.JSONDecodeError:
                continue
        
        return None
    
    def _validate_tool_call(self, tool_call: Dict[str, Any]) -> tuple[str, dict]:
        """验证工具调用参数"""
        name = tool_call.get("name")
        args = tool_call.get("args", {})
        
        if not name:
            raise ValueError("工具调用缺少'name'字段")
        
        if name not in self.tools:
            raise ValueError(f"未知工具: {name}。可用工具: {list(self.tools.keys())}")
        
        # 参数验证
        if name in TOOL_ARGS_MODELS:
            try:
                model = TOOL_ARGS_MODELS[name]
                validated_args = model(**args)
                # 兼容 Pydantic V1 和 V2
                if hasattr(validated_args, 'model_dump'):
                    args = validated_args.model_dump(exclude_none=True)
                else:
                    args = validated_args.dict(exclude_none=True)
            except Exception as e:
                raise ValueError(f"工具参数验证失败: {e}")
        
        return name, args
    
    def _execute_tool(self, name: str, args: dict) -> dict:
        """执行工具"""
        tool_func = self.tools[name]
        
        try:
            start_time = time.time()
            result = tool_func(**args)
            duration = time.time() - start_time
            
            # 摘要结果（如果太大）
            if isinstance(result, dict) and result.get("ok"):
                result = summarize_tool_result(name, result, max_length=2000)
            
            return result
            
        except NonRetryableError as e:
            return {
                "tool": name,
                "ok": False,
                "error": str(e),
                "retryable": False
            }
        except RetryableError as e:
            return {
                "tool": name,
                "ok": False,
                "error": str(e),
                "retryable": True
            }
        except Exception as e:
            # 记录详细的错误信息用于调试
            import traceback
            error_type = type(e).__name__
            
            # 记录完整的异常信息（用于调试）
            try:
                full_traceback = traceback.format_exc()
                self.logger.debug(f"工具 {name} 执行异常完整堆栈:\n{full_traceback}")
            except Exception:
                pass
            
            # 安全地提取错误信息，避免序列化问题
            try:
                error_msg = str(e)
                # 限制错误消息长度，避免包含不可序列化对象
                if len(error_msg) > 500:
                    error_msg = error_msg[:500] + "..."
                
                # 记录原始错误信息（用于调试）
                self.logger.warning(f"🔍 工具 {name} 异常详情 - 类型: {error_type}, 消息: {error_msg}")
                
                # 如果是序列化相关错误，记录更多调试信息
                if "not JSON serializable" in error_msg or "序列化" in error_msg or "RAGRetriever" in error_msg:
                    self.logger.warning(f"⚠️ 检测到序列化相关错误 - 工具: {name}, 错误类型: {error_type}")
                    self.logger.warning(f"序列化错误详情: {repr(e)[:1000]}")
                    
                    # 尝试获取异常的更多信息
                    try:
                        if hasattr(e, '__cause__') and e.__cause__:
                            self.logger.warning(f"异常原因: {type(e.__cause__).__name__}: {str(e.__cause__)[:500]}")
                        if hasattr(e, '__context__') and e.__context__:
                            self.logger.warning(f"异常上下文: {type(e.__context__).__name__}: {str(e.__context__)[:500]}")
                    except Exception:
                        pass
                    
                    error_msg = f"{error_type}: 序列化错误（已清理）"
            except Exception as extract_error:
                # 如果连提取错误信息都失败，使用默认值
                self.logger.error(f"提取错误信息时失败: {extract_error}")
                error_type = "Exception"
                error_msg = "未知错误（无法提取错误信息）"
            
            # 使用安全的错误信息记录日志
            try:
                self.logger.error(f"工具执行异常: {name} - {error_type}: {error_msg}")
            except Exception as log_error:
                # 如果日志记录也失败，至少打印到控制台
                print(f"工具执行异常: {name} - {error_type}: {error_msg}")
                print(f"日志记录也失败: {log_error}")
            
            return {
                "tool": name,
                "ok": False,
                "error": f"{error_type}: {error_msg}"
            }
    
    def audit(self, task: str) -> str:
        """
        执行审计任务
        
        Args:
            task: 审计任务描述
        
        Returns:
            审计报告
        """
        session = AuditSession(task)
        session.state = AuditState.COLLECTING
        
        self.logger.info(f"开始审计任务: {task}", trace_id=session.id)
        
        # 初始化会话
        session.add_message("system", self.system_prompt)
        session.add_message(
            "user",
            f"任务：{task}\n\n"
            f"请在需要时调用工具，格式：\n"
            f"```tool\n{{\"name\": \"工具名\", \"args\": {{\"参数名\": \"参数值\"}}}}\n```\n\n"
            f"重要提示：\n"
            f"- 参数名称必须完全匹配系统提示中工具定义中的参数名。\n"
            f"- 【必须使用RAG】执行静态扫描（slither_scan/semgrep_scan）后，必须根据扫描结果调用rag_search检索相关漏洞知识。例如：\n"
            f"  * 扫描发现重入风险 → 调用rag_search(query='reentrancy')\n"
            f"  * 扫描发现权限问题 → 调用rag_search(query='access control')\n"
            f"  * 审计ERC20代币 → 调用rag_search(query='ERC20 common issues')\n"
            f"  * 审计可升级合约 → 调用rag_search(query='proxy patterns')\n"
            f"- 工具调用顺序建议：read_file → slither_scan/semgrep_scan → rag_search（根据扫描结果检索相关漏洞）→ 其他分析工具。\n"
            f"- 如果扫描结果中包含漏洞类型（如SWC编号、漏洞名称），必须调用rag_search检索该漏洞的详细信息和修复建议。"
        )
        
        # 主循环
        max_iterations = self.config.max_tool_iterations
        for iteration in range(max_iterations):
            session.iteration = iteration + 1
            
            try:
                # 调用LLM
                response = self._call_llm(session.messages)
                session.add_message("assistant", response)
                
                # 尝试提取工具调用
                tool_call_data = self._extract_tool_call(response)
                
                if tool_call_data:
                    # 执行工具
                    try:
                        name, args = self._validate_tool_call(tool_call_data)
                        
                        tool_call = ToolCall(name, args)
                        session.add_tool_call(tool_call)
                        
                        result = self._execute_tool(name, args)
                        tool_call.result = result
                        tool_call.duration = time.time() - tool_call.timestamp
                        
                        # 确保结果可序列化
                        serializable_result = _make_json_serializable(result)
                        
                        # 将结果添加到会话
                        result_json = orjson.dumps(serializable_result).decode()
                        session.add_message(
                            "user",
                            f"【工具结果】\n```json\n{result_json}\n```\n\n"
                            f"请基于此结果继续分析。"
                        )
                        
                        # 如果工具失败且不可重试，记录错误但继续
                        if not result.get("ok") and not result.get("retryable", True):
                            self.logger.warning(f"工具执行失败（不可重试）: {name}")
                        
                        continue
                        
                    except ValueError as e:
                        # 工具调用验证失败
                        session.add_message(
                            "user",
                            f"工具调用错误: {e}。请修正后重试。"
                        )
                        continue
                
                else:
                    # 没有工具调用，返回最终结果
                    session.state = AuditState.COMPLETED
                    self.logger.info(f"审计完成: {session.id}", trace_id=session.id)
                    return response
                    
            except Exception as e:
                self.logger.error(f"迭代 {iteration + 1} 失败: {e}", trace_id=session.id)
                session.add_message(
                    "user",
                    f"执行出错: {e}。请继续或结束审计。"
                )
        
        # 达到最大迭代次数
        session.state = AuditState.FAILED
        self.logger.warning(f"达到最大迭代次数 ({max_iterations}): {session.id}", trace_id=session.id)
        
        # 尝试生成部分报告
        summary_message = (
            f"已达到最大迭代次数 ({max_iterations})。\n\n"
            f"已执行 {len(session.tool_calls)} 个工具调用。\n"
            f"请基于已收集的信息生成审计报告摘要。"
        )
        session.add_message("user", summary_message)
        
        try:
            final_response = self._call_llm(session.messages)
            return f"⚠️ 达到最大迭代次数限制 ({max_iterations})，以下是基于已收集信息的审计摘要：\n\n{final_response}"
        except Exception as e:
            return f"执行轮次已达上限 ({max_iterations})，已执行 {len(session.tool_calls)} 个工具调用。请使用 --max-iterations 参数增加迭代次数或缩小审计范围。"


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="智能合约审计 Agent")
    parser.add_argument(
        "--target", "-t",
        type=str,
        help="要审计的合约文件或目录路径（例如: ./contracts/Token.sol 或 ./contracts）"
    )
    parser.add_argument(
        "--task", "-T",
        type=str,
        help="自定义审计任务描述（如果提供，将覆盖默认任务）"
    )
    parser.add_argument(
        "--contract-dir", "-d",
        type=str,
        help="默认合约目录（默认: contracts）"
    )
    parser.add_argument(
        "--max-iterations", "-i",
        type=int,
        help="最大工具调用轮次（默认: 15）"
    )
    
    args = parser.parse_args()
    
    agent = AuditAgent()
    
    # 如果指定了迭代次数，直接修改 Agent 的配置
    if args.max_iterations:
        agent.config.max_tool_iterations = args.max_iterations
    
    # 确定审计目标
    config = agent.config
    if args.target:
        target = args.target
    elif config.default_target:
        target = config.default_target
    elif args.contract_dir:
        target = args.contract_dir
    else:
        target = config.default_contract_dir
    
    # 构建任务描述
    if args.task:
        task = args.task
    else:
        # 自动生成任务描述
        if Path(target).is_file():
            task = f"请审计 {target}，并输出结构化报告与修复建议。必要时调用slither、semgrep、mythril、echidna、rag等工具。"
        else:
            task = f"请审计 {target} 目录下的所有合约，并输出结构化报告与修复建议。必要时调用slither、semgrep、mythril、echidna、rag等工具。"
    
    print("=" * 60)
    print("智能合约审计 Agent")
    print("=" * 60)
    print(f"审计目标: {target}")
    print(f"任务: {task}\n")
    
    result = agent.audit(task)
    
    print("\n" + "=" * 60)
    print("审计结果:")
    print("=" * 60)
    print(result)


if __name__ == "__main__":
    main()

