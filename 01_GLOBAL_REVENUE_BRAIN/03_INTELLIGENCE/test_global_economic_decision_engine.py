from global_economic_decision_engine import evaluate


def candidate(**updates: str) -> dict[str, str]:
    row = {
        "title": "Paid issue", "url": "https://github.com/example/repo/issues/1",
        "category": "open_source_bounty",
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


def test_unproven_bug_bounty_does_not_request_approval_or_dominate_queue() -> None:
    result = evaluate(candidate(
        category="authorized_bug_bounty",
        truth_status="AUTHORIZED_BUG_BOUNTY_REVIEW_REQUIRED",
        url="https://immunefi.com/bug-bounty/example/information/",
        payment_method="USDC",
        reward_basis="maximum_advertised_reward",
        reward_amount="500000",
        estimated_hours="80",
        comments="0",
    ))
    assert result["decision_route"] == "EVIDENCE_REFRESH_REQUIRED"
    assert result["automation_eligible"] == "false"
    assert result["external_action_allowed"] == "false"
    assert float(result["estimated_payment_probability"]) <= 0.001
    assert "pesquisa passiva" in result["decision_next_action"]


if __name__ == "__main__":
    test_ready_zero_competition_is_technical_execution()
    test_high_competition_is_archived()
    test_review_is_never_sent_to_executor()
    test_unproven_bug_bounty_does_not_request_approval_or_dominate_queue()
    print("global economic decision tests: ok")
