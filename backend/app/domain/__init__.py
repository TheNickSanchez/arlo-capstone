"""Domain logic shared by the FastAPI service and the Temporal worker (SAD §2, §4).

Pure Python only: no SQLAlchemy sessions, no Temporal client, no Claude SDK. This
keeps hashing, status-machine, and action-catalog rules independently unit
testable and importable from both `backend.app` and `worker` without pulling in
I/O dependencies.
"""
