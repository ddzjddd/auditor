# Pausable / 暂停机制

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
