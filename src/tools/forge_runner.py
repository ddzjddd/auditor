# src/tools/forge_runner.py
import subprocess
import json
import os
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.schemas import ForgeCompileArgs
from utils.cache import cached_tool
from utils.retry import retry_with_backoff, RetryableError, NonRetryableError
from utils.logger import get_logger

logger = get_logger()


@cached_tool("forge_compile")
@retry_with_backoff(retryable_exceptions=[subprocess.TimeoutExpired])
def forge_compile(root_dir: str, evm_version: str | None = None, opt_runs: int = 200, timeout: int = 60) -> dict:
    """
    使用 Foundry 编译合约，返回 ABI/Bytecode/编译信息
    
    Args:
        root_dir: 项目根目录
        evm_version: EVM版本（可选）
        opt_runs: 优化器运行次数
        timeout: 编译超时时间（秒）
    
    Returns:
        dict: {"tool": "forge", "ok": bool, "data": dict}
    """
    # 参数验证
    try:
        args = ForgeCompileArgs(
            root_dir=root_dir,
            evm_version=evm_version,
            opt_runs=opt_runs,
            timeout=timeout
        )
        root_dir = args.root_dir
        evm_version = args.evm_version
        opt_runs = args.opt_runs
        timeout = args.timeout
    except Exception as e:
        raise NonRetryableError(f"参数验证失败: {e}")
    
    logger.info(f"执行Forge编译: {root_dir}", tool_name="forge_compile", tool_args={"root_dir": root_dir})
    
    try:
        cmd = ["forge", "build", "--root", root_dir, "--json"]
        if evm_version:
            cmd += ["--evm-version", evm_version]
        cmd += ["--optimizer-runs", str(opt_runs)]

        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = p.stdout.strip()

        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            data = {"raw": out[:20000], "parse_error": True}

        # 从 out 文件夹提取编译结果
        artifacts_dir = os.path.join(root_dir, "out")
        compiled = {}
        compiled_paths = {}  # 存储完整路径信息
        if os.path.exists(artifacts_dir):
            for root, _, files in os.walk(artifacts_dir):
                for f in files:
                    if f.endswith(".json") and not f.startswith("build-info"):
                        fp = os.path.join(root, f)
                        try:
                            with open(fp, 'r', encoding='utf-8') as jf:
                                j = json.load(jf)
                            contract_name = f.replace(".json", "")
                            # 计算相对路径（从out目录开始）
                            rel_path = os.path.relpath(fp, artifacts_dir)
                            compiled[contract_name] = {
                                "abi": j.get("abi"),
                                "bytecode": j.get("bytecode", {}).get("object"),
                                "compiler": j.get("metadata", {}).get("compiler", {}),
                            }
                            # 存储完整路径信息
                            compiled_paths[contract_name] = {
                                "full_path": fp,
                                "relative_path": rel_path,
                                "directory": os.path.dirname(rel_path)
                            }
                        except Exception as e:
                            logger.warning(f"解析编译产物失败 {fp}: {e}")
                            continue

        result = {
            "tool": "forge",
            "ok": (p.returncode == 0),
            "data": {
                "compile_out": data,
                "contracts": compiled,
                "contract_paths": compiled_paths,  # 添加路径信息
                "artifacts_dir": artifacts_dir
            }
        }
        
        if p.returncode != 0:
            result["error"] = p.stderr[:500] if p.stderr else "Unknown error"
        
        return result

    except subprocess.TimeoutExpired:
        raise RetryableError("Forge编译超时")
    except FileNotFoundError:
        raise NonRetryableError("Forge未安装或不在PATH中")
    except Exception as e:
        raise RetryableError(f"Forge编译失败: {e}")
