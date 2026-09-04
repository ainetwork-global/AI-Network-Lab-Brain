from autonomy_risk_policy import assess


def test_verified_internal_work_is_green():
    decision = assess({"title": "Implement parser", "eligibility_status": "confirmed eligible"})
    assert decision.level == "GREEN"
    assert decision.decision == "AUTONOMOUS_INTERNAL_EXECUTION"


def test_public_submission_requires_approval():
    decision = assess({"requirements": "Submit a pull request"}, action="external_submission")
    assert decision.level == "YELLOW"
    assert decision.decision == "HUMAN_APPROVAL_REQUIRED"


def test_submission_text_does_not_block_internal_development():
    decision = assess({"requirements": "Submit a pull request", "eligibility_status": "confirmed eligible"})
    assert decision.decision == "AUTONOMOUS_INTERNAL_EXECUTION"


def test_upfront_payment_is_red():
    decision = assess({"requirements": "Registration fee of USD 5"})
    assert decision.level == "RED"
    assert decision.decision == "HUMAN_APPROVAL_REQUIRED"


def test_fake_account_is_always_rejected():
    decision = assess({"requirements": "Create a fake account"})
    assert decision.level == "PROHIBITED"
    assert decision.decision == "REJECT"


def test_unknown_material_fact_requires_approval():
    decision = assess({"payment_status": "not confirmed"})
    assert decision.decision == "HUMAN_APPROVAL_REQUIRED"
