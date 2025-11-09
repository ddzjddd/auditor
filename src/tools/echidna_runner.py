# src/tools/echidna_runner.py
import subprocess
import json
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.schemas import EchidnaTestArgs
from utils.cache import cached_tool
from utils.retry import retry_with_backoff, RetryableError, NonRetryableError
from utils.logger import get_logger
from config import get_config

logger = get_logger()


@cached_tool("echidna_test")
@retry_with_backoff(retryable_exceptions=[subprocess.TimeoutExpired, ConnectionError])
def echidna_test(
    target: str,
    config: str | None = None,
    test_mode: str = "property",
    timeout: int = 300,
    seq_len: int = 100
) -> dict:
    """
    使用 Echidna 进行基于属性的模糊测试
    
    Args:
        target: 测试文件路径或项目根目录
        config: Echidna配置文件路径（可选）
        test_mode: 测试模式 ("property" 或 "assertion")
        timeout: 执行超时时间（秒）
        seq_len: 测试序列长度
    
    Returns:
        dict: {"tool": "echidna", "ok": bool, "data": dict}
    """
    # 参数验证
    try:
        args = EchidnaTestArgs(
            target=target,
            config=config,
            test_mode=test_mode,
            timeout=timeout,
            seq_len=seq_len
        )
        target = args.target
        config = args.config
        test_mode = args.test_mode
        timeout = args.timeout
        seq_len = args.seq_len
    except Exception as e:
        raise NonRetryableError(f"参数验证失败: {e}")
    
    logger.info(
        f"执行Echidna测试: {target}",
        tool_name="echidna_test",
        tool_args={"target": target, "test_mode": test_mode}
    )
    
    try:
        # 构建Echidna命令
        cmd = ["echidna", target, "--format", "json"]
        
        if config:
            cmd += ["--config", config]
        
        if test_mode == "assertion":
            cmd += ["--test-mode", "assertion"]
        else:
            cmd += ["--test-mode", "property"]
        
        cmd += ["--seq-len", str(seq_len)]
        
        config_obj = get_config()
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=min(timeout, config_obj.tool_timeout)
        )
        
        # 解析输出
        stdout = p.stdout.strip()
        stderr = p.stderr.strip()
        
        # 尝试解析JSON输出
        data = {}
        if stdout:
            try:
                data = json.loads(stdout)
            except json.JSONDecodeError:
                # 如果不是JSON，尝试解析文本输出
                data = {
                    "raw_output": stdout[:20000],
                    "parse_error": True
                }
        
        # 检查是否发现漏洞
        found_bugs = False
        if isinstance(data, dict):
            found_bugs = data.get("bugs", []) or data.get("test_results", {}).get("failed", [])
        
        result = {
            "tool": "echidna",
            "ok": (p.returncode == 0 or found_bugs),  # 发现bug也算成功
            "data": {
                "test_mode": test_mode,
                "bugs_found": bool(found_bugs),
                "results": data,
                "return_code": p.returncode
            }
        }
        
        if stderr:
            result["data"]["stderr"] = stderr[:1000]
        
        if p.returncode != 0 and not found_bugs:
            result["error"] = stderr[:500] if stderr else "Echidna执行失败"
        
        return result
        
    except subprocess.TimeoutExpired:
        raise RetryableError("Echidna测试超时")
    except FileNotFoundError:
        raise NonRetryableError("Echidna未安装或不在PATH中。请安装: foundryup")
    except Exception as e:
        raise RetryableError(f"Echidna测试失败: {e}")

