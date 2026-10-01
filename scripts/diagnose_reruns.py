"""Measure rerun differences; diagnostic evidence, never a passing theorem test."""
from dataclasses import asdict
import json
import math
import os
import platform

import numpy as np

from chainbench.checks import CHECKS
from chainbench.learning import ratio_chart
from chainbench.stress import run_stress, run_stress_case
from chainbench.visuals import build_check_chart

class Differences:
    def __init__(self):
        self.floats = 0
        self.changed_floats = 0
        self.exact_fault_count = 0
        self.exact_faults = []
        self.nonfinite = 0
        self.max_absolute = None
        self.max_scaled = None
        self.max_relative = None
        self.threshold_exceedances = {"1e-12/1e-14": 0, "1e-12/1e-12": 0,
                                     "1e-10/1e-12": 0, "1e-7/1e-12": 0}
    def fault(self, path, why):
        self.exact_fault_count += 1
        if len(self.exact_faults) < 8:
            self.exact_faults.append({"path": path, "reason": why})
    def compare(self, a, b, path="$", exact=False):
        if isinstance(a, float) and isinstance(b, float):
            self.floats += 1
            if not (math.isfinite(a) and math.isfinite(b)):
                self.nonfinite += 1
                self.fault(path, "nonfinite")
                return
            delta = abs(a-b)
            if exact and a != b:
                self.fault(path, "exact input/config float changed")
            if not delta:
                return
            self.changed_floats += 1
            entry = {"path": path, "a": float(a), "b": float(b), "absolute": delta,
                     "scaled": delta/max(1., abs(a), abs(b)),
                     "relative": delta/max(abs(a), abs(b))}
            for key in ("absolute", "scaled", "relative"):
                old = getattr(self, "max_"+key)
                if old is None or entry[key] > old[key]:
                    setattr(self, "max_"+key, entry)
            for label in self.threshold_exceedances:
                rt, at = map(float, label.split("/"))
                if not math.isclose(a, b, rel_tol=rt, abs_tol=at):
                    self.threshold_exceedances[label] += 1
            return
        if type(a) is not type(b):
            self.fault(path, "types differ")
        elif isinstance(a, dict):
            if a.keys() != b.keys():
                self.fault(path, "keys differ")
            for key in a.keys() & b.keys():
                self.compare(a[key], b[key], path+"."+key,
                             exact or key in {"inputs", "config"})
        elif isinstance(a, (list, tuple)):
            if len(a) != len(b):
                self.fault(path, "lengths differ")
            for k, (left, right) in enumerate(zip(a,b)):
                self.compare(left,right,f"{path}[{k}]",exact)
        elif a != b:
            self.fault(path, "nonfloating value changed")
    def emit(self, name):
        print(json.dumps({"comparison": name, **self.__dict__}, allow_nan=False), flush=True)

print(json.dumps({"purpose": "Measure all differences; thresholds are diagnostics, not altered tests",
                  "python": platform.python_version(), "numpy": np.__version__,
                  "system": platform.system(), "machine": platform.machine(),
                  "thread_environment": {k: os.environ.get(k) for k in
                      ("OPENBLAS_NUM_THREADS","VECLIB_MAXIMUM_THREADS","OMP_NUM_THREADS",
                       "MKL_NUM_THREADS","BLIS_NUM_THREADS")}}), flush=True)
np.show_config()
for topic in CHECKS:
    stats = Differences()
    first = run_stress(topic, trials=32, seed=0)
    for repeat in range(3):
        stats.compare(first,run_stress(topic,trials=32,seed=0),f"{topic}.repeat{repeat}")
    for row in first["rows"]:
        stats.compare(row,run_stress_case(topic,row["seed"])["case"],
                      f"{topic}.single_seed{row['seed']}")
    stats.emit(topic+"; seeds 0..31; 3 full reruns plus individual cases")
for topic in CHECKS:
    stats = Differences()
    first_chart = build_check_chart(topic)
    first = asdict(first_chart)
    ratio = ratio_chart(topic,first_chart)
    first_ratio = asdict(ratio) if ratio is not None else None
    for repeat in range(10):
        other = build_check_chart(topic)
        stats.compare(first,asdict(other),f"{topic}.chart{repeat}")
        ratio = ratio_chart(topic,other)
        stats.compare(first_ratio,asdict(ratio) if ratio is not None else None,
                      f"{topic}.normalized{repeat}")
    stats.emit(topic+"; canonical and normalized charts; 10 reruns")
