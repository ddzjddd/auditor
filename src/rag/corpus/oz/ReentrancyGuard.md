# ReentrancyGuard / 重入保护

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
