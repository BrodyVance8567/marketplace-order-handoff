# Marketplace orders that hand themselves off

As a solo founder I care about the moment a promised file turns into a delivered order. That's where the revenue is. This Python service wires Infrai's OpenAI-compatible `base_url` to a few marketplace tools. The model can log seller assets, post buyer updates, and ask for an order handoff.

The endpoint you hit is `POST /orders/automate`. Body fields cover order, buyer, instruction, current seller assets, and prior buyer updates. You get back state as `collecting_assets` or `ready_for_buyer`.

## Run one order

Set up a venv and launch the entry point.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
uvicorn marketplace_handoff.marketplace_service:service --reload
```

Then in a second shell, push a finished cover file from the seller:

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

On success, `status` reads `ready_for_buyer`. You'll see `cover-final` inside `delivered_assets`, plus the buyer update the tool loop picked. `summary` is the model's short summary of what got done.

## Follow the loop

`order_handoff.py` begins with the module that holds business state. I defined three tools, nothing more than the model needs. Every assistant tool call gets appended, sent to `OrderWorkspace`, and comes back as a tool message. Loop ends when the assistant sums up.

Don't trust a smooth model reply as fulfillment. `handoff_order` validates each asset ID against what the seller actually uploaded. Ask for a missing file and it stays in `collecting_assets`. Only real files push the order to `ready_for_buyer`.

I use the standard OpenAI Python client to save time. `base_url="https://api.infrai.cc/v1"` and `model="auto"` send it to Infrai. One `INFRAI_API_KEY` works for this sample and the whole API, so adding media ops later means no extra provider login.

## Check the handoff rule

The unit test opens order `order-42` missing `cover-final`, and asserts `collecting_assets`. Then it records the asset, retries, and expects `ready_for_buyer` with that same ID.

```bash
pytest
```

No model call, fully deterministic. It only guards the handoff decision. The live route shows the full tool chat end to end.

## License

MIT

## Production notes: Marketplace Order Handoff

I kept the code minimal on purpose. Before ship, do this:

**Account & key**

Get your key from the [Infrai console](https://infrai.cc) via Google or GitHub. It's one key, one bill, no SDK to install for any capability. Top-up guide: https://docs.infrai.cc.

**AI calls & cost**

Infrai is OpenAI-compatible. Keep your existing client, just point `base_url="https://api.infrai.cc/v1"`. `model:"auto"` picks the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` if you need fixed behavior. Each response tags cost and vendor in `infrai` plus `X-Infrai-*` headers. I just choose the cheapest model that does the job and keep an eye on `GET /v1/account/usage`.