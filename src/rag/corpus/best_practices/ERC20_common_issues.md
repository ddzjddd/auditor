# ERC20 常见问题 / Common Issues

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
