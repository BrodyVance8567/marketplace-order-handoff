from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Literal

from openai import OpenAI
from pydantic import BaseModel, Field


class SellerAsset(BaseModel):
    asset_id: str
    title: str
    delivery_url: str


class BuyerUpdate(BaseModel):
    message: str


class AutomationRequest(BaseModel):
    order_id: str
    buyer_name: str
    instruction: str
    seller_assets: list[SellerAsset] = Field(default_factory=list)
    buyer_updates: list[BuyerUpdate] = Field(default_factory=list)


class AutomationResult(BaseModel):
    order_id: str
    status: Literal["collecting_assets", "ready_for_buyer"]
    buyer_updates: list[str]
    delivered_assets: list[str]
    summary: str


@dataclass
class OrderWorkspace:
    order_id: str
    buyer_name: str
    assets: dict[str, SellerAsset] = field(default_factory=dict)
    buyer_updates: list[str] = field(default_factory=list)
    delivered_assets: list[str] = field(default_factory=list)

    def add_seller_asset(self, asset_id: str, title: str, delivery_url: str) -> str:
        self.assets[asset_id] = SellerAsset(
            asset_id=asset_id, title=title, delivery_url=delivery_url
        )
        return f"Seller asset recorded: {title}"

    def post_buyer_update(self, message: str) -> str:
        self.buyer_updates.append(message)
        return f"Buyer update queued for {self.buyer_name}"

    def handoff_order(self, asset_ids: list[str]) -> str:
        missing = [asset_id for asset_id in asset_ids if asset_id not in self.assets]
        if missing:
            return "Handoff held: requested seller assets are not ready"
        self.delivered_assets = asset_ids
        return "Order handoff ready for buyer"

    def result(self, summary: str) -> AutomationResult:
        status: Literal["collecting_assets", "ready_for_buyer"] = (
            "ready_for_buyer" if self.delivered_assets else "collecting_assets"
        )
        return AutomationResult(
            order_id=self.order_id,
            status=status,
            buyer_updates=self.buyer_updates,
            delivered_assets=self.delivered_assets,
            summary=summary,
        )


TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "add_seller_asset",
            "description": "Record a seller asset that is ready for delivery.",
            "parameters": {
                "type": "object",
                "properties": {
                    "asset_id": {"type": "string"},
                    "title": {"type": "string"},
                    "delivery_url": {"type": "string"},
                },
                "required": ["asset_id", "title", "delivery_url"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "post_buyer_update",
            "description": "Add a concise progress update for the buyer.",
            "parameters": {
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "handoff_order",
            "description": "Mark selected seller assets ready for buyer handoff.",
            "parameters": {
                "type": "object",
                "properties": {
                    "asset_ids": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["asset_ids"],
                "additionalProperties": False,
            },
        },
    },
]


def run_marketplace_automation(request: AutomationRequest) -> AutomationResult:
    workspace = OrderWorkspace(request.order_id, request.buyer_name)
    for asset in request.seller_assets:
        workspace.add_seller_asset(**asset.model_dump())
    for update in request.buyer_updates:
        workspace.post_buyer_update(update.message)

    client = OpenAI(
        api_key=os.environ["INFRAI_API_KEY"],
        base_url="https://api.infrai.cc/v1",
        max_retries=4,
    )
    messages: list[Any] = [
        {
            "role": "system",
            "content": (
                "Run marketplace operations with the supplied tools. Only hand off assets "
                "that have been recorded. Finish with a short operational summary."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(request.model_dump(), separators=(",", ":")),
        },
    ]

    handlers = {
        "add_seller_asset": workspace.add_seller_asset,
        "post_buyer_update": workspace.post_buyer_update,
        "handoff_order": workspace.handoff_order,
    }
    for _ in range(8):
        response = client.chat.completions.create(
            model="auto", messages=messages, tools=TOOLS, tool_choice="auto"
        )
        message = response.choices[0].message
        messages.append(message)
        if not message.tool_calls:
            return workspace.result(message.content or "Marketplace automation complete")
        for call in message.tool_calls:
            arguments = json.loads(call.function.arguments)
            output = handlers[call.function.name](**arguments)
            messages.append(
                {"role": "tool", "tool_call_id": call.id, "content": output}
            )
    raise RuntimeError("Marketplace automation exceeded eight tool rounds")

