"""Activity `execute_approved` (SAD §2). Implement in @backend.eng.

New ClaudeSDKClient; allowed_tools = frozen approved write list ∩ PRD §3.4 writes.
PreToolUse PEP deny off-list tools. Idempotent retries.
"""
