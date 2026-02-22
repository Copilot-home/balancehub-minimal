"""Legacy placeholder adapter.

BalanceHub v2 prototype is Stripe-first; HuggingFace path is intentionally
kept as a no-op scaffold for future connector onboarding.
"""


def execute_huggingface(_state):
    raise NotImplementedError("HuggingFace adapter is not enabled in Stripe-first prototype")
