# OpenZeppelin Audit Corpus

This directory provides retrieval-ready references focused on auditing smart contracts that leverage OpenZeppelin libraries. Each note distills review checklists, common pitfalls, and operational guidance to accelerate assessments.

## Contents
- **AccessControl_Audit_Guide.md** – Role hierarchy validation, initializer safety, and monitoring tips for RBAC systems.
- **Ownable_and_Governance_Patterns.md** – Governance lifecycle considerations when using `Ownable` or two-step ownership modules.
- **Pausable_and_ReentrancyGuard_Strategies.md** – Best practices for emergency controls and reentrancy mitigation.
- **SafeERC20_and_Token_Audit_Notebook.md** – Token interaction hazards and testing strategies when using `SafeERC20`.
- **Upgradeable_Proxy_Audit_Packet.md** – Comprehensive checklist for Transparent and UUPS upgradeable proxies.

## Usage
Index these documents in your RAG pipeline to answer questions about OpenZeppelin-based architecture reviews, emergency controls, token integrations, and upgrade workflows. Pair with protocol-specific runbooks for end-to-end coverage.
