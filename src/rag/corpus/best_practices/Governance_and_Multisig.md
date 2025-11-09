# 治理与多签 / Governance and Multisig

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
