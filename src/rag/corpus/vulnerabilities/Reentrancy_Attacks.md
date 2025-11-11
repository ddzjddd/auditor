# Reentrancy Attacks

## Why they matter
Reentrancy occurs when a contract makes an external call before finishing its own state changes. A malicious callee can reenter the vulnerable function, repeating sensitive operations like withdrawals, burns, or governance votes, leading to fund drains and invariant violations.

## Common weakness patterns
- **State updates after external calls**: Balance bookkeeping or flag updates happen after token transfers or low-level calls.
- **Reentrant callbacks in ERC standards**: `ERC777` hooks, `ERC1155Receiver` callbacks, and token fallbacks executing before the sending contract finalizes state.
- **Cross-function reentrancy**: One public function sets up state that another reentrant entry point can exploit.
- **Reentrancy through proxies**: Upgradable proxies forward calls back into implementation logic before completion.
- **Withdrawal loops**: Iterating through user accounts with external transfers inside the loop allows early accounts to reenter and drain the pool.

## Detection checklist
- Identify every external call (`call`, `transfer`, `send`, token `transfer`/`transferFrom`, `safeTransferFrom`) and confirm the contract updates critical state before invoking them.
- Validate `ReentrancyGuard` usage: ensure modifiers wrap every sensitive function and are not bypassed in internal calls.
- Analyze pull payment patterns to ensure withdrawals use user-initiated `withdraw` calls rather than automatic payouts.
- Inspect hooks and fallback functions that can trigger during token transfers; confirm they cannot reenter without limits.
- Test with fuzzers or Foundry scripts that perform nested calls to confirm the contract rejects reentrant attempts.

## Mitigation strategies
- Follow the Checks-Effects-Interactions pattern: update balances and emit events before making external calls.
- Employ `ReentrancyGuard` or mutex-like state variables with careful coverage of all entry points.
- Prefer pull over push payments and throttle withdrawal sizes or frequency to cap potential losses.
- Use reentrancy-safe token wrappers (e.g., `nonReentrant` modifiers on bridge/escrow contracts).
- Add unit and invariant tests simulating reentrant adversaries, including cross-contract recursion chains.
