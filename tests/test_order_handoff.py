from marketplace_handoff.order_handoff import OrderWorkspace


def test_handoff_waits_for_asset_then_becomes_ready() -> None:
    order = OrderWorkspace(order_id="order-42", buyer_name="Mina")

    held = order.handoff_order(["cover-final"])
    assert held == "Handoff held: requested seller assets are not ready"
    assert order.result("Waiting for the cover").status == "collecting_assets"

    order.add_seller_asset(
        asset_id="cover-final",
        title="Final podcast cover",
        delivery_url="https://cdn.example.test/orders/42/cover.png",
    )
    ready = order.handoff_order(["cover-final"])

    assert ready == "Order handoff ready for buyer"
    result = order.result("Final cover is ready")
    assert result.status == "ready_for_buyer"
    assert result.delivered_assets == ["cover-final"]

