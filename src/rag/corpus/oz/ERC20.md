# ERC20 / 代币标准

## 概述
ERC20 是以太坊上最常用的代币标准，定义了可互换代币的基本接口。

## 核心函数
- `totalSupply()`: 返回代币总供应量
- `balanceOf(account)`: 返回账户余额
- `transfer(to, amount)`: 转账代币
- `transferFrom(from, to, amount)`: 从指定地址转账
- `approve(spender, amount)`: 授权支出额度
- `allowance(owner, spender)`: 查询授权额度

## 使用示例
```solidity
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract MyToken is ERC20 {
    constructor() ERC20("MyToken", "MTK") {
        _mint(msg.sender, 1000000 * 10**decimals());
    }
}
```

## 最佳实践
1. 使用 OpenZeppelin 的标准实现
2. 注意 `approve` 的竞态条件问题
3. 使用 SafeERC20 处理非标准代币
4. 实现适当的访问控制

## 常见错误
- 忘记实现 `decimals()` 函数
- `approve` 竞态条件
- 未检查返回值（某些代币如 USDT）
- 精度计算错误

## 安全注意事项
- 防止整数溢出（Solidity 0.8+ 已内置）
- 实现适当的访问控制
- 考虑添加暂停机制
- 防止重入攻击
