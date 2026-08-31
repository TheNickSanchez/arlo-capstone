"""PreToolUse PEP placeholder (SAD AD-9). Implement in @backend.eng.

Deny any state-changing tool if phase ≠ Executing or tool ∉ frozen approved list.
Do not trust model-stated phase. Audit policy_deny=true on deny.
"""
