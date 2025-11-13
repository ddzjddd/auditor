# SafeERC20 & Token Audit Notebook

## Purpose
`SafeERC20` wraps ERC-20 token interactions to normalize return values and bubble up reverts. Protocols often rely on this helper for custody, fee collection, and liquidity flows. Audits should confirm tokens integrated with the protocol are compatible with the assumptions encoded in `SafeERC20`.

## Checklist
1. **Token Compliance**
   - Validate upstream tokens follow ERC-20 return semantics; identify non-standard tokens requiring custom wrappers.
   - Confirm allowance handling uses `safeIncreaseAllowance`/`safeDecreaseAllowance` to avoid race conditions.
2. **Address Interaction**
   - Ensure `safeTransfer`/`safeTransferFrom` calls are guarded against reentrancy when tokens invoke callbacks.
   - Review low-level calls for potential gas griefing or malicious token behavior.
3. **Permit Extensions**
   - When using `IERC20Permit`, verify signature domain separation and replay protection.
   - Confirm deadline checks prevent signature reuse after expiration.
4. **Accounting Invariants**
   - Track token balances before/after each transfer; ensure reentrancy guards are present when balances update.
   - Validate zero-address checks exist where tokens are minted/burned.

## Integration Tests
- Mock adversarial ERC-20 tokens that return `false` or consume all gas to confirm wrappers revert cleanly.
- Simulate approval front-running scenarios.
- Execute fuzz tests varying `amount`, `from`, `to`, and allowance states.

## Observability
- Monitor token balance deltas per transaction and reconcile with accounting modules.
- Alert when allowances exceed predefined thresholds.
- Maintain runbooks for revoking allowances on compromised addresses.
