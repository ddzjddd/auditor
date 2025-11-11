# Access Control Vulnerabilities

## Why they matter
Improper authorization logic allows adversaries to obtain privileged capabilities such as minting tokens, pausing protocols, or draining treasuries. Access control bugs often arise from implicit trust in externally owned accounts (EOAs) or misconfigured roles in libraries like OpenZeppelin `Ownable`, `AccessControl`, and `RBAC` frameworks.

## Common weakness patterns
- **Missing modifiers or role checks**: Functions intended for admins lack `onlyOwner`, `onlyRole`, or equivalent guard logic.
- **Role overlap and privilege escalation**: Granting multiple roles to a single address or assigning the default admin to a hot wallet can lead to compromised keys granting full control.
- **Improper revocation and rotation**: Failure to revoke roles after migrations or emergencies keeps dormant privileges exploitable.
- **Delegatecall exposure**: Contracts that delegatecall untrusted targets without verifying caller permissions inherit remote state changes and authorization.
- **Assumed msg.sender**: Meta-transactions or proxy patterns change who is seen as the caller, bypassing naive `msg.sender` checks.

## Detection checklist
- Review every external and public entry point to ensure an explicit access modifier is present.
- Inspect constructor, initializer, and upgrade scripts to confirm admin roles are assigned to governance-controlled contracts, not EOAs.
- Trace any `grantRole`, `revokeRole`, or `setPendingAdmin` flows to ensure only authorized actors can change privilege assignments.
- Simulate delegatecall targets and upgrade beacon implementations to verify they enforce their own authorization.
- Monitor emitted `RoleGranted` and `RoleRevoked` events to confirm at-runtime role state matches expectations.

## Mitigation strategies
- Employ multi-sig or timelock-controlled admin roles with on-chain governance when possible.
- Favor restrictive `AccessControl` hierarchies where each role has a narrow permission set and its own admin role.
- Use explicit allowlists for high-impact functions like treasury transfers and parameter updates.
- Integrate automated testing (e.g., Forge, Hardhat) that fuzzes for unauthorized function access.
- Document emergency procedures for role rotation and keep runbooks updated after each deployment.
