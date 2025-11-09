# src/tools/semgrep_runner.py
import subprocess
import json
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.schemas import SemgrepScanArgs
from utils.cache import cached_tool
from utils.retry import retry_with_backoff, RetryableError, NonRetryableError
from utils.logger import get_logger
from config import get_config

logger = get_logger()


@cached_tool("semgrep_scan")
@retry_with_backoff(retryable_exceptions=[subprocess.TimeoutExpired, ConnectionError])
def semgrep_scan(
    target: str,
    config: str | None = None,
    severity: str | None = None,
    output_format: str = "json"
) -> dict:
    """
    使用 Semgrep 进行基于规则的代码扫描
    
    Args:
        target: 文件路径或项目根目录
        config: Semgrep配置（规则集或配置文件路径，如 "solidity" 或 "p/solidity"）
        severity: 过滤严重程度 ("ERROR", "WARNING", "INFO")
        output_format: 输出格式 ("json", "text")
    
    Returns:
        dict: {"tool": "semgrep", "ok": bool, "data": dict}
    """
    # 参数验证
    try:
        args = SemgrepScanArgs(
            target=target,
            config=config,
            severity=severity,
            output_format=output_format
        )
        target = args.target
        config = args.config
        severity = args.severity
        output_format = args.output_format
    except Exception as e:
        raise NonRetryableError(f"参数验证失败: {e}")
    
    logger.info(
        f"执行Semgrep扫描: {target}",
        tool_name="semgrep_scan",
        tool_args={"target": target, "config": config}
    )
    
    try:
        # 构建Semgrep命令
        cmd = ["semgrep", "--json", target]
        
        if config:
            cmd += ["--config", config]
        else:
            # 默认使用Solidity规则集
            cmd += ["--config", "p/solidity"]
        
        if severity:
            cmd += ["--severity", severity]
        
        # 添加额外选项
        cmd += ["--no-git-ignore", "--quiet"]  # 不忽略git，减少输出
        
        config_obj = get_config()
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=config_obj.tool_timeout
        )
        
        stdout = p.stdout.strip()
        stderr = p.stderr.strip()
        
        # 解析JSON输出
        data = {}
        if stdout:
            try:
                data = json.loads(stdout)
            except json.JSONDecodeError:
                data = {
                    "raw_output": stdout[:20000],
                    "parse_error": True
                }
        
        # 统计结果
        results = data.get("results", [])
        errors = [r for r in results if r.get("extra", {}).get("severity") == "ERROR"]
        warnings = [r for r in results if r.get("extra", {}).get("severity") == "WARNING"]
        
        result = {
            "tool": "semgrep",
            "ok": (p.returncode in (0, 1)),  # Semgrep返回1表示发现issue
            "data": {
                "total_findings": len(results),
                "errors": len(errors),
                "warnings": len(warnings),
                "results": results[:100],  # 限制返回数量
                "config_used": config or "p/solidity"
            }
        }
        
        if stderr:
            result["data"]["stderr"] = stderr[:500]
        
        if p.returncode not in (0, 1):
            result["error"] = stderr[:500] if stderr else "Semgrep执行失败"
        
        return result
        
    except subprocess.TimeoutExpired:
        raise RetryableError("Semgrep扫描超时")
    except FileNotFoundError:
        raise NonRetryableError("Semgrep未安装。请安装: pip install semgrep 或 brew install semgrep")
    except Exception as e:
        raise RetryableError(f"Semgrep扫描失败: {e}")

