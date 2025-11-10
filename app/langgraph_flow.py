from typing import Dict
from app.schemas import StubResult, ProposedAction

def run_stub_flow(ticket: Dict) -> StubResult:
    """
    Extremely small, deterministic stand-in for your agent graph.
    Replace later with real LangGraph nodes and tools.
    """
    text = (ticket.get("text") or "").lower()

    factors: list[str] = []
    if "bill" in text or "charge" in text:
        factors.append("last_bill_delta>=+10%")
    if "speed" in text or "slow" in text:
        factors.append("avg_down_mbps<10")
    if not factors:
        factors.append("recent_ticket_activity")

    # a simple, explainable score (just for demo)
    churn_score = min(0.2 + 0.2 * len(factors), 0.95)

    msg = (
        "We noticed a recent billing change and possible line/speed issues. "
        "We can review your plan and check your line. Would you like us to schedule a callback?"
    )

    return StubResult(
        ticket_id=ticket.get("ticket_id", "T-000"),
        churn_score=round(churn_score, 2),
        top_factors=factors[:3],
        proposed_action=ProposedAction(
            type="plan_review",
            reason="Billing change + speed concerns",
            customer_message=msg,
        ),
    )
