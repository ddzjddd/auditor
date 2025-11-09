# src/tools/chain_state.py
import sys
from pathlib import Path
from web3 import Web3
import requests
import json

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.schemas import ChainStateArgs
from utils.cache import cached_tool
from utils.retry import retry_with_backoff, RetryableError, NonRetryableError
from utils.logger import get_logger

logger = get_logger()


@cached_tool("read_chain_state")
@retry_with_backoff(retryable_exceptions=[ConnectionError, TimeoutError])
def read_chain_state(chain: str, address: str) -> dict:
    """
    读取链上部署状态与关键槽位（proxy实现地址、owner、roles、paused等）
    兼容主流 EVM 链。
    
    Args:
        chain: 链名称
        address: 合约地址
    
    Returns:
        dict: {"tool": "chain_state", "ok": bool, "data": dict}
    """
    # 参数验证
    try:
        args = ChainStateArgs(chain=chain, address=address)
        chain = args.chain
        address = args.address
    except Exception as e:
        raise NonRetryableError(f"参数验证失败: {e}")
    
    logger.info(f"查询链状态: {chain}/{address}", tool_name="read_chain_state", tool_args={"chain": chain, "address": address})
    
    try:
        rpc_endpoints = {
            "ethereum": "https://eth.llamarpc.com",
            "arbitrum": "https://arb1.arbitrum.io/rpc",
            "bsc": "https://bsc-dataseed.binance.org",
            "polygon": "https://polygon-rpc.com",
            "optimism": "https://mainnet.optimism.io",
            "base": "https://mainnet.base.org"
        }
        if chain not in rpc_endpoints:
            raise NonRetryableError(f"不支持的链: {chain}")

        w3 = Web3(Web3.HTTPProvider(rpc_endpoints[chain]))
        addr = Web3.to_checksum_address(address)

        # Proxy 实现槽位 (EIP-1967 / OpenZeppelin)
        impl_slot = "0x" + hex(int(Web3.keccak(text="eip1967.proxy.implementation")) - 1 & ((1 << 256) - 1))[2:]
        raw = w3.eth.get_storage_at(addr, impl_slot)
        impl_address = "0x" + raw.hex()[-40:] if int.from_bytes(raw, "big") != 0 else None

        # 读取 owner / paused 状态
        abi_owner = [{"name": "owner", "outputs": [{"type": "address"}], "inputs": [], "stateMutability": "view", "type": "function"}]
        abi_paused = [{"name": "paused", "outputs": [{"type": "bool"}], "inputs": [], "stateMutability": "view", "type": "function"}]
        contract = w3.eth.contract(address=addr, abi=abi_owner + abi_paused)

        try:
            owner = contract.functions.owner().call()
        except Exception:
            owner = None
        try:
            paused = contract.functions.paused().call()
        except Exception:
            paused = None

        # 尝试读取 AccessControl role 列表（若存在）
        roles = {}
        try:
            role_names = ["DEFAULT_ADMIN_ROLE", "UPGRADER_ROLE", "PAUSER_ROLE"]
            for r in role_names:
                role_hash = Web3.keccak(text=r).hex()
                has_role_fn = contract.get_function_by_name("hasRole")
                admins = []
                for account in [owner] if owner else []:
                    try:
                        if has_role_fn(role_hash, account).call():
                            admins.append(account)
                    except Exception:
                        pass
                roles[r] = admins
        except Exception:
            roles = {}

        return {
            "tool": "chain_state",
            "ok": True,
            "data": {
                "chain": chain,
                "address": addr,
                "implementation": impl_address,
                "owner": owner,
                "paused": paused,
                "roles": roles
            }
        }

    except NonRetryableError:
        raise
    except Exception as e:
        raise RetryableError(f"查询链状态失败: {e}")
