"""The rerun tolerance must not hide provenance or meaningful evidence changes."""
import copy
import math

import pytest
from _numeric_records import assert_recomputed_record


def record():
    return {
        'seed': 3,
        'input_sha256': 'a' * 64,
        'inputs': {'x0': [0.0, 1.0]},
        'config': {'step': 0.5},
        'rows': [{'iteration': 1, 'gap': 1e-6, 'iterate': [0.1, -0.2]}],
        'converged': False,
        'termination': 'max_steps',
        'unresolved': None,
    }


def test_independent_roundoff_is_allowed_without_modifying_either_record():
    original = record()
    rerun = copy.deepcopy(original)
    rerun['rows'][0]['gap'] = math.nextafter(1e-6, math.inf)
    rerun['rows'][0]['iterate'][0] = math.nextafter(0.1, math.inf)
    snapshot = copy.deepcopy(rerun)
    assert_recomputed_record(rerun, original)
    assert rerun == snapshot and original == record()
    # Actual failing Intel canonical residual, within the existing absolute tolerance.
    assert_recomputed_record(2.833996741079226e-7, 2.833996740567777e-7)


@pytest.mark.parametrize('fault', [
    'hash', 'seed', 'seed-type', 'iteration', 'iteration-type', 'missing-row',
    'missing-key', 'extra-key', 'status', 'bool-type', 'none', 'input', 'config',
    'gap', 'iterate', 'order',
])
def test_rerun_comparison_rejects_corrupted_evidence(fault):
    original = record()
    changed = copy.deepcopy(original)
    if fault == 'hash':
        changed['input_sha256'] = 'b' * 64
    elif fault == 'seed':
        changed['seed'] = 4
    elif fault == 'seed-type':
        changed['seed'] = 3.0
    elif fault == 'iteration':
        changed['rows'][0]['iteration'] = 2
    elif fault == 'iteration-type':
        changed['rows'][0]['iteration'] = 1.0
    elif fault == 'missing-row':
        changed['rows'].clear()
    elif fault == 'missing-key':
        changed.pop('unresolved')
    elif fault == 'extra-key':
        changed['extra'] = None
    elif fault == 'status':
        changed['termination'] = 'converged'
    elif fault == 'bool-type':
        changed['converged'] = 0
    elif fault == 'none':
        changed['unresolved'] = 0.0
    elif fault == 'input':
        changed['inputs']['x0'][1] = math.nextafter(1.0, math.inf)
    elif fault == 'config':
        changed['config']['step'] = math.nextafter(0.5, math.inf)
    elif fault == 'gap':
        changed['rows'][0]['gap'] += 1e-10
    elif fault == 'iterate':
        changed['rows'][0]['iterate'][0] += 1e-8
    else:
        changed['rows'][0]['iterate'].reverse()
    with pytest.raises(AssertionError, match=r'\$'):
        assert_recomputed_record(changed, original)


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -float('inf')])
@pytest.mark.parametrize('key', ['inputs', 'result'])
def test_even_matching_nonfinite_values_are_rejected(value, key):
    with pytest.raises(AssertionError, match='nonfinite'):
        assert_recomputed_record({key: [value]}, {key: [value]})
