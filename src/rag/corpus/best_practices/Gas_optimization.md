# Gas 优化 / Gas Optimization

## 存储优化

### 1. 使用打包存储
```solidity
// ❌ 浪费 Gas
struct User {
    uint256 id;        // 32 bytes
    uint128 balance;   // 16 bytes
    uint128 timestamp; // 16 bytes
}

// ✅ 优化：打包到单个存储槽
struct User {
    uint128 balance;   // 16 bytes
    uint128 timestamp; // 16 bytes
    uint256 id;        // 32 bytes
}
```

### 2. 使用事件而非存储
对于不需要链上访问的数据，使用事件而非存储变量。

### 3. 缓存存储变量
```solidity
// ❌ 多次读取存储
function update() public {
    users[msg.sender].balance += 1;
    users[msg.sender].count += 1;
    users[msg.sender].lastUpdate = block.timestamp;
}

// ✅ 优化：缓存到内存
function update() public {
    User storage user = users[msg.sender];
    user.balance += 1;
    user.count += 1;
    user.lastUpdate = block.timestamp;
}
```

## 函数优化

### 1. 使用 external 而非 public
对于不需要内部调用的函数，使用 `external` 可以节省 Gas。

### 2. 批量操作
```solidity
// ❌ 多次调用
function transferMany(address[] memory to, uint256[] memory amounts) public {
    for (uint i = 0; i < to.length; i++) {
        transfer(to[i], amounts[i]);
    }
}

// ✅ 优化：批量处理
function transferMany(address[] memory to, uint256[] memory amounts) public {
    require(to.length == amounts.length, "Length mismatch");
    for (uint i = 0; i < to.length; i++) {
        _transfer(msg.sender, to[i], amounts[i]);
    }
}
```

### 3. 短路评估
```solidity
// ✅ 使用 && 和 || 的短路特性
if (condition1 && condition2) {
    // 如果 condition1 为 false，不会评估 condition2
}
```

## 循环优化

### 1. 缓存数组长度
```solidity
// ❌ 每次循环都读取长度
for (uint i = 0; i < array.length; i++) {
    // ...
}

// ✅ 优化：缓存长度
uint length = array.length;
for (uint i = 0; i < length; i++) {
    // ...
}
```

### 2. 使用 unchecked 块
在确保不会溢出的情况下，使用 `unchecked` 块可以节省 Gas。

## 其他优化技巧

1. **使用自定义错误而非 require 字符串**
   ```solidity
   error InsufficientBalance();
   if (balance < amount) revert InsufficientBalance();
   ```

2. **使用 immutable 和 constant**
   ```solidity
   address public immutable owner;
   uint256 public constant MAX_SUPPLY = 1000000;
   ```

3. **避免不必要的零值检查**
   ```solidity
   // Solidity 0.8+ 自动检查，无需手动检查
   ```

4. **使用 assembly 进行低级优化**（仅在必要时）

## 工具
- Hardhat Gas Reporter
- Foundry Gas Snapshot
- Tenderly Gas Profiler
