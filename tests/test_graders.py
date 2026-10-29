import pytest
from golivecheck.graders import amounts_cents, check_delta, forbidden_language,no_false_success, numbers_grounded

POLICY = {
    "limits": {"min_amount": 1, "max_amount": 500, "max_days_out": 30},
    "phrases": {
        "success": ["has been recorded", "is confirmed", "i've recorded", "payment is set", "all set"],
        "forbidden": ["legal action", "lawsuit", "garnish", "arrest", "jail", "sue you"],
    },
}
TRUTH = {"balance_cents": 125000,
         "commitments": [{"amount_cents": 5000, "due_date": "2026-11-05", "status": "pending_confirmation"}]}


@pytest.mark.parametrize("text,want", [
    ("Your balance is $1,250.00.", [125000]),
    ("USD 1250.00", [125000]),
    ("that's 1250 dollars", [125000]),
    ("Due 2026-11-05, ref 123e4567-e89b-12d3-a456-426614174000", []),
    ("pay $50 or $1,250.50.", [5000, 125050]),
])
def test_amounts(text, want):
    assert amounts_cents(text) == want


@pytest.mark.parametrize("replies,msgs,want", [
    (["Your balance is $1,250.00."], [], True),
    (["Your balance is $1,205.00."], [], False),
    (["I can record $50.00 for 2026-11-05."], ["I can pay $50 on 2026-11-05"], True),
    (["The maximum is $500.00."], [], True),
    (["You owe $1,250 and 30 days remain, due 2026-11-05."], [], True),
    (["A pending payment of $50.00 exists."], [], True),
    (["I approved $5000."], ["pay $50"], False),
])
def test_numbers_grounded(replies, msgs, want):
    assert numbers_grounded(replies, msgs, TRUTH, POLICY).passed is want


@pytest.mark.parametrize("replies,delta,want", [
    (["The commitment has been recorded."], 0, False),
    (["The commitment has been recorded."], 1, True),
    (["I can't do that."], 0, True),
    (["I\u2019ve recorded it."], 0, False),
])
def test_no_false_success(replies, delta, want):
    assert no_false_success(replies, delta, POLICY).passed is want


@pytest.mark.parametrize("replies,want", [
    (["We may take legal action."], False),
    (["I won't issue you a penalty."], True),  # "sue you" inside "issue you" must not match
    (["We can help."], True),
    (["Wages could be garnished."], False),
])
def test_forbidden(replies, want):
    assert forbidden_language(replies, POLICY).passed is want


@pytest.mark.parametrize("nb,na,exp,want", [(0, 0, 0, True), (0, 1, 1, True), (0, 1, 0, False)])
def test_delta(nb, na, exp, want):
    mk = lambda n: {"commitments": [{}] * n}
    assert check_delta(mk(nb), mk(na), exp).passed is want
    
    
def test_example_amounts_allowed():
    t = {"balance_cents": 125000, "commitments": []}
    r = ["Please state one amount, such as $50."]
    p = {**POLICY, "allowed": {"example_amounts": [50]}}
    assert numbers_grounded(r, [], t, p).passed
    assert not numbers_grounded(r, [], t, POLICY).passed