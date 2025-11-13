# 预言机与价格源安全 / Oracle & Price Feed Security

## 1. 预言机模型分类 Oracle Models
- **去中心化喂价 (e.g., Chainlink)**：多节点聚合、轮询更新、心跳间隔
- **去中心化交易所 TWAP**：使用 Uniswap/SushiSwap 等 DEX 平均价
- **自定义聚合器**：项目方运行的 off-chain 服务推送价格
- **混合模型**：综合多数据源（CEX + DEX + Off-chain）

## 2. 审计关注点 Audit Focus Areas
### 2.1 数据来源与聚合
- 是否使用中位数/均值/加权平均处理单个数据源异常
- 聚合过程中是否存在浮点精度问题（`mulDiv`、`1e18` 标准化）
- 检查数据源白名单的可配置性与访问控制

### 2.2 更新频率与心跳
- `latestRoundData` 等接口的 `updatedAt` 是否过期
- 支持 keeper / cron job 调度的最小更新间隔、最大延迟
- 对延迟数据的处理（fallback 机制）

### 2.3 故障切换与后备方案
- 主预言机失败时是否启用后备（Fallback Oracle）
- 后备切换条件：价格偏差阈值、最大无更新区间
- 切换逻辑需具备访问控制，防止任意账户切换到恶意价格

### 2.4 访问控制与权限管理
- 喂价合约是否限制 `setOracle`, `setFeed` 等函数
- 使用 `onlyOwner`/`onlyRole`/多签控制关键参数
- 记录角色操作事件以便追溯

### 2.5 消费者合约的健壮性
- 验证返回值、捕获 `stale price` 和 `zero price`
- 在借贷协议中设置 `maxPriceDeviation`, `maxPriceAge`
- 对外部 `call` 的 `try/catch` 处理，避免预言机失败导致 DoS

## 3. 常见漏洞案例 Common Vulnerabilities
1. **闪电贷价格操纵**：使用池内瞬时价格作为抵押品估值
   - ✅ 使用时间加权平均价（TWAP）或多区块平均
   - ✅ 结合链下参考价做偏差检测
2. **心跳停更**：喂价节点长时间未更新，导致抵押参数过时
   - ✅ 设置最大允许延迟 `require(block.timestamp - updatedAt < maxDelay)`
   - ✅ 引入 Keeper 监控失败报警
3. **权限泄露**：单个 EOA 可以替换预言机地址
   - ✅ 多签治理 + timelock
   - ✅ 事件记录与离线审计
4. **浮点精度错误**：喂价数据 `8 decimals` 与协议 `18 decimals` 未对齐
   - ✅ 统一使用 `FixedPointMathLib` 或自定义 `mulDiv` 函数
   - ✅ 添加单元测试覆盖极值场景

## 4. 安全测试建议 Testing Recommendations
- 模拟价格快速波动、停更、极端偏差
- Fuzz 测试 `setPrice`, `updateAnswer` 与消费方关键函数
- 单元测试覆盖：
  - 价格来源异常返回
  - `stale` 数据处理
  - TWAP 缓冲区长度（`observationCardinality`）
- 集成测试：结合 Keeper / Automation 脚本验证长时间运行稳定性

## 5. 监控指标 Monitoring Metrics
- 最近更新区块与时间戳
- 价格偏差（相对主市场或参考价格）
- 数据源状态：响应时间、失败率
- Keeper/Relayer 状态：运行进程、最近心跳

## 6. 参考资料 References
- Chainlink Documentation: Data Feeds Security
- Uniswap v3 TWAP Oracle 设计文档
- MakerDAO Oracle Security Module (OSM)
- Trail of Bits《预言机安全最佳实践》
