# SafeERC20 / 安全 ERC20 操作

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
