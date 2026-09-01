"""AuthN primitives (SAD §8): password hashing + signed session tokens.

Stdlib-only (`hashlib`/`hmac`) so no additional third-party auth dependency is
required beyond what `setup.md` already installed. No secret values are ever
written to artifacts or logs (AAMAD core rule).
"""
