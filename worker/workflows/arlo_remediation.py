"""ArloRemediationWorkflow — Temporal Workflow (SAD §2).

Deterministic control flow only. No LLM, MCP, or DB drivers.

Lifecycle: investigate → generate_proposal → wait_condition(Signal approval_decision)
→ execute_approved (approve only) → validate_and_close.

Implement in @backend.eng. Do not register auto-approve timers (PRD: no auto-approve).
"""
