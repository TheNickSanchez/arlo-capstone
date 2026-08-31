"""Temporal Worker entrypoint. Implement in @backend.eng (*develop-be).

Register ArloRemediationWorkflow + activities on task queue `arlo-activities`.
Must run with AAMAD_TARGET_RUNTIME=claude-agent-sdk (compose and scripts pin this).
"""


def main() -> None:
    raise NotImplementedError(
        "Temporal worker not implemented. See project-context/2.build/backend.md."
    )


if __name__ == "__main__":
    main()
