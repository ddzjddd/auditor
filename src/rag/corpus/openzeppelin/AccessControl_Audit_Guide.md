# OpenZeppelin AccessControl Audit Guide

## Contract Summary
OpenZeppelin's `AccessControl` module introduces role-based access management using `bytes32` identifiers. Roles can grant/revoke other roles according to administrative relationships, enabling fine-grained permissioning beyond the simple owner model.

## Key Entry Points
- `grantRole(bytes32 role, address account)`
- `revokeRole(bytes32 role, address account)`
- `renounceRole(bytes32 role, address caller)`
- Custom functions guarded with `onlyRole` modifiers

## Invariant Checklist
1. **Role admin graph**
   - Verify every role has an explicitly defined admin role; ensure `DEFAULT_ADMIN_ROLE` usage is intentional.
   - Confirm admin roles cannot be renounced accidentally, leaving privileged functions inaccessible.
2. **Initialization flow**
   - For upgradeable deployments, ensure `__AccessControl_init` or equivalent initializer is invoked exactly once.
   - Check constructors/initializers grant roles to appropriate governance accounts.
3. **Revocation safety**
   - Ensure emergency revocation flows cannot DoS critical maintenance functions.
   - Confirm off-chain automation handles event-based updates (`RoleGranted`, `RoleRevoked`).
4. **Cross-contract authorization**
   - Validate roles assigned to contract addresses map to trusted code paths.
   - For multi-chain setups, ensure relayer / bridge contracts cannot escalate privileges via replay.

## Common Vulnerabilities
- **Orphaned admin role**: All admin addresses renounce or are revoked, preventing future role changes.
- **Unprotected role grant**: Custom helper functions that wrap `grantRole` but lack `onlyRole` checks.
- **Ambiguous DEFAULT_ADMIN_ROLE**: Single hot wallet retains admin powers leading to key compromise risk.
- **Upgradeable gap mis-use**: Forgetting `_setupRole` in initializer, leaving roles unset on proxies.

## Recommended Tests
- Unit tests covering grant/revoke/renounce flows for each role.
- Fuzz tests ensuring modifiers gate access for arbitrary addresses.
- Simulation of compromised admin revoking/renouncing roles to verify governance recovery.
- Event emission assertions to ensure monitoring pipelines can detect changes.

## Monitoring & Operations
- Subscribe to `RoleGranted`/`RoleRevoked` events with threshold alerts for unexpected accounts.
- Document role hierarchy diagrams in runbooks; review quarterly.
- Maintain multi-sig or timelock for admin roles to enforce separation of duties.
