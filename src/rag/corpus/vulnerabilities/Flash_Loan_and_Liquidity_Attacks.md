# Flash Loan and Liquidity Attacks

## Why they matter
Flash loans enable attackers to borrow large capital without collateral and return it within a single transaction. When combined with liquidity manipulation, they can break assumptions about market depth, collateralization, or invariant maintenance in AMMs and lending protocols.

## Common weakness patterns
- **Unbounded price impact**: Protocol logic assumes deep liquidity and does not guard against drastic per-block price swings.
- **Atomic arbitrage paths**: Interdependent protocols whose operations can be chained in one transaction without intermediate checks.
- **Temporal dependency**: Contracts rely on end-of-block balances or supply-demand snapshots that a flash loan can manipulate.
- **Low reserve buffers**: Vaults that allow instant withdrawals without checking post-withdraw liquidity ratios.
- **Composable governance**: Flash-loan funded voting or staking to pass malicious proposals or drain rewards.

## Detection checklist
- Review critical operations for assumptions about pool reserves, collateral ratios, or token balances that are not revalidated after external calls.
- Evaluate whether functions like `rebalance`, `liquidate`, or `swap` can be invoked repeatedly within one block to exploit intermediate states.
- Simulate flash-loan sequences using tools like Foundry or Tenderly to test whether invariants (`k=x*y`, collateralization) hold.
- Check governance vote weight snapshots and ensure they occur at block boundaries that cannot be manipulated by flash loans.
- Verify that withdrawal and redemption logic enforces cooldowns or rate limits to prevent instant draining after price manipulation.

## Mitigation strategies
- Add price change bounds and slippage checks that compare against time-weighted oracles before executing large operations.
- Use circuit breakers that pause sensitive functions when reserves drop below thresholds or utilization spikes abruptly.
- Introduce minimum liquidity buffers and enforce delayed withdrawals or two-transaction commit/redeem flows.
- Snapshot voting power at proposal creation rather than at execution; require staking lockups for governance participants.
- Monitor on-chain analytics for abnormal flash-loan volumes targeting protocol contracts and respond with emergency procedures.
