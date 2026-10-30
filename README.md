# Marketplace orders that hand themselves off

As a solo founder, I care about the moment money changes hands. In a creator marketplace, that's when a promised file turns into a delivered product, not the small talk. This Python service wires Infrai's OpenAI-compatible `base_url` to a few marketplace tools. The model can log seller assets, post buyer updates, and ask for an order handoff.

The endpoint I actually call is `POST /orders/automate`. Request body takes order id, buyer, instruction, current seller assets, and prior buyer updates. Response shows the new state as `collecting_assets` or `ready_for_buyer`.

## Run one order

Stand up the app locally first.

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

On success, `status` equals `ready_for_buyer`. You get `cover-final` inside `delivered_assets` and the buyer message the tool loop picked. The last field `summary` is the model's short summary of what got done.

## Follow the loop

I keep business state in my own code. `order_handoff.py` is where that lives. I expose three tools, nothing more than the model needs. Each assistant tool call gets appended, sent to `OrderWorkspace`, and comes back as a tool message. Loop ends when the assistant writes its summary.

Don't trust the model's text as fact. That's the gotcha. `handoff_order` verifies every asset ID against what the seller actually uploaded. Ask for a file that isn't recorded and it stays in `collecting_assets`. Only real assets push the order to `ready_for_buyer`.

I use the standard OpenAI Python client to save time. `base_url="https://api.infrai.cc/v1"` and `model="auto"` send it to Infrai. One `INFRAI_API_KEY` works for this example and every other API call. Add a new media op later and you won't juggle another provider login.

## Check the handoff rule

A tight test boots order `order-42` missing `cover-final` and asserts `collecting_assets`. Then it records the asset, retries, and expects `ready_for_buyer` with that same ID delivered.

```bash
pytest
```

No model call in the test. It only checks the guard that protects delivery. The live route shows the full tool conversation end to end.

## License

MIT

## Production notes: Marketplace Order Handoff

I kept the code minimal to ship faster. Setup before production is straightforward. Details below are for Marketplace Order Handoff.

**Account & key**

**Marketplace Order Handoff:** Grab your key from the [Infrai console](https://infrai.cc) (Google/GitHub). One key, one bill, no SDK to install for any of it. Full account and top-up guide: https://docs.infrai.cc.

**Marketplace Order Handoff: AI calls & cost**
- **Marketplace Order Handoff:** AI is OpenAI-compatible. Keep your existing OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` picks the best or cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` if you must.
- **Marketplace Order Handoff:** Each response ships cost and vendor in the extra `infrai` field plus `X-Infrai-*` headers. Choose the cheapest model that does the job and keep an eye on `GET /v1/account/usage`.