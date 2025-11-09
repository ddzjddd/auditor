#!/usr/bin/env python3
"""
填充 RAG Corpus 内容
从 SWC Registry、OpenZeppelin 文档等来源获取内容
"""
import os
import sys
import json
import re
from pathlib import Path
import httpx
from typing import Dict, List

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

CORPUS_DIR = Path(__file__).parent / "corpus"
CORPUS_DIR.mkdir(parents=True, exist_ok=True)

# SWC Registry 基础信息
SWC_ENTRIES = {
    101: "Integer Overflow and Underflow",
    102: "Outdated Compiler Version",
    103: "Floating Pragma",
    104: "Unchecked Call Return Value",
    105: "Unprotected Ether Withdrawal",
    106: "Unprotected SELFDESTRUCT Instruction",
    107: "Reentrancy",
    108: "State Variable Default Visibility",
    109: "Uninitialized Storage Pointer",
    110: "Assert Violation",
    111: "Use of Deprecated Solidity Functions",
    112: "Delegatecall to Untrusted Callee",
    113: "DoS with Failed Call",
    114: "Transaction Order Dependence",
    115: "Authorization through tx.origin",
    116: "Timestamp Dependence",
    117: "Signature Malleability",
    118: "Incorrect Constructor Name",
    119: "Shadowing State Variables",
    120: "Weak Sources of Randomness from Chain Attributes",
    121: "Missing Protection against Signature Replay Attacks",
    122: "Lack of Proper Signature Verification",
    123: "Requirement Violation",
    124: "Write to Arbitrary Storage Location",
    125: "Incorrect Inheritance Order",
    126: "Insufficient Gas Griefing",
    127: "Arbitrary Jump with Function Type Variable",
    128: "DoS With Block Gas Limit",
    129: "Typographical Error",
    130: "Right-to-Left-Override control character (RLO)",
    131: "Presence of unused variables",
    132: "Unexpected Ether balance",
    133: "Hash Collisions With Multiple Variable Length Arguments",
    134: "Message call with hardcoded gas amount",
    135: "Code With No Effects",
    136: "Unencrypted Private Data On-Chain",
    137: "Storage of Unencrypted Private Data",
    138: "Uninitialized Return Variable",
    139: "Unpredictable State",
    140: "Missing Protection against Signature Replay Attacks",
    141: "Integer Overflow",
    142: "Proper Signature Verification",
    143: "Deprecated Solidity Pragmas",
    144: "Uninitialized Local Variable",
    145: "Dangerous Public Function",
    146: "Improper Verification of Cryptographic Signature",
    147: "Improper Verification of Cryptographic Signature",
    148: "Arbitrary Write to Fixed-Size Array",
    149: "Classification - Access Control",
    150: "Classification - Arithmetic",
    151: "Classification - DoS",
    152: "Classification - Environment",
    153: "Classification - Randomness",
    154: "Classification - Time",
    155: "Classification - Unchecked Return Values",
}


def fetch_swc_content(swc_id: int) -> str:
    """从 SWC Registry 获取内容"""
    url = f"https://swcregistry.io/docs/SWC-{swc_id}"
    title = SWC_ENTRIES.get(swc_id, 'Unknown')
    
    # 根据 SWC ID 提供更具体的修复建议
    specific_advice = _get_swc_specific_advice(swc_id)
    
    try:
        with httpx.Client(timeout=10, follow_redirects=True) as client:
            response = client.get(url)
            if response.status_code == 200:
                # 简单提取主要内容（实际应该用更好的HTML解析）
                content = response.text
                # 提取标题
                title_match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE)
                if title_match:
                    title = title_match.group(1).strip()
                
                # 提取描述（简化版）
                desc_match = re.search(r'<meta name="description" content="(.*?)"', content, re.IGNORECASE)
                description = desc_match.group(1) if desc_match else ""
                
                return f"""# SWC-{swc_id}: {title}

## 描述
{description or '请参考官方文档获取详细信息'}

## 详细信息
请访问: {url}

## 常见场景
{specific_advice.get('scenarios', '请参考 SWC Registry 官方文档获取详细信息和示例。')}

## 修复建议
{specific_advice.get('fixes', '1. 使用最新版本的 Solidity 编译器\n2. 启用所有编译器警告\n3. 进行全面的安全审计\n4. 使用 OpenZeppelin 等经过审计的库')}

## 相关 SWC
{specific_advice.get('related', '')}
"""
    except httpx.TimeoutException:
        print(f"  ⚠️  SWC-{swc_id} 请求超时，使用默认内容")
    except httpx.RequestError as e:
        print(f"  ⚠️  SWC-{swc_id} 网络错误: {e}")
    except Exception as e:
        print(f"  ⚠️  SWC-{swc_id} 获取内容失败: {e}")
    
    # 返回默认内容
    return f"""# SWC-{swc_id}: {title}

## 描述
{SWC_ENTRIES.get(swc_id, 'Unknown vulnerability pattern')}

## 详细信息
请访问: {url}

## 常见场景
{specific_advice.get('scenarios', '请参考 SWC Registry 官方文档获取详细信息和示例。')}

## 修复建议
{specific_advice.get('fixes', '1. 使用最新版本的 Solidity 编译器\n2. 启用所有编译器警告\n3. 进行全面的安全审计\n4. 使用 OpenZeppelin 等经过审计的库')}

## 相关 SWC
{specific_advice.get('related', '')}
"""


def _get_swc_specific_advice(swc_id: int) -> Dict[str, str]:
    """根据 SWC ID 返回特定的建议"""
    advice_map = {
        101: {
            'scenarios': '- 整数溢出：`uint256 x = type(uint256).max; x + 1` 会溢出\n- 整数下溢：`uint256 x = 0; x - 1` 会下溢',
            'fixes': '1. 使用 Solidity 0.8.0+（内置溢出检查）\n2. 或使用 OpenZeppelin 的 SafeMath 库\n3. 在关键计算前检查边界条件',
            'related': '- SWC-141: Integer Overflow'
        },
        107: {
            'scenarios': '- 外部调用后更新状态：攻击者可以在回调中重入\n- 跨函数重入：通过不同函数重入',
            'fixes': '1. 使用 ReentrancyGuard 的 `nonReentrant` 修饰符\n2. 遵循 CEI 模式（Checks-Effects-Interactions）\n3. 先更新状态，再进行外部调用',
            'related': '- SWC-113: DoS with Failed Call'
        },
        104: {
            'scenarios': '- 调用 `transfer()` 但不检查返回值\n- 某些代币（如 USDT）不返回 bool 值',
            'fixes': '1. 使用 OpenZeppelin 的 SafeERC20\n2. 始终检查外部调用的返回值\n3. 使用 `require(success)` 验证调用结果',
            'related': '- SWC-113: DoS with Failed Call'
        },
        105: {
            'scenarios': '- 缺少访问控制的提现函数\n- 任何人都可以调用关键函数',
            'fixes': '1. 使用 `onlyOwner` 或 `onlyRole` 修饰符\n2. 实现多签钱包控制\n3. 使用时间锁延迟关键操作',
            'related': '- SWC-115: Authorization through tx.origin'
        },
        112: {
            'scenarios': '- 委托调用不可信合约\n- 存储布局冲突',
            'fixes': '1. 仅委托调用可信合约\n2. 验证目标地址\n3. 使用库模式而非委托调用',
            'related': ''
        },
        116: {
            'scenarios': '- 使用 `block.timestamp` 作为随机源\n- 依赖 `block.number` 进行时间计算',
            'fixes': '1. 避免使用 block.timestamp 作为随机源\n2. 使用 Chainlink VRF 或其他可信随机源\n3. 使用 commit-reveal 方案',
            'related': '- SWC-120: Weak Sources of Randomness'
        },
    }
    
    return advice_map.get(swc_id, {
        'scenarios': '请参考 SWC Registry 官方文档获取详细信息和示例。',
        'fixes': '1. 使用最新版本的 Solidity 编译器\n2. 启用所有编译器警告\n3. 进行全面的安全审计\n4. 使用 OpenZeppelin 等经过审计的库',
        'related': ''
    })


def populate_swc_files(force: bool = False):
    """填充 SWC 文件
    
    Args:
        force: 如果为 True，强制重新生成所有文件
    """
    swc_dir = CORPUS_DIR / "swc"
    swc_dir.mkdir(exist_ok=True)
    
    print("📚 填充 SWC 漏洞库文件...")
    total = len(SWC_ENTRIES)
    success_count = 0
    skip_count = 0
    
    for idx, swc_id in enumerate(sorted(SWC_ENTRIES.keys()), 1):
        file_path = swc_dir / f"swc-{swc_id}.md"
        
        if not force and file_path.exists() and file_path.stat().st_size > 200:
            print(f"  [{idx}/{total}] ⏭️  SWC-{swc_id} 已存在，跳过")
            skip_count += 1
            continue
        
        print(f"  [{idx}/{total}] 📝 生成 SWC-{swc_id}...", end=" ", flush=True)
        try:
            content = fetch_swc_content(swc_id)
            file_path.write_text(content, encoding="utf-8")
            print("✅")
            success_count += 1
        except Exception as e:
            print(f"❌ 错误: {e}")
    
    print(f"✅ SWC 文件填充完成: {success_count} 个生成, {skip_count} 个跳过")


def populate_oz_files():
    """填充 OpenZeppelin 文件"""
    oz_dir = CORPUS_DIR / "oz"
    oz_dir.mkdir(exist_ok=True)
    
    print("📚 填充 OpenZeppelin 文件...")
    
    # AccessControl
    (oz_dir / "AccessControl.md").write_text("""# AccessControl / 角色控制

## 概述
OpenZeppelin 的 AccessControl 提供了基于角色的访问控制（RBAC）机制。

## 核心功能
- `hasRole(role, account)`: 检查账户是否拥有特定角色
- `grantRole(role, account)`: 授予角色
- `revokeRole(role, account)`: 撤销角色
- `renounceRole(role, account)`: 账户主动放弃角色

## 使用示例
```solidity
import "@openzeppelin/contracts/access/AccessControl.sol";

contract MyContract is AccessControl {
    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    
    constructor() {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
    }
    
    function mint(address to, uint256 amount) public onlyRole(MINTER_ROLE) {
        // mint logic
    }
}
```

## 最佳实践
1. 使用 `DEFAULT_ADMIN_ROLE` 作为超级管理员角色
2. 为每个功能定义独立的角色（如 MINTER_ROLE, BURNER_ROLE）
3. 使用 `onlyRole` 修饰符保护敏感函数
4. 避免在构造函数外直接调用 `_grantRole`，使用 `grantRole` 并通过事件追踪

## 常见错误
- 忘记授予 DEFAULT_ADMIN_ROLE，导致无法管理其他角色
- 使用 `onlyOwner` 而不是 `onlyRole`，限制了灵活性
- 没有正确设置角色层级关系

## 安全注意事项
- 确保 DEFAULT_ADMIN_ROLE 的持有者可信
- 考虑使用多签钱包管理管理员角色
- 定期审查角色分配情况
""", encoding="utf-8")
    
    # ReentrancyGuard
    (oz_dir / "ReentrancyGuard.md").write_text("""# ReentrancyGuard / 重入保护

## 概述
ReentrancyGuard 提供了防止重入攻击的保护机制。

## 核心功能
- `nonReentrant` 修饰符：防止函数在执行期间被重入调用
- 使用状态变量 `_status` 跟踪重入状态

## 使用示例
```solidity
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

contract MyContract is ReentrancyGuard {
    mapping(address => uint256) public balances;
    
    function withdraw(uint256 amount) public nonReentrant {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        
        balances[msg.sender] -= amount;
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
    }
}
```

## 最佳实践
1. 在外部调用之前更新状态（Checks-Effects-Interactions 模式）
2. 对所有涉及外部调用的函数使用 `nonReentrant` 修饰符
3. 对于复杂逻辑，考虑使用 ReentrancyGuard 的 `_reentrancyGuardEntered` 检查

## 常见错误
- 忘记在外部调用前更新状态
- 在 `nonReentrant` 函数中调用其他可能重入的函数
- 使用 `nonReentrant` 但未遵循 CEI 模式

## 安全注意事项
- `nonReentrant` 不能防止跨函数重入，需要仔细设计状态更新顺序
- 对于复杂合约，考虑使用更细粒度的重入保护
- 测试所有可能的重入路径
""", encoding="utf-8")
    
    # Ownable
    (oz_dir / "Ownable.md").write_text("""# Ownable / 所有权模式

## 概述
Ownable 提供了简单的单所有者访问控制模式。

## 核心功能
- `owner()`: 获取当前所有者地址
- `onlyOwner` 修饰符：限制函数仅所有者可调用
- `transferOwnership(newOwner)`: 转移所有权
- `renounceOwnership()`: 放弃所有权（使合约无主）

## 使用示例
```solidity
import "@openzeppelin/contracts/access/Ownable.sol";

contract MyContract is Ownable {
    function sensitiveFunction() public onlyOwner {
        // 只有所有者可以调用
    }
    
    function transferOwnership(address newOwner) public override onlyOwner {
        require(newOwner != address(0), "New owner cannot be zero address");
        super.transferOwnership(newOwner);
    }
}
```

## 最佳实践
1. 在构造函数中设置初始所有者
2. 转移所有权前验证新所有者地址不为零地址
3. 对于重要操作，考虑使用多签钱包作为所有者
4. 谨慎使用 `renounceOwnership()`，确保合约不再需要所有者控制

## 常见错误
- 忘记在构造函数中设置所有者
- 转移所有权到零地址或错误地址
- 在不需要时使用 `renounceOwnership()`，导致合约无法升级

## 安全注意事项
- 所有者拥有完全控制权，必须妥善保管私钥
- 考虑使用时间锁延迟关键操作
- 对于生产环境，建议使用 AccessControl 而不是 Ownable
""", encoding="utf-8")
    
    # UUPSUpgradeable
    (oz_dir / "UUPSUpgradeable.md").write_text("""# UUPSUpgradeable / 升级代理模式

## 概述
UUPS (Universal Upgradeable Proxy Standard) 是一种可升级合约模式。

## 核心功能
- `_authorizeUpgrade(newImplementation)`: 授权升级的内部函数
- `upgradeTo(newImplementation)`: 升级到新实现
- `upgradeToAndCall(newImplementation, data)`: 升级并调用初始化函数

## 使用示例
```solidity
import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";

contract MyContract is UUPSUpgradeable, OwnableUpgradeable {
    uint256 public value;
    
    function initialize() public initializer {
        __Ownable_init();
        __UUPSUpgradeable_init();
    }
    
    function _authorizeUpgrade(address newImplementation) 
        internal 
        override 
        onlyOwner 
    {
        // 只有所有者可以授权升级
    }
    
    function setValue(uint256 _value) public {
        value = _value;
    }
}
```

## 最佳实践
1. 必须使用 `onlyOwner` 或其他访问控制保护 `_authorizeUpgrade`
2. 在升级前充分测试新实现
3. 使用 `upgradeToAndCall` 进行初始化时，确保数据格式正确
4. 考虑使用时间锁延迟升级操作

## 常见错误
- 忘记保护 `_authorizeUpgrade`，导致任何人都可以升级
- 在升级后的实现中修改存储布局，导致数据损坏
- 忘记调用 `__UUPSUpgradeable_init()` 或 `__Ownable_init()`

## 安全注意事项
- 升级是高风险操作，必须严格控制访问权限
- 确保新实现与旧实现的存储布局兼容
- 在生产环境升级前，在测试网充分测试
- 考虑使用多签钱包和时间锁管理升级权限
""", encoding="utf-8")
    
    print("✅ OpenZeppelin 文件填充完成")


def populate_best_practices():
    """填充最佳实践文件"""
    bp_dir = CORPUS_DIR / "best_practices"
    bp_dir.mkdir(exist_ok=True)
    
    print("📚 填充最佳实践文件...")
    
    # ERC20 常见问题
    (bp_dir / "ERC20_common_issues.md").write_text("""# ERC20 常见问题 / Common Issues

## 1. approve 竞态条件 (Race Condition)

### 问题描述
当用户想要将授权从 A 改为 B 时，如果先调用 `approve(B, amount)`，恶意用户可能在前一个交易被确认前，使用旧的授权额度。

### 解决方案
使用 `increaseAllowance` 和 `decreaseAllowance`，或先设置为 0 再设置新值：
```solidity
function safeApprove(address spender, uint256 amount) external {
    require(allowance[msg.sender][spender] == 0, "Approve must be zero first");
    _approve(msg.sender, spender, amount);
}
```

## 2. 返回值缺失

### 问题描述
ERC20 标准要求 `transfer` 和 `transferFrom` 返回 bool，但某些代币（如 USDT）不返回。

### 解决方案
使用 OpenZeppelin 的 SafeERC20：
```solidity
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

using SafeERC20 for IERC20;
token.safeTransfer(to, amount); // 自动处理返回值
```

## 3. 精度问题

### 问题描述
某些代币使用非常小的精度（如 18 位小数），在计算时可能出现精度损失。

### 解决方案
- 使用足够大的整数进行计算
- 最后再除以精度因子
- 使用 SafeMath（Solidity < 0.8）或依赖内置溢出检查（>= 0.8）

## 4. 重入攻击

### 问题描述
在 `transfer` 回调中可能触发重入攻击。

### 解决方案
- 使用 ReentrancyGuard
- 遵循 Checks-Effects-Interactions 模式
- 在外部调用前更新状态

## 5. 前端运行攻击 (Front-running)

### 问题描述
交易在 mempool 中可见，攻击者可能抢先执行。

### 解决方案
- 使用 commit-reveal 方案
- 设置最小/最大价格限制
- 使用私有 mempool（如 Flashbots）

## 最佳实践总结
1. 始终使用 OpenZeppelin 的实现
2. 进行全面的单元测试
3. 使用静态分析工具（Slither, Mythril）
4. 进行专业的安全审计
5. 实现时间锁和多重签名保护关键操作
""", encoding="utf-8")
    
    # 代理模式
    (bp_dir / "Proxy_patterns.md").write_text("""# 代理模式 / Proxy Patterns

## Transparent Proxy Pattern

### 特点
- 管理员调用和用户调用通过不同路径
- 避免函数选择器冲突
- 实现相对简单

### 使用场景
适合大多数可升级合约场景。

### 示例
```solidity
import "@openzeppelin/contracts/proxy/transparent/TransparentUpgradeableProxy.sol";
```

## UUPS (Universal Upgradeable Proxy Standard)

### 特点
- 升级逻辑在实现合约中
- Gas 成本更低
- 更灵活

### 使用场景
适合需要频繁升级的合约。

### 安全注意事项
- 必须保护 `_authorizeUpgrade` 函数
- 确保存储布局兼容性

## Beacon Proxy Pattern

### 特点
- 多个代理共享同一个实现
- 一次升级影响所有代理
- 适合工厂模式

### 使用场景
适合需要部署多个相同合约实例的场景。

## 安全最佳实践

### 1. 存储布局兼容性
```solidity
// ❌ 错误：在现有变量之间插入新变量
contract V1 {
    uint256 public a;
    uint256 public b; // 新变量
    uint256 public c;
}

// ✅ 正确：在末尾添加新变量
contract V2 {
    uint256 public a;
    uint256 public c;
    uint256 public b; // 新变量在末尾
}
```

### 2. 初始化器保护
```solidity
contract MyContract {
    bool private initialized;
    
    function initialize() external {
        require(!initialized, "Already initialized");
        initialized = true;
        // 初始化逻辑
    }
}
```

### 3. 代理存储槽冲突
使用 EIP-1967 标准存储槽：
- Implementation: `bytes32(uint256(keccak256('eip1967.proxy.implementation')) - 1)`
- Admin: `bytes32(uint256(keccak256('eip1967.proxy.admin')) - 1)`

## 常见错误
1. 修改存储变量顺序
2. 忘记保护升级函数
3. 在实现合约中使用构造函数（应使用初始化函数）
4. 存储槽冲突

## 推荐工具
- OpenZeppelin Upgrades Plugin
- Hardhat Upgrades
- Foundry 的 forge upgrade
""", encoding="utf-8")
    
    # 治理与多签
    (bp_dir / "Governance_and_Multisig.md").write_text("""# 治理与多签 / Governance and Multisig

## 多签钱包

### Gnosis Safe
最流行的多签钱包解决方案：
- 支持任意数量的签名者
- 可配置阈值（如 3/5）
- 提供丰富的功能（模块、插件）

### 使用场景
- 管理合约所有者权限
- 控制资金转移
- 执行关键操作（升级、参数修改）

## 时间锁 (Timelock)

### 作用
延迟关键操作的执行，给社区时间审查和响应。

### 实现
```solidity
import "@openzeppelin/contracts/governance/TimelockController.sol";

contract MyTimelock is TimelockController {
    constructor(
        uint256 minDelay,
        address[] memory proposers,
        address[] memory executors
    ) TimelockController(minDelay, proposers, executors) {}
}
```

### 最佳实践
- 关键操作至少延迟 24-48 小时
- 紧急操作可以设置更短的延迟
- 使用多签钱包作为 proposer

## DAO 治理

### 投票机制
1. **简单多数投票**：超过 50% 支持即通过
2. **法定人数投票**：需要达到最小投票人数
3. **加权投票**：根据代币持有量加权

### 提案流程
1. 创建提案
2. 投票期（通常 3-7 天）
3. 执行期（提案通过后可执行）
4. 时间锁延迟（可选）

## 安全最佳实践

### 1. 多签配置
- 至少 3 个签名者
- 阈值设置为 2/3 或更高
- 使用硬件钱包作为签名者

### 2. 时间锁配置
- 关键操作延迟至少 24 小时
- 使用多签钱包控制时间锁
- 定期审查待执行操作

### 3. 治理代币
- 防止代币集中持有
- 实施反女巫攻击机制
- 考虑委托投票

## 常见错误
1. 多签阈值设置过低（如 1/3）
2. 忘记实施时间锁
3. 治理代币可被恶意集中
4. 提案执行无时间限制

## 推荐工具
- Gnosis Safe
- OpenZeppelin Governor
- Compound Governor
- Aragon
""", encoding="utf-8")
    
    # 审计报告模板
    (bp_dir / "Audit_report_template.md").write_text("""# 审计报告模板 / Audit Report Template

## 报告结构

### 1. 执行摘要 (Executive Summary)
- 审计范围
- 审计方法
- 总体风险评估
- 关键发现摘要

### 2. 漏洞分类

#### Critical (严重)
- 可能导致资金损失或合约完全失效
- 示例：重入攻击、整数溢出、未授权访问

#### High (高危)
- 可能导致部分资金损失或功能失效
- 示例：逻辑错误、访问控制缺陷

#### Medium (中危)
- 可能导致功能异常或用户体验问题
- 示例：Gas 优化、边界条件处理

#### Low (低危)
- 代码质量问题，不影响功能
- 示例：代码风格、注释缺失

#### Informational (信息)
- 建议和改进意见
- 示例：最佳实践建议、代码优化

### 3. 详细发现

每个发现应包含：
```
### [H-01] 标题

**描述**：
详细描述问题

**影响**：
说明可能的影响和后果

**位置**：
文件路径和行号

**代码**：
```solidity
// 问题代码
```

**修复建议**：
```solidity
// 修复后的代码
```

**参考**：
相关 SWC 编号或文档链接
```

### 4. 测试覆盖

- 单元测试覆盖率
- 集成测试情况
- 模糊测试结果

### 5. 工具扫描结果

- Slither 扫描结果
- Mythril 分析结果
- 其他工具发现

### 6. 建议

- 代码改进建议
- 架构优化建议
- 安全增强建议

## 报告示例格式

```markdown
# 审计报告

**项目名称**: Token Contract
**审计日期**: 2024-01-01
**审计范围**: contracts/Token.sol
**审计方法**: 手动审查 + 自动化工具

## 摘要
- Critical: 2
- High: 5
- Medium: 8
- Low: 3

## 详细发现

### [C-01] 重入漏洞
...
```

## 最佳实践
1. 使用标准化的严重程度分类
2. 提供清晰的修复建议
3. 包含代码示例和 PoC
4. 参考 SWC 和 CWE 分类
5. 提供可执行的修复代码
""", encoding="utf-8")
    
    print("✅ 最佳实践文件填充完成")


def populate_reports():
    """填充审计报告示例"""
    reports_dir = CORPUS_DIR / "reports"
    reports_dir.mkdir(exist_ok=True)
    
    print("📚 填充审计报告示例...")
    
    # Vault 审计报告示例
    (reports_dir / "example_vault_audit.md").write_text("""# Vault Contract 审计报告示例

## 执行摘要

**审计目标**: Vault.sol - 资金管理合约
**审计日期**: 2024-01-01
**审计方法**: 手动代码审查 + 自动化工具扫描

**总体风险评估**: 中等风险
- Critical: 1
- High: 2
- Medium: 3
- Low: 1

## 详细发现

### [C-01] 重入漏洞

**描述**：
`withdraw()` 函数在更新余额之前进行外部调用，存在重入攻击风险。

**影响**：
攻击者可以通过重入调用多次提取资金，导致资金损失。

**位置**：
`Vault.sol:45-52`

**代码**：
```solidity
function withdraw(uint256 amount) public {
    require(balances[msg.sender] >= amount, "Insufficient balance");
    (bool success, ) = msg.sender.call{value: amount}("");
    require(success, "Transfer failed");
    balances[msg.sender] -= amount; // 状态更新在外部调用之后
}
```

**修复建议**：
```solidity
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

contract Vault is ReentrancyGuard {
    function withdraw(uint256 amount) public nonReentrant {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        balances[msg.sender] -= amount; // 先更新状态
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
    }
}
```

**参考**：
- SWC-107: Reentrancy

### [H-01] 未检查外部调用返回值

**描述**：
虽然代码检查了 `success`，但某些代币合约可能不遵循标准，导致调用失败但返回 true。

**影响**：
可能导致资金丢失或状态不一致。

**位置**：
`Vault.sol:48`

**修复建议**：
使用 OpenZeppelin 的 SafeERC20 库处理代币转账。

### [H-02] 访问控制缺失

**描述**：
`setFeeRate()` 函数没有访问控制，任何人都可以修改费率。

**影响**：
攻击者可以将费率设置为 100%，窃取所有资金。

**位置**：
`Vault.sol:60`

**修复建议**：
```solidity
function setFeeRate(uint256 _feeRate) public onlyOwner {
    require(_feeRate <= 1000, "Fee rate too high"); // 最大 10%
    feeRate = _feeRate;
}
```

### [M-01] Gas 优化

**描述**：
`deposit()` 函数中的循环可以优化。

**位置**：
`Vault.sol:30-35`

### [M-02] 事件缺失

**描述**：
关键操作（deposit, withdraw）未发出事件。

**修复建议**：
添加事件以便链下监控和审计。

### [M-03] 整数溢出风险

**描述**：
虽然 Solidity 0.8+ 有内置溢出检查，但建议使用 SafeMath 进行显式检查。

### [L-01] 代码注释不足

**描述**：
部分复杂逻辑缺少注释说明。

## 测试覆盖

- 单元测试覆盖率: 85%
- 集成测试: 通过
- 模糊测试: 发现 2 个边界条件问题

## 工具扫描结果

### Slither
- 发现 3 个中危问题
- 1 个低危问题

### Mythril
- 发现 1 个重入漏洞（已修复）

## 建议

1. 实施全面的访问控制机制
2. 添加事件记录所有关键操作
3. 增加单元测试覆盖率至 95%+
4. 考虑实施时间锁保护关键参数修改
5. 进行专业的安全审计

## 结论

合约在修复上述问题后可以部署，但建议进行第二轮审计以确保所有问题已解决。
""", encoding="utf-8")
    
    # Token 审计报告示例
    (reports_dir / "example_token_audit.md").write_text("""# ERC20 Token Contract 审计报告示例

## 执行摘要

**审计目标**: Token.sol - ERC20 代币合约
**审计日期**: 2024-01-15
**审计方法**: 手动代码审查 + 自动化工具扫描

**总体风险评估**: 低风险
- Critical: 0
- High: 1
- Medium: 2
- Low: 2

## 详细发现

### [H-01] approve 竞态条件

**描述**：
`approve()` 函数存在竞态条件，用户无法安全地更改授权额度。

**影响**：
用户可能无法及时撤销或修改授权，导致资金风险。

**位置**：
`Token.sol:45`

**修复建议**：
使用 `increaseAllowance` 和 `decreaseAllowance`，或先设置为 0 再设置新值。

### [M-01] 缺少暂停机制

**描述**：
合约缺少紧急暂停功能，在发现漏洞时无法及时停止交易。

**修复建议**：
继承 OpenZeppelin 的 `Pausable` 合约。

### [M-02] 最大供应量检查

**描述**：
`mint()` 函数未检查是否会超过最大供应量。

**修复建议**：
添加最大供应量检查和限制。

## 结论

合约整体实现良好，建议修复上述问题后部署。
""", encoding="utf-8")
    
    print("✅ 审计报告示例填充完成")


def populate_more_oz_files():
    """填充更多 OpenZeppelin 合约文档"""
    oz_dir = CORPUS_DIR / "oz"
    oz_dir.mkdir(exist_ok=True)
    
    print("📚 填充更多 OpenZeppelin 文件...")
    
    # ERC20
    (oz_dir / "ERC20.md").write_text("""# ERC20 / 代币标准

## 概述
ERC20 是以太坊上最常用的代币标准，定义了可互换代币的基本接口。

## 核心函数
- `totalSupply()`: 返回代币总供应量
- `balanceOf(account)`: 返回账户余额
- `transfer(to, amount)`: 转账代币
- `transferFrom(from, to, amount)`: 从指定地址转账
- `approve(spender, amount)`: 授权支出额度
- `allowance(owner, spender)`: 查询授权额度

## 使用示例
```solidity
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract MyToken is ERC20 {
    constructor() ERC20("MyToken", "MTK") {
        _mint(msg.sender, 1000000 * 10**decimals());
    }
}
```

## 最佳实践
1. 使用 OpenZeppelin 的标准实现
2. 注意 `approve` 的竞态条件问题
3. 使用 SafeERC20 处理非标准代币
4. 实现适当的访问控制

## 常见错误
- 忘记实现 `decimals()` 函数
- `approve` 竞态条件
- 未检查返回值（某些代币如 USDT）
- 精度计算错误

## 安全注意事项
- 防止整数溢出（Solidity 0.8+ 已内置）
- 实现适当的访问控制
- 考虑添加暂停机制
- 防止重入攻击
""", encoding="utf-8")
    
    # ERC721
    (oz_dir / "ERC721.md").write_text("""# ERC721 / 非同质化代币标准

## 概述
ERC721 定义了非同质化代币（NFT）的标准接口，每个代币都是唯一的。

## 核心函数
- `balanceOf(owner)`: 返回所有者拥有的 NFT 数量
- `ownerOf(tokenId)`: 返回 NFT 的所有者
- `safeTransferFrom(from, to, tokenId)`: 安全转账
- `approve(to, tokenId)`: 授权单个 NFT
- `setApprovalForAll(operator, approved)`: 授权所有 NFT
- `getApproved(tokenId)`: 查询授权地址

## 使用示例
```solidity
import "@openzeppelin/contracts/token/ERC721/ERC721.sol";

contract MyNFT is ERC721 {
    uint256 private _tokenIdCounter;
    
    constructor() ERC721("MyNFT", "MNFT") {}
    
    function mint(address to) public returns (uint256) {
        uint256 tokenId = _tokenIdCounter;
        _tokenIdCounter++;
        _safeMint(to, tokenId);
        return tokenId;
    }
}
```

## 最佳实践
1. 使用 `_safeMint` 而不是 `_mint`（检查接收者是否支持 ERC721）
2. 实现适当的访问控制
3. 考虑实现元数据接口（ERC721Metadata）
4. 使用枚举器接口（ERC721Enumerable）如果需要遍历

## 常见错误
- 忘记检查 tokenId 是否存在
- 未实现 `_beforeTokenTransfer` 钩子
- 授权逻辑错误
- 重入攻击风险

## 安全注意事项
- 防止重入攻击
- 实现适当的访问控制
- 检查接收者地址
- 防止整数溢出
""", encoding="utf-8")
    
    # Pausable
    (oz_dir / "Pausable.md").write_text("""# Pausable / 暂停机制

## 概述
Pausable 提供了紧急暂停合约功能的机制，在发现漏洞时可以及时停止交易。

## 核心功能
- `paused()`: 检查合约是否已暂停
- `pause()`: 暂停合约
- `unpause()`: 恢复合约
- `whenNotPaused` 修饰符：仅在未暂停时执行

## 使用示例
```solidity
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract MyContract is Pausable, Ownable {
    function transfer(address to, uint256 amount) 
        public 
        whenNotPaused 
    {
        // 转账逻辑
    }
    
    function pause() public onlyOwner {
        _pause();
    }
    
    function unpause() public onlyOwner {
        _unpause();
    }
}
```

## 最佳实践
1. 使用多签钱包控制暂停权限
2. 考虑实施时间锁延迟暂停操作
3. 在关键函数上使用 `whenNotPaused` 修饰符
4. 提供清晰的暂停原因和恢复计划

## 常见错误
- 忘记在关键函数上添加 `whenNotPaused` 修饰符
- 暂停权限过于集中
- 没有恢复机制或计划

## 安全注意事项
- 暂停是紧急措施，不应滥用
- 确保有明确的恢复流程
- 考虑使用时间锁防止恶意暂停
""", encoding="utf-8")
    
    # SafeERC20
    (oz_dir / "SafeERC20.md").write_text("""# SafeERC20 / 安全 ERC20 操作

## 概述
SafeERC20 提供了安全的 ERC20 代币操作，处理非标准代币（如 USDT）的返回值问题。

## 核心功能
- `safeTransfer(token, to, value)`: 安全转账
- `safeTransferFrom(token, from, to, value)`: 安全转账从
- `safeApprove(token, spender, value)`: 安全授权
- `safeIncreaseAllowance(token, spender, value)`: 安全增加授权
- `safeDecreaseAllowance(token, spender, value)`: 安全减少授权

## 使用示例
```solidity
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

contract MyContract {
    using SafeERC20 for IERC20;
    
    function transferTokens(IERC20 token, address to, uint256 amount) public {
        token.safeTransfer(to, amount); // 自动处理返回值
    }
}
```

## 最佳实践
1. 始终使用 SafeERC20 处理外部代币
2. 使用 `safeIncreaseAllowance` 和 `safeDecreaseAllowance` 避免竞态条件
3. 不要混用 SafeERC20 和直接调用

## 常见错误
- 直接调用 `transfer` 而不使用 `safeTransfer`
- 忘记导入 `using SafeERC20 for IERC20`
- 混用 SafeERC20 和直接调用

## 安全注意事项
- SafeERC20 不能防止重入攻击，仍需使用 ReentrancyGuard
- 某些代币可能不遵循标准，SafeERC20 可以处理这些情况
""", encoding="utf-8")
    
    print("✅ 更多 OpenZeppelin 文件填充完成")


def populate_more_best_practices():
    """填充更多最佳实践内容"""
    bp_dir = CORPUS_DIR / "best_practices"
    bp_dir.mkdir(exist_ok=True)
    
    print("📚 填充更多最佳实践文件...")
    
    # Gas 优化
    (bp_dir / "Gas_optimization.md").write_text("""# Gas 优化 / Gas Optimization

## 存储优化

### 1. 使用打包存储
```solidity
// ❌ 浪费 Gas
struct User {
    uint256 id;        // 32 bytes
    uint128 balance;   // 16 bytes
    uint128 timestamp; // 16 bytes
}

// ✅ 优化：打包到单个存储槽
struct User {
    uint128 balance;   // 16 bytes
    uint128 timestamp; // 16 bytes
    uint256 id;        // 32 bytes
}
```

### 2. 使用事件而非存储
对于不需要链上访问的数据，使用事件而非存储变量。

### 3. 缓存存储变量
```solidity
// ❌ 多次读取存储
function update() public {
    users[msg.sender].balance += 1;
    users[msg.sender].count += 1;
    users[msg.sender].lastUpdate = block.timestamp;
}

// ✅ 优化：缓存到内存
function update() public {
    User storage user = users[msg.sender];
    user.balance += 1;
    user.count += 1;
    user.lastUpdate = block.timestamp;
}
```

## 函数优化

### 1. 使用 external 而非 public
对于不需要内部调用的函数，使用 `external` 可以节省 Gas。

### 2. 批量操作
```solidity
// ❌ 多次调用
function transferMany(address[] memory to, uint256[] memory amounts) public {
    for (uint i = 0; i < to.length; i++) {
        transfer(to[i], amounts[i]);
    }
}

// ✅ 优化：批量处理
function transferMany(address[] memory to, uint256[] memory amounts) public {
    require(to.length == amounts.length, "Length mismatch");
    for (uint i = 0; i < to.length; i++) {
        _transfer(msg.sender, to[i], amounts[i]);
    }
}
```

### 3. 短路评估
```solidity
// ✅ 使用 && 和 || 的短路特性
if (condition1 && condition2) {
    // 如果 condition1 为 false，不会评估 condition2
}
```

## 循环优化

### 1. 缓存数组长度
```solidity
// ❌ 每次循环都读取长度
for (uint i = 0; i < array.length; i++) {
    // ...
}

// ✅ 优化：缓存长度
uint length = array.length;
for (uint i = 0; i < length; i++) {
    // ...
}
```

### 2. 使用 unchecked 块
在确保不会溢出的情况下，使用 `unchecked` 块可以节省 Gas。

## 其他优化技巧

1. **使用自定义错误而非 require 字符串**
   ```solidity
   error InsufficientBalance();
   if (balance < amount) revert InsufficientBalance();
   ```

2. **使用 immutable 和 constant**
   ```solidity
   address public immutable owner;
   uint256 public constant MAX_SUPPLY = 1000000;
   ```

3. **避免不必要的零值检查**
   ```solidity
   // Solidity 0.8+ 自动检查，无需手动检查
   ```

4. **使用 assembly 进行低级优化**（仅在必要时）

## 工具
- Hardhat Gas Reporter
- Foundry Gas Snapshot
- Tenderly Gas Profiler
""", encoding="utf-8")
    
    # 测试最佳实践
    (bp_dir / "Testing_best_practices.md").write_text("""# 测试最佳实践 / Testing Best Practices

## 测试类型

### 1. 单元测试
测试单个函数或合约的功能。

### 2. 集成测试
测试多个合约之间的交互。

### 3. 模糊测试 (Fuzzing)
使用随机输入测试合约的健壮性。

### 4. 形式化验证
使用数学方法证明合约的正确性。

## 测试框架

### Foundry
```solidity
// test/MyContract.t.sol
import "forge-std/Test.sol";
import "../src/MyContract.sol";

contract MyContractTest is Test {
    MyContract public contract;
    
    function setUp() public {
        contract = new MyContract();
    }
    
    function testFunction() public {
        // 测试逻辑
    }
    
    function testFuzz(uint256 x) public {
        // 模糊测试
    }
}
```

### Hardhat
```javascript
const { expect } = require("chai");

describe("MyContract", function () {
    it("Should work correctly", async function () {
        // 测试逻辑
    });
});
```

## 测试覆盖

### 目标覆盖率
- 单元测试: 90%+
- 集成测试: 覆盖所有主要流程
- 边界条件: 100% 覆盖

### 关键测试场景
1. 正常流程
2. 边界条件（0, 最大值, 最小值）
3. 错误条件（revert 情况）
4. 重入攻击
5. 访问控制
6. 整数溢出/下溢
7. Gas 限制

## 最佳实践

### 1. 使用 Fixtures
```solidity
function setUp() public {
    // 设置测试环境
}
```

### 2. 测试事件
```solidity
vm.expectEmit(true, true, false, true);
emit Transfer(from, to, amount);
contract.transfer(to, amount);
```

### 3. 测试 Revert
```solidity
vm.expectRevert(InsufficientBalance.selector);
contract.withdraw(amount);
```

### 4. 使用快照
```solidity
uint256 snapshot = vm.snapshot();
// 修改状态
vm.revertTo(snapshot);
```

## 常见错误

1. 测试覆盖率不足
2. 未测试边界条件
3. 未测试错误情况
4. 测试过于简单
5. 未测试 Gas 消耗

## 工具推荐

- Foundry: 快速、强大的测试框架
- Hardhat: 流行的开发框架
- Echidna: 模糊测试工具
- Slither: 静态分析
- Mythril: 符号执行
""", encoding="utf-8")
    
    # 常见漏洞模式
    (bp_dir / "Common_vulnerability_patterns.md").write_text("""# 常见漏洞模式 / Common Vulnerability Patterns

## 1. 重入攻击 (Reentrancy)

### 模式
```solidity
// ❌ 危险模式
function withdraw() public {
    uint256 amount = balances[msg.sender];
    (bool success, ) = msg.sender.call{value: amount}("");
    balances[msg.sender] = 0; // 状态更新在外部调用之后
}
```

### 防护
- 使用 ReentrancyGuard
- 遵循 CEI 模式（Checks-Effects-Interactions）
- 先更新状态，再进行外部调用

## 2. 整数溢出/下溢

### 模式
```solidity
// ❌ Solidity < 0.8
uint256 total = a + b; // 可能溢出
```

### 防护
- 使用 Solidity 0.8+（内置检查）
- 或使用 SafeMath 库

## 3. 未检查返回值

### 模式
```solidity
// ❌ 危险
token.transfer(to, amount);
```

### 防护
- 使用 SafeERC20
- 检查返回值

## 4. 访问控制缺失

### 模式
```solidity
// ❌ 危险
function withdraw() public {
    // 任何人都可以调用
}
```

### 防护
- 使用 `onlyOwner` 或 `onlyRole` 修饰符
- 实现多签钱包控制
- 使用时间锁延迟关键操作

## 5. 时间戳依赖

### 模式
```solidity
// ❌ 危险：使用 block.timestamp 作为随机源
uint256 random = block.timestamp % 100;
```

### 防护
- 避免使用 block.timestamp 作为随机源
- 使用 Chainlink VRF 或其他可信随机源
- 使用 commit-reveal 方案

## 6. 前端运行 (Front-running)

### 模式
```solidity
// ❌ 危险：交易在 mempool 中可见
function buy(uint256 amount) public {
    uint256 price = calculatePrice(amount);
    // 攻击者可以抢先执行
}
```

### 防护
- 使用 commit-reveal 方案
- 设置价格限制
- 使用私有 mempool（如 Flashbots）

## 7. 委托调用风险

### 模式
```solidity
// ❌ 危险：委托调用不可信合约
delegatecall(target, data);
```

### 防护
- 仅委托调用可信合约
- 验证目标地址
- 使用库模式而非委托调用

## 8. 未初始化存储指针

### 模式
```solidity
// ❌ 危险：未初始化的存储指针
struct Data {
    uint256 value;
}
Data storage data; // 未初始化
```

### 防护
- 始终初始化存储指针
- 使用 memory 而非 storage（如果可能）
- 使用 Solidity 0.5.0+ 的检查

## 9. 函数选择器冲突

### 模式
```solidity
// ❌ 危险：函数选择器可能冲突
function transfer(address to, uint256 amount) public {}
function transfer(address to) public {} // 选择器冲突
```

### 防护
- 确保函数签名唯一
- 使用不同的参数类型
- 使用函数重载时注意选择器

## 10. 浮点 pragma

### 模式
```solidity
// ❌ 危险：浮点版本
pragma solidity ^0.8.0;
```

### 防护
- 使用固定版本：`pragma solidity 0.8.20;`
- 或使用范围：`pragma solidity >=0.8.0 <0.9.0;`

## 检测工具

- Slither: 静态分析
- Mythril: 符号执行
- Echidna: 模糊测试
- Manticore: 符号执行
- Securify: 在线分析
""", encoding="utf-8")
    
    print("✅ 更多最佳实践文件填充完成")


def populate_reports():
    """填充审计报告示例"""
    reports_dir = CORPUS_DIR / "reports"
    reports_dir.mkdir(exist_ok=True)
    
    print("📚 填充审计报告示例...")
    
    # 完整的 Vault 审计报告示例
    (reports_dir / "example_vault_audit.md").write_text("""# Vault Contract 审计报告示例

## 执行摘要

**审计目标**: Vault.sol - 资金管理合约
**审计日期**: 2024-01-01
**审计方法**: 手动代码审查 + 自动化工具扫描
**审计范围**: contracts/Vault.sol, contracts/interfaces/IVault.sol

### 总体评估
本次审计发现了 2 个严重漏洞、3 个高危漏洞、5 个中危问题和若干低危/信息性问题。

### 漏洞统计
- Critical: 2
- High: 3
- Medium: 5
- Low: 2
- Informational: 4

## 详细发现

### [C-01] 重入漏洞导致资金损失

**严重程度**: Critical

**描述**:
`withdraw()` 函数在更新余额之前进行外部调用，存在重入攻击风险。攻击者可以通过恶意合约在 `receive()` 函数中再次调用 `withdraw()`，从而多次提取资金。

**位置**:
`contracts/Vault.sol:45-52`

**代码**:
```solidity
function withdraw(uint256 amount) public {
    require(balances[msg.sender] >= amount, "Insufficient balance");
    
    (bool success, ) = msg.sender.call{value: amount}("");
    require(success, "Transfer failed");
    
    balances[msg.sender] -= amount; // 状态更新在外部调用之后
}
```

**影响**:
攻击者可以提取超过其实际余额的资金，导致合约资金损失。

**修复建议**:
```solidity
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

contract Vault is ReentrancyGuard {
    function withdraw(uint256 amount) public nonReentrant {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        
        balances[msg.sender] -= amount; // 先更新状态
        
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
    }
}
```

**参考**: SWC-107

---

### [C-02] 未授权访问导致资金提取

**严重程度**: Critical

**描述**:
`emergencyWithdraw()` 函数缺少访问控制，任何人都可以调用此函数提取合约中的所有资金。

**位置**:
`contracts/Vault.sol:60-65`

**代码**:
```solidity
function emergencyWithdraw() public {
    uint256 balance = address(this).balance;
    (bool success, ) = msg.sender.call{value: balance}("");
    require(success, "Transfer failed");
}
```

**影响**:
攻击者可以立即提取合约中的所有资金。

**修复建议**:
```solidity
import "@openzeppelin/contracts/access/Ownable.sol";

contract Vault is Ownable {
    function emergencyWithdraw() public onlyOwner {
        uint256 balance = address(this).balance;
        (bool success, ) = owner().call{value: balance}("");
        require(success, "Transfer failed");
    }
}
```

**参考**: SWC-105

---

### [H-01] 整数溢出风险

**严重程度**: High

**描述**:
在 Solidity 0.8.0 之前的版本中，`deposit()` 函数存在整数溢出风险。虽然当前代码使用 0.8.0+，但建议添加显式检查以提高可读性。

**位置**:
`contracts/Vault.sol:30-35`

**代码**:
```solidity
function deposit() public payable {
    balances[msg.sender] += msg.value; // 可能溢出（< 0.8.0）
}
```

**影响**:
在旧版本 Solidity 中可能导致整数溢出，造成资金计算错误。

**修复建议**:
确保使用 Solidity 0.8.0+，或添加显式检查：
```solidity
function deposit() public payable {
    require(balances[msg.sender] + msg.value >= balances[msg.sender], "Overflow");
    balances[msg.sender] += msg.value;
}
```

**参考**: SWC-101

---

### [H-02] 未检查外部调用返回值

**严重程度**: High

**描述**:
虽然代码检查了 `call()` 的返回值，但某些代币的 `transfer()` 函数可能不返回 bool 值，导致调用失败。

**位置**:
`contracts/Vault.sol:45-52`

**影响**:
如果与不遵循标准的代币交互，可能导致调用失败但未检测到。

**修复建议**:
使用 SafeERC20 处理代币转账：
```solidity
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

using SafeERC20 for IERC20;

function withdrawToken(IERC20 token, uint256 amount) public {
    token.safeTransfer(msg.sender, amount);
}
```

**参考**: SWC-104

---

### [H-03] 时间戳依赖

**严重程度**: High

**描述**:
`calculateReward()` 函数使用 `block.timestamp` 计算奖励，可能被矿工操纵。

**位置**:
`contracts/Vault.sol:70-75`

**代码**:
```solidity
function calculateReward(address user) public view returns (uint256) {
    uint256 timeDiff = block.timestamp - lastUpdate[user];
    return balances[user] * timeDiff / 1 days; // 依赖 block.timestamp
}
```

**影响**:
矿工可以在 ±15 秒范围内操纵时间戳，影响奖励计算。

**修复建议**:
避免使用 `block.timestamp` 进行关键计算，或使用时间范围检查：
```solidity
function calculateReward(address user) public view returns (uint256) {
    require(block.timestamp >= lastUpdate[user], "Invalid timestamp");
    uint256 timeDiff = block.timestamp - lastUpdate[user];
    // 添加最小时间限制
    if (timeDiff < 1 days) return 0;
    return balances[user] * timeDiff / 1 days;
}
```

**参考**: SWC-116

---

### [M-01] Gas 优化：未使用打包存储

**严重程度**: Medium

**描述**:
`UserInfo` 结构体未优化存储布局，浪费 Gas。

**位置**:
`contracts/Vault.sol:15-19`

**代码**:
```solidity
struct UserInfo {
    uint256 balance;    // 32 bytes
    uint128 reward;     // 16 bytes
    uint128 timestamp;  // 16 bytes
}
```

**修复建议**:
重新排列结构体以打包到单个存储槽：
```solidity
struct UserInfo {
    uint128 reward;     // 16 bytes
    uint128 timestamp;  // 16 bytes
    uint256 balance;    // 32 bytes
}
```

---

### [M-02] 缺少事件

**严重程度**: Medium

**描述**:
关键操作（deposit, withdraw）未发出事件，不利于链下监控和审计。

**修复建议**:
添加事件：
```solidity
event Deposit(address indexed user, uint256 amount);
event Withdraw(address indexed user, uint256 amount);

function deposit() public payable {
    balances[msg.sender] += msg.value;
    emit Deposit(msg.sender, msg.value);
}
```

---

### [M-03] 缺少暂停机制

**严重程度**: Medium

**描述**:
合约缺少紧急暂停机制，在发现漏洞时无法及时停止交易。

**修复建议**:
使用 OpenZeppelin 的 Pausable：
```solidity
import "@openzeppelin/contracts/security/Pausable.sol";

contract Vault is Pausable, Ownable {
    function withdraw(uint256 amount) public whenNotPaused {
        // ...
    }
    
    function pause() public onlyOwner {
        _pause();
    }
}
```

---

### [M-04] 未实现时间锁

**严重程度**: Medium

**描述**:
关键操作（如 emergencyWithdraw）缺少时间锁，无法给用户时间响应。

**修复建议**:
使用 OpenZeppelin 的 TimelockController。

---

### [M-05] 缺少最大提取限制

**严重程度**: Medium

**描述**:
单次提取没有上限，可能导致 Gas 限制问题。

**修复建议**:
添加最大提取限制：
```solidity
uint256 public constant MAX_WITHDRAW = 1000 ether;

function withdraw(uint256 amount) public {
    require(amount <= MAX_WITHDRAW, "Exceeds max withdraw");
    // ...
}
```

---

### [L-01] 代码注释不足

**严重程度**: Low

**描述**:
部分函数缺少 NatSpec 注释。

**修复建议**:
添加完整的 NatSpec 注释。

---

### [L-02] 魔法数字

**严重程度**: Low

**描述**:
代码中存在魔法数字（如 `1 days`），应定义为常量。

**修复建议**:
```solidity
uint256 public constant REWARD_PERIOD = 1 days;
```

---

## 测试覆盖

### 单元测试
- 覆盖率: 85%
- 主要功能: ✅ 已测试
- 边界条件: ⚠️ 部分测试

### 集成测试
- 基本流程: ✅ 已测试
- 重入攻击: ❌ 未测试
- 访问控制: ⚠️ 部分测试

### 模糊测试
- 未进行模糊测试

## 工具扫描结果

### Slither
- 发现 8 个问题（2 个高危，6 个中危）

### Mythril
- 发现 3 个潜在问题

### Securify
- 发现 2 个问题

## 建议

### 代码改进
1. 实现完整的访问控制
2. 添加重入保护
3. 优化 Gas 消耗
4. 添加事件和日志

### 架构优化
1. 考虑使用代理模式支持升级
2. 实现多签钱包控制
3. 添加时间锁机制

### 安全增强
1. 进行专业安全审计
2. 实施漏洞赏金计划
3. 定期安全审查
4. 建立应急响应流程

## 结论

虽然合约实现了基本功能，但存在严重的安全漏洞，**不建议在主网部署**。建议修复所有 Critical 和 High 级别的问题后，重新进行审计。

---

**审计人员**: AI Auditor
**报告版本**: 1.0
**下次审计建议**: 修复后 2 周内
""", encoding="utf-8")
    
    # 添加更多审计报告示例
    (reports_dir / "example_token_audit.md").write_text("""# ERC20 Token 审计报告示例

## 执行摘要

**审计目标**: Token.sol - ERC20 代币合约
**审计日期**: 2024-01-15
**审计方法**: 手动代码审查 + 自动化工具扫描

### 总体评估
本次审计发现了 1 个高危漏洞、3 个中危问题和若干低危问题。

### 漏洞统计
- Critical: 0
- High: 1
- Medium: 3
- Low: 2
- Informational: 3

## 详细发现

### [H-01] approve 竞态条件

**严重程度**: High

**描述**:
`approve()` 函数存在竞态条件，用户无法安全地更改授权额度。

**修复建议**:
使用 `increaseAllowance` 和 `decreaseAllowance`，或先设置为 0 再设置新值。

**参考**: SWC-114

---

### [M-01] 缺少暂停机制

**严重程度**: Medium

**描述**:
代币合约缺少紧急暂停功能。

**修复建议**:
实现 Pausable 功能。

---

## 结论

合约整体安全性较好，但建议修复高危问题后再部署。

---

**审计人员**: AI Auditor
**报告版本**: 1.0
""", encoding="utf-8")
    
    print("✅ 审计报告示例填充完成")


def main():
    """主函数：填充所有 Corpus 内容"""
    import argparse
    
    parser = argparse.ArgumentParser(description="填充 RAG Corpus 内容")
    parser.add_argument(
        "--skip-swc",
        action="store_true",
        help="跳过 SWC 文件填充"
    )
    parser.add_argument(
        "--skip-oz",
        action="store_true",
        help="跳过 OpenZeppelin 文件填充"
    )
    parser.add_argument(
        "--skip-best-practices",
        action="store_true",
        help="跳过最佳实践文件填充"
    )
    parser.add_argument(
        "--skip-reports",
        action="store_true",
        help="跳过审计报告示例填充"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制重新生成所有文件（即使已存在）"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🚀 开始填充 RAG Corpus 内容")
    print("=" * 60)
    print()
    
    try:
        if not args.skip_swc:
            populate_swc_files(force=args.force)
            print()
        
        if not args.skip_oz:
            populate_oz_files()
            populate_more_oz_files()
            print()
        
        if not args.skip_best_practices:
            populate_best_practices()
            populate_more_best_practices()
            print()
        
        if not args.skip_reports:
            populate_reports()
            print()
        
        print("=" * 60)
        print("✅ 所有 Corpus 内容填充完成！")
        print("=" * 60)
        print()
        print(f"📁 Corpus 目录: {CORPUS_DIR}")
        print(f"📊 目录结构:")
        print(f"   - swc/          : SWC 漏洞库")
        print(f"   - oz/           : OpenZeppelin 文档")
        print(f"   - best_practices/: 最佳实践")
        print(f"   - reports/      : 审计报告示例")
        print()
        print("💡 提示: 运行 'python src/rag/build_index.py' 构建索引")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
