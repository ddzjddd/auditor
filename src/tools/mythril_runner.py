# src/tools/mythril_runner.py
import subprocess
import json
import tempfile
import os
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.schemas import MythrilScanArgs
from utils.cache import cached_tool
from utils.retry import retry_with_backoff, RetryableError, NonRetryableError
from utils.logger import get_logger

logger = get_logger()


@cached_tool("mythril_scan")
@retry_with_backoff(retryable_exceptions=[subprocess.TimeoutExpired])
def mythril_scan(bytecode: str, entry: str | None = None, timeout: int = 120) -> dict:
    """
    调用 Mythril 对合约进行符号执行分析
    
    Args:
        bytecode: 合约字节码 (hex)
        entry: 可选，入口函数名
        timeout: 执行超时时间（秒）
    
    Returns:
        dict: {"tool": "mythril", "ok": bool, "data": dict}
    """
    # 参数验证
    try:
        args = MythrilScanArgs(bytecode=bytecode, entry=entry, timeout=timeout)
        bytecode = args.bytecode
        entry = args.entry
        timeout = args.timeout
    except Exception as e:
        raise NonRetryableError(f"参数验证失败: {e}")
    
    logger.info(f"执行Mythril扫描", tool_name="mythril_scan", tool_args={"entry": entry, "timeout": timeout})
    
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile("w+", suffix=".hex", delete=False) as f:
            f.write(bytecode.strip())
            tmp_path = f.name

        cmd = ["myth", "analyze", tmp_path, "-o", "json", "--max-depth", "12"]
        if entry:
            cmd += ["--entry-point", entry]

        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = p.stdout.strip()

        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            data = {"raw": out[:20000], "parse_error": True}

        result = {
            "tool": "mythril",
            "ok": (p.returncode in (0, 255)),
            "data": data
        }
        
        if p.returncode not in (0, 255):
            result["error"] = p.stderr[:500] if p.stderr else "Unknown error"
        
        return result

    except subprocess.TimeoutExpired:
        raise RetryableError("Mythril扫描超时")
    except FileNotFoundError:
        raise NonRetryableError("Mythril未安装或不在PATH中")
    except Exception as e:
        raise RetryableError(f"Mythril扫描失败: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
