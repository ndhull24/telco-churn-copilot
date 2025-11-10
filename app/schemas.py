from pydantic import BaseModel, Field

class Ticket(BaseModel):
    ticket_id: str = Field(..., examples=["T-123"])
    customer_id: str = Field(..., examples=["C-9"])
    text: str = Field(..., min_length=3, examples=["my bill went up and speed is slow"])

class ProposedAction(BaseModel):
    type: str
    reason: str
    customer_message: str

class StubResult(BaseModel):
    ticket_id: str
    churn_score: float
    top_factors: list[str]
    proposed_action: ProposedAction
