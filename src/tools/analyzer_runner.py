# src/tools/analyzer_runner.py
import subprocess
import json
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.schemas import AnalyzerScanArgs
from utils.cache import cached_tool
from utils.retry import retry_with_backoff, RetryableError, NonRetryableError
from utils.logger import get_logger
from config import get_config

logger = get_logger()


@cached_tool("analyzer_scan")
@retry_with_backoff(retryable_exceptions=[subprocess.TimeoutExpired, ConnectionError])
def analyzer_scan(
    target: str,
    report_format: str = "json",
    no_optimizations: bool = False
) -> dict:
    """
    使用 4naly3er 进行 Gas 优化分析
    
    Args:
        target: 文件路径或项目根目录（包含合约的目录）
        report_format: 报告格式 ("json", "md", "txt")
        no_optimizations: 是否禁用优化建议
    
    Returns:
        dict: {"tool": "4naly3er", "ok": bool, "data": dict}
    """
    # 参数验证
    try:
        args = AnalyzerScanArgs(
            target=target,
            report_format=report_format,
            no_optimizations=no_optimizations
        )
        target = args.target
        report_format = args.report_format
        no_optimizations = args.no_optimizations
    except Exception as e:
        raise NonRetryableError(f"参数验证失败: {e}")
    
    logger.info(
        f"执行4naly3er分析: {target}",
        tool_name="analyzer_scan",
        tool_args={"target": target, "report_format": report_format}
    )
    
    try:
        # 构建4naly3er命令
        # 4naly3er通常作为forge脚本运行
        target_path = Path(target)
        
        if target_path.is_file():
            # 如果是单个文件，需要找到项目根目录
            # 向上查找foundry.toml或package.json
            root_dir = target_path.parent
            while root_dir != root_dir.parent:
                if (root_dir / "foundry.toml").exists() or (root_dir / "package.json").exists():
                    break
                root_dir = root_dir.parent
            target = str(root_dir)
        else:
            target = str(target_path.absolute())
        
        # 4naly3er通常通过forge script或直接运行
        # 检查是否有4naly3er可执行文件
        cmd = None
        if subprocess.run(["which", "4naly3er"], capture_output=True).returncode == 0:
            cmd = ["4naly3er", target]
        elif (Path(target) / "4naly3er").exists() or (Path(target) / "4naly3er.py").exists():
            # 尝试作为Python脚本运行
            script_path = Path(target) / "4naly3er.py"
            if not script_path.exists():
                script_path = Path(target) / "4naly3er"
            if script_path.exists():
                cmd = ["python3", str(script_path), target]
        else:
            # 尝试使用forge script运行（如果项目中有4naly3er脚本）
            forge_script = Path(target) / "script" / "4naly3er.s.sol"
            if forge_script.exists():
                cmd = ["forge", "script", str(forge_script), "--root", target]
            else:
                raise NonRetryableError(
                    "4naly3er未找到。请安装: "
                    "curl -L https://github.com/Picodes/4naly3er/releases/latest/download/4naly3er -o /usr/local/bin/4naly3er && chmod +x /usr/local/bin/4naly3er"
                )
        
        if not cmd:
            raise NonRetryableError("无法找到4naly3er执行方式")
        
        if report_format == "json":
            cmd += ["--json"]
        
        config_obj = get_config()
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=config_obj.tool_timeout,
            cwd=target
        )
        
        stdout = p.stdout.strip()
        stderr = p.stderr.strip()
        
        # 解析输出
        data = {}
        if stdout:
            if report_format == "json":
                try:
                    data = json.loads(stdout)
                except json.JSONDecodeError:
                    data = {"raw_output": stdout[:20000], "parse_error": True}
            else:
                data = {"report": stdout[:20000]}
        
        # 提取Gas优化建议
        optimizations = []
        if isinstance(data, dict):
            optimizations = data.get("optimizations", []) or data.get("gas_optimizations", [])
        
        result = {
            "tool": "4naly3er",
            "ok": (p.returncode == 0),
            "data": {
                "optimizations_found": len(optimizations),
                "optimizations": optimizations[:50],  # 限制数量
                "report": data,
                "return_code": p.returncode
            }
        }
        
        if stderr:
            result["data"]["stderr"] = stderr[:1000]
        
        if p.returncode != 0:
            result["error"] = stderr[:500] if stderr else "4naly3er执行失败"
        
        return result
        
    except NonRetryableError:
        raise
    except subprocess.TimeoutExpired:
        raise RetryableError("4naly3er分析超时")
    except FileNotFoundError:
        raise NonRetryableError("4naly3er未安装或不在PATH中")
    except Exception as e:
        raise RetryableError(f"4naly3er分析失败: {e}")

