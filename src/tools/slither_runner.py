# src/tools/slither_runner.py
import subprocess
import json
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.schemas import SlitherScanArgs
from utils.cache import cached_tool
from utils.retry import retry_with_backoff, RetryableError, NonRetryableError
from utils.logger import get_logger
from config import get_config

logger = get_logger()


@cached_tool("slither_scan")
@retry_with_backoff(retryable_exceptions=[subprocess.TimeoutExpired, ConnectionError])
def slither_scan(target: str, config: str | None = None) -> dict:
    """
    对项目或单文件进行 Slither 静态扫描
    
    Args:
        target: 文件路径或项目根目录
        config: Slither配置文件路径（可选）
    
    Returns:
        dict: {"tool": "slither", "ok": bool, "data": dict}
    """
    # 参数验证
    try:
        args = SlitherScanArgs(target=target, config=config)
        target = args.target
        config = args.config
    except Exception as e:
        raise NonRetryableError(f"参数验证失败: {e}")
    
    logger.info(f"执行Slither扫描: {target}", tool_name="slither_scan", tool_args={"target": target})
    
    try:
        cmd = ["slither", target, "--json", "-"]
        if config:
            cmd += ["--config-file", config]
        
        config_obj = get_config()
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=config_obj.tool_timeout
        )
        
        out = p.stdout.strip() or "{}"
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            data = {"raw": out[:20000], "parse_error": True}
        
        result = {
            "tool": "slither",
            "ok": (p.returncode in (0, 255)),
            "data": data
        }
        
        if p.returncode not in (0, 255):
            result["error"] = p.stderr[:500] if p.stderr else "Unknown error"
        
        return result
        
    except subprocess.TimeoutExpired:
        raise RetryableError("Slither扫描超时")
    except FileNotFoundError:
        raise NonRetryableError("Slither未安装或不在PATH中")
    except Exception as e:
        raise RetryableError(f"Slither扫描失败: {e}")
