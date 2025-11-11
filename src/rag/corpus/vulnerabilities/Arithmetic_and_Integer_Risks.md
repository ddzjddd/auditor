# Arithmetic and Integer Risks

## Why they matter
Smart contracts rely on fixed-size integers. Overflow, underflow, and precision loss can invalidate accounting assumptions, leak funds, or break governance mechanisms. While Solidity 0.8+ reverts on overflow by default, many protocols interact with legacy contracts, inline assembly, or libraries that still permit unchecked math.

## Common weakness patterns
- **Unchecked arithmetic**: Use of `unchecked {}` blocks, `SafeMath` omissions, or inline assembly that bypasses compiler checks.
- **Precision truncation**: Division before multiplication, integer division of ratios, or mixing decimals between tokens (e.g., 6 vs 18 decimals).
- **Rounding-induced privilege**: Calculations that determine voting power or collateralization thresholds can be manipulated via rounding direction.
- **Cumulative drift**: Interest accrual and rebasing math that truncates residual dust each block can create long-term imbalances.
- **Signed vs unsigned confusion**: Converting negative ints to uints or vice versa without validation causes wrap-around exploits.

## Detection checklist
- Search for `unchecked`, assembly blocks, or custom math libraries and confirm every operation has explicit range reasoning.
- Review token decimal assumptions; ensure scaling factors (`1e18`) are consistently applied before division.
- Evaluate multi-step formulas for reordering opportunities that preserve precision (multiply before divide when safe).
- Fuzz financial formulas with extreme values (max/min collateral, fees) to detect rounding that breaks invariants.
- Confirm casting between `int` and `uint` is guarded by explicit bounds checks.

## Mitigation strategies
- Default to OpenZeppelin `SafeCast` and `Math` utilities for overflow-aware operations.
- Document expected input ranges in NatSpec and enforce them with `require` statements.
- Normalize token amounts to a common precision using wad/ray math helpers before calculations.
- Introduce invariant tests (e.g., Echidna, Foundry) to continuously validate that math routines respect balance conservation.
- Avoid storing intermediate fractional values on-chain when off-chain computation or oracles can supply pre-scaled numbers.
