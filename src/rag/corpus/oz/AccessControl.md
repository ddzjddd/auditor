# AccessControl / 角色控制

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
