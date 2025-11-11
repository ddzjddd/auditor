# Oracle and Price Manipulation

## Why they matter
DeFi protocols depend on external data sources for asset pricing, governance decisions, and collateral health. Manipulating oracle inputs or abusing stale data allows adversaries to mint undercollateralized loans, liquidate honest users, or drain pools.

## Common weakness patterns
- **Single-source oracles**: Relying on one DEX pair or centralized API without fallback mechanisms.
- **Low-liquidity price feeds**: Thin liquidity pools are easy to swing with flash loans, especially during TWAP windows.
- **Stale data**: Oracles that update on-demand allow attackers to trade using outdated prices before an honest update occurs.
- **Improper scaling/decimals**: Misinterpreting oracle decimals leads to systematic mispricing.
- **Lack of circuit breakers**: Protocols that accept any oracle result without sanity checks cannot detect extreme deviations.

## Detection checklist
- Trace all code paths that read from `AggregatorV3Interface`, Uniswap, Chainlink, or custom oracle contracts and verify fallback logic exists.
- Analyze TWAP configuration: window length, observation frequency, and minimal liquidity requirements.
- Review price updates for access control to ensure only trusted reporters can push data.
- Simulate flash-loan price manipulation by executing large swaps and checking liquidation thresholds.
- Confirm sanity bounds (e.g., min/max price change per block) and heartbeat intervals are enforced before using oracle data.

## Mitigation strategies
- Use robust oracle frameworks (Chainlink OCR, Uniswap v3 TWAP) with sufficiently long averaging windows and anchored prices.
- Implement dual-oracle systems where deviations between feeds trigger pauses or require governance review.
- Require or incentivize frequent updates by restricting operations when data is stale beyond a heartbeat threshold.
- Add rate-limiters and circuit breakers for collateral or exchange-rate dependent functions.
- Monitor on-chain liquidity and oracle deviation metrics; alert when liquidity falls below safe thresholds.
