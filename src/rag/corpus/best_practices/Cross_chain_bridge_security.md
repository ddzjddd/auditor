# 跨链桥安全审计要点 / Cross-Chain Bridge Security Checklist

## 1. 架构理解 Architecture Overview
- 绘制资产流向：锁定链（Lock Chain）、铸造链（Mint Chain）、中继层（Relayer / Oracle）
- 确认桥模型：锁定与铸造、燃烧与释放、轻客户端验证、原生消息桥等
- 识别信任边界：多签节点、预言机、中继器、验证人集合（Validator Set）

## 2. 状态同步与验证 State Synchronization & Verification
- 检查跨链消息验证机制（Merkle proof、轻客户端、SNARK/STARK）
- 验证存储的根或检查点是否可篡改
- 关注链下签名聚合流程：
  - 是否要求最小签名数（threshold）
  - 签名是否绑定链 ID、nonce、防止重放
- 如为轻客户端方案，确认区块头验证逻辑覆盖难题：
  - 权威签名、BLS 聚合、质押削减
  - 重组（re-org）和终局性等待时间配置

## 3. 资产托管与金库管理 Custody & Vault Management
- 锁仓合约是否允许任意资产或仅允许白名单资产
- 检查资产释放函数是否具备：
  - 权限控制（多签/DAO）
  - 额度限制（daily cap / tx cap）
  - 非重复使用的 nonce（防止重复释放）
- 验证燃烧与铸造流程中的资产供应一致性
- 评估紧急开关 / 暂停逻辑（pause/emergency withdraw）

## 4. 消息执行与可升级性 Message Execution & Upgradability
- CEI 模式：跨链消息执行后再转账，避免重入
- 对外部调用使用 `try/catch` 或受控调用模块
- 升级机制：
  - 逻辑合约是否可由单个 EOA 更换
  - 升级延迟、治理流程、多签阈值
- 检查执行模块是否允许任意调用 `call`/`delegatecall`

## 5. 常见攻击面 Common Attack Surfaces
- **签名伪造**：ECDSA/ECDSA-Threshold 验证是否严格（链 ID、域分隔）
- **价格操纵**：桥上铸造资产的估值依赖喂价是否可靠
- **速率限制绕过**：频繁小额交易绕过单笔限额
- **中继人串谋**：检查是否有质押惩罚、信誉机制
- **消息重放**：跨链消息哈希是否唯一绑定 source chain + nonce + payload
- **重入/回调**：跨链执行后调用同一桥合约导致重复释放
- **外部依赖**：第三方预言机、Keeper、链下服务的可用性

## 6. 审计清单 Audit Checklist
1. ✅ 确认跨链消息的来源验证逻辑与事件捕获一致
2. ✅ 核对 event 与 payload 编码解码流程，防止 `abi.decode` 错误
3. ✅ 检查链下签名聚合流程的防重放机制
4. ✅ 对金库余额、totalSupply、各链锁仓/铸造状态做镜像对账脚本
5. ✅ 关注 `require(msg.sender == address(this))` 等逻辑是否可被绕过
6. ✅ 验证暂停和紧急退出逻辑不会造成资产永久锁死
7. ✅ 模拟跨链消息乱序、延迟、重复传输的执行结果

## 7. 监控与应急 Monitoring & Incident Response
- 实时跟踪跨链交易延迟、失败率、资产余额差异
- 部署链下守护进程对异常事件（过量铸造、大额提款）报警
- 准备多签/治理提案模板以快速暂停桥或调整阈值
- 演练灾难恢复：受信任密钥泄露、单链停机、链上攻击

## 8. 参考资料 References
- Chainlink CCIP 安全白皮书
- L2 跨链桥安全建议（L2Beat Security Mindset）
- Trail of Bits《跨链桥安全审计手册》
- Ethereum.org Bridge Security Best Practices
