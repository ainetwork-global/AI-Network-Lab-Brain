from global_economic_decision_engine import evaluate


def candidate(**updates: str) -> dict[str, str]:
    row = {
        "title": "Paid issue", "url": "https://github.com/example/repo/issues/1",
        "truth_status": "READY_FOR_TECHNICAL_REVIEW", "payment_method": "Algora",
        "source_validation": "official_adapter", "reward_basis": "fixed_bounty",
        "reward_amount": "100", "reward_currency": "USD", "estimated_hours": "5",
        "comments": "2", "open_competing_prs": "0",
    }
    row.update(updates)
    return row


def test_ready_zero_competition_is_technical_execution() -> None:
    result = evaluate(candidate())
    assert result["decision_route"] == "AUTONOMOUS_TECHNICAL_EXECUTION"
    assert result["automation_eligible"] == "true"
    assert result["external_action_allowed"] == "false"


def test_high_competition_is_archived() -> None:
    result = evaluate(candidate(truth_status="BLOCKED_HIGH_COMPETITION", comments="59", open_competing_prs="28"))
    assert result["decision_route"] == "ARCHIVE_BLOCKED"
    assert result["estimated_payment_probability"] == "0.0000"


def test_review_is_never_sent_to_executor() -> None:
    result = evaluate(candidate(truth_status="PAYMENT_EVIDENCE_REVIEW_REQUIRED", payment_method=""))
    assert result["decision_route"] == "HUMAN_DECISION_REQUIRED"
    assert result["automation_eligible"] == "false"


if __name__ == "__main__":
    test_ready_zero_competition_is_technical_execution()
    test_high_competition_is_archived()
    test_review_is_never_sent_to_executor()
    print("global economic decision tests: ok")
