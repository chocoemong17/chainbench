from chainbench.checks import run_all, run_check


def test_all_bundled_checks_are_consistent():
    results = run_all()
    assert results
    assert all(r.consistent is not False for r in results)


def test_known_check():
    result = run_check("beck-teboulle-2009")
    assert result.consistent is True
