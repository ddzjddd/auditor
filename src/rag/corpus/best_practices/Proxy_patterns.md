# 代理模式 / Proxy Patterns

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
