from fastapi import FastAPI

from .order_handoff import (
    AutomationRequest,
    AutomationResult,
    run_marketplace_automation,
)

service = FastAPI(title="Marketplace handoff automation")


@service.post("/orders/automate", response_model=AutomationResult)
def automate_order(request: AutomationRequest) -> AutomationResult:
    return run_marketplace_automation(request)

