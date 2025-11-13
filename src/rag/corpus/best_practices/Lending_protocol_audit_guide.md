# 借贷协议审计指南 / Lending Protocol Audit Guide

## 1. 核心模块 Core Modules
- **抵押金库 (Vault/Pool)**：存款、取款、利息累计
- **借款逻辑 (Borrowing)**：利率模型、健康系数、清算阈值
- **清算机制 (Liquidation)**：折价、奖励、最大偿还比例
- **风险参数治理 (Risk Parameters)**：LTV、reserve factor、债务上限

## 2. 资金安全 Funds Safety
- `deposit`, `withdraw`, `borrow`, `repay` 函数遵循 CEI 模式
- 使用 SafeERC20，处理 `approve(0)` 以避免竞态
- 确认代币转账支持 fee-on-transfer、rebasing 场景
- 验证协议金库余额与会计变量（`totalDeposits`, `totalBorrows`）一致

## 3. 利率模型 Interest Rate Model
- 检查利率曲线（kink/baseSlope/optimalUtilization）与白皮书一致
- 防止 `setInterestModel` 被非授权账户调用
- 确认利率计算不会溢出 (`r * deltaTime / 1e18`)
- 模拟极端利用率（0%、100%）下的利率与利息累计

## 4. 账户健康度 Account Health
- 健康因子 `HF = collateral_value * liquidation_threshold / borrow_value`
- `liquidate` 前应重新计算健康度，避免使用缓存数据
- 检查多抵押资产组合的汇总逻辑（价格、折扣、汇率）
- 防止用户通过闪电贷在同一交易中绕过健康度检查

## 5. 清算流程 Liquidation Process
- 清算奖励（bonus）是否符合预期
- 单笔清算的最大可偿还额度 (`closeFactor`)
- 清算后更新抵押与债务余额的顺序：先减少债务再转移抵押
- 考虑抵押资产为 NFT、LP Token 等复杂资产的处理

## 6. 风险参数治理 Risk Parameter Governance
- 参数修改是否需要 timelock、多签审批
- 关键参数：`collateralFactor`, `reserveFactor`, `interestRateModel`
- 添加事件日志 `emit ParameterChanged(...)` 便于追踪
- 治理提案执行脚本需要审计（防止参数错误）

## 7. 经济性攻击 Economic Attacks
- **利率操纵**：利用闪电贷快速借入还款改变利率
- **价格操纵**：抵押资产依赖单一预言机，检查 TWAP/偏差限制
- **Bad Debt**：资产大幅贬值导致无法清算，需要风险缓冲基金
- **流动性枯竭**：大量提款导致利率飙升，考虑提款限制

## 8. 测试与模拟 Testing & Simulation
- 单元测试覆盖：
  - 存款/借款/还款/提款的正反用例
  - 极端利率、利用率
  - 清算边界条件（刚好健康度 < 1）
- 属性/模糊测试：
  - Invariant: `cash + borrows - reserves == totalDeposits`
  - Fuzz: 随机序列操作，确保无溢出、无失败
- 经济模型模拟：Gauntlet、Chaos Labs 等工具评估参数稳定性

## 9. 监控与运营 Monitoring & Ops
- 监控池子利用率、利率、坏账规模、清算事件
- 设置极端情况报警（利用率 > 95%、价格偏差 > 20%）
- 准备紧急暂停、风险参数调整流程
- 定期进行资产负债表对账与第三方审计

## 10. 参考资料 References
- Aave Protocol Whitepaper & Risk Framework
- Compound Protocol Security Review
- OpenZeppelin《DeFi Lending Best Practices》
- Gauntlet Risk Parameter Recommendations
