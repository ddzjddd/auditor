# UUPSUpgradeable / 升级代理模式

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
