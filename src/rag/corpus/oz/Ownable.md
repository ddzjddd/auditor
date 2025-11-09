# Ownable / 所有权模式

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
