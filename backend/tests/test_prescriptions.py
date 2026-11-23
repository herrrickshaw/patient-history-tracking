from app import prescriptions as rx


def drugs(dept):
    return [o["drug"] for o in rx.generate_orders(dept)]


def test_default_orders_only_for_unmatched_or_missing_department():
    base = [d[0] for d in rx.DEFAULT_ORDERS]
    assert drugs(None) == base
    assert drugs("") == base
    assert drugs("Neurology") == base


def test_surgery_and_cardiac_extras_case_insensitive_substring():
    base = [d[0] for d in rx.DEFAULT_ORDERS]
    assert drugs("General SURGERY") == base + [rx.SURGERY_EXTRA[0][0]]
    assert drugs("Cardiology") == base + [rx.CARDIAC_EXTRA[0][0]]
    both = drugs("Cardiac surgery")
    assert both == base + [rx.SURGERY_EXTRA[0][0], rx.CARDIAC_EXTRA[0][0]]


def test_order_shape_and_module_constants_not_mutated():
    before = list(rx.DEFAULT_ORDERS)
    orders = rx.generate_orders("surgery")
    rx.generate_orders("surgery")
    assert rx.DEFAULT_ORDERS == before
    first = orders[0]
    drug, dose, route, freq = rx.DEFAULT_ORDERS[0]
    assert first == {"drug": drug, "dose": dose, "route": route, "frequency_sim_sec": freq, "status": "active", "next_due": None}
    assert all(o["status"] == "active" and o["next_due"] is None for o in orders)
    # returned dicts are independent between calls
    orders[0]["status"] = "x"
    assert rx.generate_orders("surgery")[0]["status"] == "active"
