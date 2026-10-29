from datetime import date, timedelta

from golivecheck.run import expand, expand_list


def test_expand():
    ctx = {"proposal_id": "123e4567-e89b-12d3-a456-426614174000", "amount": "50.00"}
    d = lambda n: (date.today() + timedelta(days=n)).isoformat()
    assert expand("pay ${amount} on {date+7}", ctx) == f"pay $50.00 on {d(7)}"
    assert expand("{date-1} {proposal_id}", ctx) == f"{d(-1)} {ctx['proposal_id']}"


def test_expand_list():
    policy = {"phrases": {"success": ["a", "b"], "forbidden": ["x"]}}
    assert expand_list(["{policy.success}", "z"], policy) == ["a", "b", "z"]