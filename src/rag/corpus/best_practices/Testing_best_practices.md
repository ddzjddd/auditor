# 测试最佳实践 / Testing Best Practices

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
