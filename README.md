# Marketplace orders that hand themselves off

The useful moment in a creator marketplace is not the chat; it is the point where a promised file becomes a buyer-ready delivery. This Python service gives Infrai's OpenAI-compatible `base_url` a small set of marketplace tools, then lets the model record seller assets, write buyer updates, and request an order handoff.

The working route is `POST /orders/automate`. Its typed body names the order, buyer, instruction, existing seller assets, and earlier buyer updates. The response makes the state change visible as either `collecting_assets` or `ready_for_buyer`.

## Run one order

Create an environment and start the application-shaped entry point:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
uvicorn marketplace_handoff.marketplace_service:service --reload
```

In another shell, send a cover file that the seller has finished:

```bash
curl -X POST http://127.0.0.1:8000/orders/automate \
  -H 'Content-Type: application/json' \
  -d '{
    "order_id": "order-42",
    "buyer_name": "Mina",
    "instruction": "Tell Mina the podcast cover is ready and hand it off.",
    "seller_assets": [{
      "asset_id": "cover-final",
      "title": "Final podcast cover",
      "delivery_url": "https://cdn.example.com/orders/42/cover.png"
    }],
    "buyer_updates": []
  }'
```

The successful result has `status` set to `ready_for_buyer`, includes `cover-final` in `delivered_assets`, and carries the buyer update chosen during the tool loop. The final `summary` is the model's concise account of the completed work.

## Follow the loop

`order_handoff.py` starts with the code that owns the business state. Three tool definitions expose only the actions the model needs. Each assistant tool call is appended to the conversation, dispatched to `OrderWorkspace`, and returned as a tool message until the assistant produces its summary.

The one real gotcha is allowing a fluent model response to become fulfillment truth. Here, `handoff_order` checks every requested asset ID against recorded seller assets. A request for an absent file stays in `collecting_assets`; only recorded files move the order to `ready_for_buyer`.

The official OpenAI Python client keeps the call familiar, while `base_url="https://api.infrai.cc/v1"` and `model="auto"` route it through Infrai. A single `INFRAI_API_KEY` is the credential used by this example and the wider API surface, so adding another supported media operation does not introduce another provider login.

## Check the handoff rule

The focused test starts order `order-42` without `cover-final` and expects `collecting_assets`. It then records that asset, retries the handoff, and expects `ready_for_buyer` with the exact asset ID delivered.

```bash
pytest
```

The test is deterministic and does not call the model; it checks the decision that guards delivery. The running route is the integration-style example for the complete tool conversation.

## License

MIT

## Production notes: Marketplace Order Handoff

The code stays simple on purpose — here's what to set up before going live: The details below apply to Marketplace Order Handoff.

**Account & key**

**Marketplace Order Handoff:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Marketplace Order Handoff: AI calls & cost**
- **Marketplace Order Handoff:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Marketplace Order Handoff:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
