"""Remote-only audit of every exact Frank-Wolfe segment identity."""
import json
import platform
import sys

import numpy as np

from chainbench.simplex_geometry import run_simplex_geometry
from smoke_workflows import validate_fw_segments

summary = {"python": platform.python_version(), "numpy": np.__version__, "runs": []}
for steps in (1, 18, 60):
    for repeat in range(3):
        record = run_simplex_geometry(steps)
        if '--require-clean' in sys.argv:
            validate_fw_segments(record, required=True)
        faults = []
        maximum_gap_difference = 0.0
        counts = {}
        for case in record["cases"]:
            for row, nxt in zip(case["rows"], case["rows"][1:]):
                p = row["segment"]
                i, j = p["scheduled_index"], p["minimum_index"]
                comparisons = {
                    "point": (p["points"][i], nxt["x"]),
                    "scheduled_objective": (p["objective"][i], nxt["gap"]),
                    "minimum_point": (p["minimum_point"], p["points"][j]),
                    "minimum_value": (p["minimum_value"], p["objective"][j]),
                    "roundoff": (p["quadratic_roundoff_inf"], max(abs(a-b) for a,b in zip(p["objective"],p["quadratic"]))),
                    "endpoint_bound": (p["minimum_value"] <= min(row["gap"],nxt["gap"])+3e-15, True),
                }
                for key, (actual, expected) in comparisons.items():
                    if actual != expected:
                        counts[key] = counts.get(key, 0) + 1
                        if len(faults) < 8:
                            faults.append({"case": case["id"], "iteration": row["iteration"],
                                           "field": key, "actual": actual, "expected": expected})
                maximum_gap_difference = max(maximum_gap_difference, abs(p["objective"][i]-nxt["gap"]))
        summary["runs"].append({"steps": steps, "repeat": repeat, "counts": counts,
                                "max_scheduled_objective_difference": maximum_gap_difference,
                                "first_faults": faults})
np.show_config()
print("FW_DIAGNOSTIC_JSON=" + json.dumps(summary, allow_nan=False))
if '--require-clean' in sys.argv:
    assert all(not run['counts'] for run in summary['runs'])
