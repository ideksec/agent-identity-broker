import ulid


def new_id(prefix: str) -> str:
    return f"{prefix}_{ulid.new().str}"


def lease_id() -> str:
    return new_id("lease")


def decision_id() -> str:
    return new_id("dec")


def event_id() -> str:
    return new_id("evt")


def session_id() -> str:
    return new_id("sess")


def managed_credential_id() -> str:
    return new_id("mc")
