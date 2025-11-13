# Pausable & ReentrancyGuard Audit Strategies

## Module Synopsis
OpenZeppelin's `Pausable` and `ReentrancyGuard` modules provide defensive mechanisms against runtime emergencies and recursive call attacks. Auditors should validate that these controls are implemented consistently and integrated with protocol-specific state machines.

## Pausable Review
- **Pause authority**: Identify who can call `_pause`/`_unpause`; ensure controls align with governance requirements.
- **Granularity**: Confirm that only critical state transitions are gated; consider partial pausing for specific functions.
- **State transitions**: Check modifiers (`whenNotPaused`, `whenPaused`) cover all relevant external entry points.
- **Recovery playbooks**: Review unpause procedures, including staged testing before resuming production operations.

## ReentrancyGuard Review
- **Modifier coverage**: Ensure `nonReentrant` guards protect functions updating balances, collateral, or other sensitive state.
- **Cross-function interactions**: Be aware that `nonReentrant` prevents nested calls within the same contract; verify helper functions are `private` or reentrancy-safe.
- **Upgradeable pattern**: For proxies, confirm storage slots remain consistent and guard initializer called once.
- **Multi-token flows**: Examine interactions with ERC-777 hooks, callbacks, or cross-contract calls susceptible to reentrancy.

## Attack Scenarios
- Paused system cannot recover due to missing unpause permissions.
- Partial pause missing certain function variants (e.g., meta-transaction entry points).
- `nonReentrant` omitted on helper function invoked by multiple external entry points.
- Upgraded contract forgets to inherit `ReentrancyGuardUpgradeable`, removing protection.

## Testing Plan
- Unit tests toggling pause state and ensuring only authorized actors succeed.
- Fuzz tests for reentrant token hooks verifying reverts occur before state corruption.
- Integration tests simulating pause/unpause around governance delays and timelocks.

## Monitoring & Operations
- Emit structured events on pause/unpause with reason codes.
- Track pause duration metrics and alert on prolonged downtime.
- Review guard coverage quarterly as new features are added.
