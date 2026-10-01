"""Compare independent reruns; never use this for serialization or file integrity."""
import math

# Match the canonical trajectory check, not the looser public replay default.
RTOL = 1e-12
ATOL = 1e-14


def assert_recomputed_record(actual, expected, *, path='$', exact=False):
    """Keep schema/provenance exact and allow roundoff in recomputed floats only."""
    assert type(actual) is type(expected), f'{path}: types differ'
    if isinstance(actual, dict):
        assert actual.keys() == expected.keys(), f'{path}: keys differ'
        for key in actual:
            assert_recomputed_record(
                actual[key], expected[key], path=f'{path}.{key}',
                exact=exact or key in {'inputs', 'config'},
            )
    elif isinstance(actual, (list, tuple)):
        assert len(actual) == len(expected), f'{path}: lengths differ'
        for index, (left, right) in enumerate(zip(actual, expected)):
            assert_recomputed_record(left, right, path=f'{path}[{index}]', exact=exact)
    elif isinstance(actual, float):
        assert math.isfinite(actual) and math.isfinite(expected), f'{path}: nonfinite value'
        matched = actual == expected if exact else math.isclose(
            actual, expected, rel_tol=RTOL, abs_tol=ATOL,
        )
        assert matched, f'{path}: {actual!r} != {expected!r}'
    else:
        # Includes hashes, source/environment strings, counts, ranks, bool and None.
        assert actual == expected, f'{path}: values differ'
