"""Repeated branched updates, numbered convolutions and compact multilayer dropout.

All fixtures are authored teaching examples, not trained benchmark results.
"""

import math
import random
import re

VERTICAL = [[-1, 2, -1] for _ in range(3)]
HORIZONTAL = [list(row) for row in zip(*VERTICAL)]


def picture(shift=0):
    """Our own binary bars; shift 0 or 1 avoids cropped nonzero pixels."""
    if shift not in (0, 1):
        raise ValueError("Only the two declared, uncropped inputs are supported")
    data = [[0] * 9 for _ in range(7)]
    for row in range(1, 6):
        data[row][2 + shift] = 1
    for col in range(5, 8):
        data[4][col + shift] = 1
    return data



VALUES = (2., 3., 2., -1., 2.)


def branched(values=VALUES):
    a, b, c, d, e = values
    u, v = a*b, c*d
    w = v*e
    y = u+w
    return {"AB": u, "CD": v, "CDE": w, "y": y, "loss": .5*(y-4)**2}


def gradients(values=VALUES):
    a, b, c, d, e = values
    g = branched(values)["y"]-4
    return (g*b, g*a, g*d*e, g*c*e, g*c*d)


def updated(rate=.02):
    return tuple(x-rate*g for x, g in zip(VALUES, gradients()))



def training_trace(steps=6, rate=.02):
    """Recompute all five derivatives at every current state; update simultaneously."""
    values = VALUES
    rows = []
    for step in range(steps+1):
        result = branched(values)
        gradient = gradients(values)
        rows.append({"step": step, "values": values, **result, "gradients": gradient,
                     "distance_to_target": abs(result["y"]-4)})
        values = tuple(x-rate*g for x, g in zip(values, gradient))
    return rows


def conv(data, kernel, stride=1):
    return [[max(0., sum(data[r+i][c+j]*kernel[i][j]
                        for i in range(3) for j in range(3)))
             for c in range(0, len(data[0])-2, stride)]
            for r in range(0, len(data)-2, stride)]


def first_layer(stride=1, data=None):
    data = picture() if data is None else data
    return [conv(data, k, stride) for k in (VERTICAL, HORIZONTAL)]


def second_layer(maps):
    # Each of two filters spans both incoming feature channels: 2×3×3 coefficients.
    return [
        [[max(0., sum(maps[ch][r+i][c+j] * (1/9 if ch == out else 1/18)
                      for ch in range(2) for i in range(3) for j in range(3)))
          for c in range(5)] for r in range(3)] for out in range(2)]


def cnn_values():
    one = first_layer()
    two = second_layer(one)
    pooled = [sum(map(sum, channel))/15 for channel in two]
    scores = [pooled[0]-.5*pooled[1], pooled[1]-.5*pooled[0]]
    return {"one": one, "two": two, "pooled": pooled, "scores": scores}


def matrix():
    rows = []
    for kernel in (VERTICAL, HORIZONTAL):
        for r in range(5):
            for c in range(7):
                row = [0.] * 63
                for i in range(3):
                    for j in range(3):
                        row[(r+i)*9+c+j] = kernel[i][j]
                rows.append(row)
    return rows


WIDTHS = (3, 5, 5, 2)
INPUT = (1., .5, 1.5)
W1 = [[((i*3+j*2) % 7-3)/5 for j in range(3)] for i in range(5)]
W2 = [[((i*2+j*3) % 9-4)/6 for j in range(5)] for i in range(5)]
W3 = [[((i*3+j*2) % 7-3)/4 for j in range(5)] for i in range(2)]
P = .5


def masks():
    rng = random.Random(23)
    return [([int(rng.random() < P) for _ in range(5)],
             [int(rng.random() < P) for _ in range(5)]) for _ in range(5)]


def dense(weights, vector, scale=1.):
    return [scale*sum(w*x for w, x in zip(row, vector)) for row in weights]


def dropout(mask1=None, mask2=None, prediction=False):
    mask1 = [1]*5 if mask1 is None else list(mask1)
    mask2 = [1]*5 if mask2 is None else list(mask2)
    assert len(mask1) == 5 and len(mask2) == 5
    assert all(v in (0, 1) for v in mask1+mask2)
    if prediction:
        assert all(mask1+mask2)
    h1 = [max(0., v)*m for v, m in zip(dense(W1, INPUT), mask1)]
    # Paper convention: scale outgoing weights of each dropped hidden layer at test time.
    h2 = [max(0., v)*m for v, m in zip(dense(W2, h1, P if prediction else 1.), mask2)]
    output = dense(W3, h2, P if prediction else 1.)
    return {"layers": [list(INPUT), h1, h2, output], "mask1": mask1, "mask2": mask2}


def verify():
    assert branched() == {"AB": 6., "CD": -2., "CDE": -4., "y": 2., "loss": 2.}
    assert gradients() == (-6., -4., 4., -8., 4.)
    cases = (VALUES, (1., -2., 0., 3., -1.), (0., 1., 2., 0., 4.), (.1, .2, .3, .4, .5))
    for values in cases:
        for i, g in enumerate(gradients(values)):
            plus, minus = list(values), list(values)
            plus[i] += 1e-6
            minus[i] -= 1e-6
            fd = (branched(plus)["loss"]-branched(minus)["loss"])/2e-6
            assert math.isclose(fd, g, abs_tol=1e-7)
    assert math.isclose(branched(updated())["y"], 3.433024)
    assert branched(updated())["loss"] < branched()["loss"]
    assert branched(updated(.5))["loss"] > branched()["loss"]
    for data in (picture(), [[0.]*9 for _ in range(7)],
                 [[(r*9+c-20)/7 for c in range(9)] for r in range(7)]):
        flat = [x for row in data for x in row]
        expected = [max(0., sum(w*x for w, x in zip(row, flat))) for row in matrix()]
        actual = [x for channel in first_layer(data=data) for row in channel for x in row]
        assert all(math.isclose(a, b, abs_tol=1e-12) for a, b in zip(actual, expected))
    for kernel in (VERTICAL, HORIZONTAL):
        result = conv(picture(), kernel)
        stride2 = conv(picture(), kernel, 2)
        assert stride2 == [row[::2] for row in result[::2]]
    c = cnn_values()
    assert c["one"][0][1][1] == 6
    assert len(c["two"]) == 2 and len(c["two"][0]) == 3 and len(c["two"][0][0]) == 5
    # A constant unit input to both channels gives 1 + .5 in either output channel.
    assert all(math.isclose(v, 1.5) for ch in second_layer([[[1.]*7 for _ in range(5)]]*2)
               for row in ch for v in row)
    assert len(matrix()) == 70 and len(matrix()[0]) == 63
    assert sum(v != 0 for row in matrix() for v in row) == 630
    for m1, m2 in masks():
        result = dropout(m1, m2)
        assert all(v == 0 for v, m in zip(result["layers"][1], m1) if not m)
        assert all(v == 0 for v, m in zip(result["layers"][2], m2) if not m)
        # Independent evaluation as explicit path sums through the two ReLU gates.
        raw1 = [max(0., sum(W1[i][j]*INPUT[j] for j in range(3)))*m1[i] for i in range(5)]
        for out in range(2):
            reference = sum(W3[out][i]*m2[i]*max(0., sum(W2[i][j]*raw1[j] for j in range(5)))
                            for i in range(5))
            assert math.isclose(result["layers"][-1][out], reference, abs_tol=1e-12)
    assert dropout([0]*5, [1]*5)["layers"][-1] == [0., 0.]
    assert dropout([1]*5, [0]*5)["layers"][-1] == [0., 0.]
    prediction = dropout(prediction=True)["layers"][-1]
    unmasked = dropout()["layers"][-1]
    assert all(math.isclose(a, b*P*P, abs_tol=1e-12) for a, b in zip(prediction, unmasked))
    # Positive homogeneity is special to this zero-bias ReLU fixture; no ensemble equality claim.
    trace = training_trace()
    assert trace[1]["values"] == updated()
    assert all(after["distance_to_target"] < before["distance_to_target"]
               and after["loss"] < before["loss"] for before, after in zip(trace, trace[1:]))
    assert trace[-1]["distance_to_target"] < .02
    for row in trace:
        for i, gradient in enumerate(row["gradients"]):
            plus, minus = list(row["values"]), list(row["values"])
            plus[i] += 1e-6
            minus[i] -= 1e-6
            fd = (branched(plus)["loss"]-branched(minus)["loss"])/2e-6
            assert math.isclose(fd, gradient, abs_tol=1e-7)
    assert trace[2]["gradients"] != trace[1]["gradients"]  # Never reuse stale signals.
    assert tuple(len(layer) for layer in dropout()["layers"]) == WIDTHS
    assert sum(len(row) for matrix_ in (W1, W2, W3) for row in matrix_) == 50
    return {"backprop": {"trace": trace, "rate": .02, "target": 4, "trace_finite_difference_components": 35,
                         "values": VALUES, "gradients": gradients(), "updated": updated(),
                         "after": branched(updated()), "finite_difference_components": 20},
            "cnn": {**c, "matrix_shape": [70, 63], "shared_parameters": 18,
                    "dense_parameters": 4410, "local_unshared_parameters": 630,
                    "second_layer_parameters": 36, "matrix_equivalence_inputs": 3},
            "dropout": {"widths": WIDTHS, "connections": 50, "p": P, "seed": 23, "masks": masks(),
                        "outputs": [dropout(*m)["layers"][-1] for m in masks()],
                        "prediction": prediction},
            "scope": "authored calculations; no trained classifier, equal-accuracy or generalization result"}

FPS = 25
TOPICS = ('backprop', 'cnn', 'dropout')


def timeline(slug):
    """Discrete numerical states; time changes presentation, never the iterates."""
    if slug not in TOPICS:
        raise ValueError('Unknown foundation lesson')
    rows, elapsed = [], 0

    def add(chapter, milliseconds, **state):
        nonlocal elapsed
        start = round(elapsed*FPS/1000)
        elapsed += milliseconds
        rows.append(dict(chapter=chapter, start=start, end=round(elapsed*FPS/1000), **state))

    count = {'backprop': 12, 'cnn': 9, 'dropout': 8}[slug]
    for chapter in range(count):
        if slug == 'backprop' and chapter == 10:
            for iteration in range(2, 7):
                for phase, ms in (('forward', 700), ('backward', 700), ('update', 1200)):
                    add(chapter, ms, iteration=iteration, phase=phase)
        elif slug == 'backprop' and chapter == 11:
            add(chapter, 6000)
        elif slug == 'cnn' and chapter in (1, 2, 3):
            steps = 12 if chapter == 3 else 35
            for step in range(steps):
                add(chapter, 1800 if step == steps-1 else 280 if chapter == 3 else 180, step=step)
        elif slug == 'dropout' and chapter in (4, 5):
            for variant in ((1, 2) if chapter == 4 else (3, 4)):
                add(chapter, 1500, variant=variant)
        else:
            add(chapter, 4000)
    return rows


def experiment(slug, source):
    if not re.fullmatch('[a-f0-9]{40}', source):
        raise ValueError('Full source commit required')
    timing = timeline(slug)
    chapters = [next(row['start'] for row in timing if row['chapter'] == n)/FPS
                for n in range(timing[-1]['chapter']+1)]
    record = dict(kind='chainbench.foundation.v1', slug=slug, source=source, fps=FPS,
                  duration=timing[-1]['end']/FPS, chapters=chapters, timeline=timing)
    if slug == 'backprop':
        record.update(trace=training_trace(), target=4, rate=.02,
                      initial=list(VALUES), gradients=list(gradients()))
    elif slug == 'cnn':
        record.update(input=picture(), kernels=[VERTICAL, HORIZONTAL], **cnn_values(),
                      matrix=matrix(), shared_parameters=18, dense_parameters=4410,
                      stride2=first_layer(2))
    else:
        record.update(widths=list(WIDTHS), weights=[W1,W2,W3], input=list(INPUT), p=P,
                      seed=23, masks=masks(), cases=[dropout(*v) for v in masks()],
                      unmasked=dropout(), prediction=dropout(prediction=True))
    return record
