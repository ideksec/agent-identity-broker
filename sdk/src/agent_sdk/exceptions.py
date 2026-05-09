class BrokerError(Exception):
    """Base for broker SDK errors."""


class InvalidSVID(BrokerError):
    """Raised when the broker rejects the agent's JWT-SVID."""


class PolicyDenied(BrokerError):
    """Raised when policy denies the request."""

    def __init__(self, body: dict):
        self.body = body or {}
        self.reason = self.body.get("reason", "policy denied")
        self.policy_id = self.body.get("policy_id")
        self.decision_id = self.body.get("decision_id")
        super().__init__(self.reason)


class UnknownTarget(BrokerError):
    pass
