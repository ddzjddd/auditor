# src/tools/hardhat_network_runner.py
import json
import sys
from pathlib import Path
from typing import Optional, List
import subprocess
import time

try:
    import requests
except ImportError:
    requests = None

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.schemas import HardhatNetworkArgs
from utils.cache import cached_tool
from utils.retry import retry_with_backoff, RetryableError, NonRetryableError
from utils.logger import get_logger
from config import get_config

logger = get_logger()

# 全局变量存储 Hardhat 节点进程
_hardhat_process = None
_hardhat_port = 8545


def _ensure_hardhat_node(fork_url: Optional[str] = None, fork_block: Optional[int] = None) -> int:
    """
    确保 Hardhat 节点正在运行
    
    Args:
        fork_url: Fork 的网络 RPC URL（可选）
        fork_block: Fork 的区块号（可选）
    
    Returns:
        节点运行的端口号
    """
    global _hardhat_process, _hardhat_port
    
    # 检查节点是否已经在运行
    if requests:
        try:
            r = requests.post(
                f"http://localhost:{_hardhat_port}",
                json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
                timeout=2
            )
            if r.status_code == 200:
                logger.info(f"Hardhat 节点已在运行: {_hardhat_port}")
                return _hardhat_port
        except Exception:
            pass
    
    # 启动 Hardhat 节点
    logger.info("启动 Hardhat 本地节点...")
    
    # 检查是否有 hardhat.config.js 或 hardhat.config.ts
    project_root = Path.cwd()
    has_hardhat_config = (
        (project_root / "hardhat.config.js").exists() or
        (project_root / "hardhat.config.ts").exists() or
        (project_root / "hardhat.config.cjs").exists()
    )
    
    if not has_hardhat_config:
        # 创建临时 hardhat.config.js
        config_content = """module.exports = {
  networks: {
    hardhat: {
      chainId: 31337,
"""
        if fork_url:
            config_content += f'      forking: {{\n        url: "{fork_url}",\n'
            if fork_block:
                config_content += f"        blockNumber: {fork_block},\n"
            config_content += "      },\n"
        config_content += "    },\n  },\n};\n"
        
        temp_config = project_root / "hardhat.config.temp.js"
        temp_config.write_text(config_content)
        config_file = str(temp_config)
    else:
        config_file = None
    
    try:
        cmd = ["npx", "hardhat", "node", "--port", str(_hardhat_port)]
        if fork_url:
            cmd.extend(["--fork", fork_url])
            if fork_block:
                cmd.extend(["--fork-block-number", str(fork_block)])
        
        # 启动节点（后台运行）
        _hardhat_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=project_root
        )
        
        # 等待节点启动
        if not requests:
            raise NonRetryableError("requests 库未安装。请安装: pip install requests")
        
        max_wait = 30
        for i in range(max_wait):
            time.sleep(1)
            try:
                r = requests.post(
                    f"http://localhost:{_hardhat_port}",
                    json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
                    timeout=2
                )
                if r.status_code == 200:
                    logger.info(f"Hardhat 节点启动成功: {_hardhat_port}")
                    return _hardhat_port
            except Exception:
                if i == max_wait - 1:
                    raise RetryableError("Hardhat 节点启动超时")
                continue
        
        return _hardhat_port
        
    except FileNotFoundError:
        raise NonRetryableError(
            "Hardhat 未安装。请安装: npm install --save-dev hardhat @nomicfoundation/hardhat-toolbox"
        )
    finally:
        if config_file and Path(config_file).exists():
            Path(config_file).unlink()


@cached_tool("hardhat_simulate")
@retry_with_backoff(retryable_exceptions=[ConnectionError, TimeoutError])
def hardhat_simulate(
    transaction: dict,
    fork_url: Optional[str] = None,
    fork_block: Optional[int] = None,
    rpc_url: Optional[str] = None
) -> dict:
    """
    使用 Hardhat Network 本地测试网络模拟交易执行
    
    Args:
        transaction: 交易对象，包含 from, to, input, value, gas 等字段
        fork_url: Fork 的网络 RPC URL（可选，用于 fork 主网状态）
        fork_block: Fork 的区块号（可选）
        rpc_url: Hardhat 节点 RPC URL（可选，默认 http://localhost:8545）
    
    Returns:
        dict: {"tool": "hardhat_network", "ok": bool, "data": dict}
    """
    # 参数验证
    try:
        args = HardhatNetworkArgs(
            transaction=transaction,
            fork_url=fork_url,
            fork_block=fork_block,
            rpc_url=rpc_url
        )
        transaction = args.transaction
        fork_url = args.fork_url
        fork_block = args.fork_block
        rpc_url = args.rpc_url or f"http://localhost:{_hardhat_port}"
    except Exception as e:
        raise NonRetryableError(f"参数验证失败: {e}")
    
    logger.info(
        f"执行Hardhat Network模拟",
        tool_name="hardhat_simulate",
        tool_args={"to": transaction.get("to"), "fork": bool(fork_url)}
    )
    
    try:
        # 确保节点运行
        if not fork_url:
            # 本地节点不需要 fork
            _ensure_hardhat_node()
        else:
            _ensure_hardhat_node(fork_url, fork_block)
        
        if not requests:
            raise NonRetryableError("requests 库未安装。请安装: pip install requests")
        
        # 构建 eth_call 或 eth_sendTransaction 请求
        # 使用 eth_call 进行模拟（不会实际发送交易）
        payload = {
            "jsonrpc": "2.0",
            "method": "eth_call",
            "params": [transaction, "latest"],
            "id": 1
        }
        
        # 发送请求
        response = requests.post(
            rpc_url,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        # 检查是否有错误
        if "error" in data:
            error_msg = data["error"].get("message", "交易执行失败")
            return {
                "tool": "hardhat_network",
                "ok": False,
                "error": error_msg,
                "data": {
                    "transaction": transaction,
                    "error": data["error"]
                }
            }
        
        result_hex = data.get("result", "0x")
        
        # 获取 gas 估算
        gas_payload = {
            "jsonrpc": "2.0",
            "method": "eth_estimateGas",
            "params": [transaction],
            "id": 2
        }
        
        gas_response = requests.post(rpc_url, json=gas_payload, timeout=30)
        gas_used = 0
        if gas_response.status_code == 200:
            gas_data = gas_response.json()
            if "result" in gas_data:
                gas_used = int(gas_data["result"], 16)
        
        # 获取交易回执（如果使用 eth_sendTransaction）
        receipt = None
        logs = []
        
        return {
            "tool": "hardhat_network",
            "ok": True,
            "data": {
                "status": "success",
                "result": result_hex,
                "gas_used": gas_used,
                "transaction": transaction,
                "receipt": receipt,
                "logs": logs,
                "rpc_url": rpc_url,
                "forked": bool(fork_url),
                "fork_block": fork_block
            }
        }
        
    except requests.exceptions.ConnectionError:
        raise RetryableError(f"无法连接到 Hardhat 节点: {rpc_url}")
    except requests.exceptions.Timeout:
        raise RetryableError("Hardhat 节点请求超时")
    except NonRetryableError:
        raise
    except Exception as e:
        raise RetryableError(f"Hardhat Network 模拟失败: {e}")


def hardhat_query(
    method: str,
    params: List = None,
    rpc_url: Optional[str] = None
) -> dict:
    """
    查询 Hardhat Network 状态
    
    Args:
        method: RPC 方法名（如 "eth_blockNumber", "eth_getBalance"）
        params: RPC 方法参数
        rpc_url: Hardhat 节点 RPC URL（可选）
    
    Returns:
        dict: 查询结果
    """
    rpc_url = rpc_url or f"http://localhost:{_hardhat_port}"
    params = params or []
    
    if not requests:
        return {
            "tool": "hardhat_network",
            "ok": False,
            "error": "requests 库未安装。请安装: pip install requests"
        }
    
    try:
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1
        }
        
        response = requests.post(rpc_url, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "error" in data:
            return {
                "tool": "hardhat_network",
                "ok": False,
                "error": data["error"].get("message", "查询失败"),
                "data": data["error"]
            }
        
        return {
            "tool": "hardhat_network",
            "ok": True,
            "data": {
                "method": method,
                "result": data.get("result")
            }
        }
        
    except Exception as e:
        return {
            "tool": "hardhat_network",
            "ok": False,
            "error": str(e)
        }

