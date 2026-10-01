"""Controlled 2D LASSO splitting, following Boyd et al. (2011), section 6.4."""
from __future__ import annotations

import hashlib
import itertools
import json
import math
import platform

import numpy as np

from . import __version__

SOURCE = 'https://web.stanford.edu/~boyd/papers/pdf/admm_distr_stats.pdf'
FAMILIES = {'diagonal': ((1.,0.),(0.,3.)), 'coupled': ((2.,1.),(1.,2.))}
STARTS = {'zero': (0.,0.), 'opposite': (-1.8,1.2)}
FRACTIONS = (.1,.6,1.1)
RHOS = (.1,1.,10.)
B = (1.4,-2.4)


def _optimum(A, b, lam):
    """Enumerate the nine sign patterns; check the original LASSO KKT system."""
    Q, c = A.T@A, A.T@b
    candidates = []
    for signs in itertools.product((-1,0,1),repeat=2):
        active = np.flatnonzero(signs)
        point = np.zeros(2)
        if len(active):
            point[active] = np.linalg.solve(Q[np.ix_(active,active)],c[active]-lam*np.array(signs)[active])
        if any(point[i]*signs[i]<=0 for i in active):
            continue
        gradient = Q@point-c
        if any(abs(gradient[i])>lam for i in range(2) if not signs[i]):
            continue
        subgradient = np.array([float(signs[i]) if signs[i] else -gradient[i]/lam for i in range(2)])
        residual = gradient+lam*subgradient
        if not np.allclose(residual,0.,rtol=0.,atol=2e-14):
            raise FloatingPointError('LASSO active-set solve fails its KKT check')
        candidates.append((point,subgradient,residual))
    if len(candidates)!=1:
        raise FloatingPointError('Expected one strictly convex LASSO solution')
    return candidates[0]


def objective(point, A, b, lam):
    residual = A@point-b
    return float(.5*(residual@residual)+lam*np.sum(np.abs(point)))


def stable_gap(point, A, star, subgradient, lam):
    """Quadratic error plus the L1 Bregman term, retaining raw subtraction too."""
    error = A@(point-star)
    return float(.5*(error@error)+lam*np.sum(np.abs(point)-subgradient*point))


def _run(inputs, star, subgradient, fstar):
    A,b = np.array(inputs['A']),np.array(inputs['b'])
    rho,lam = inputs['rho'],inputs['lambda']
    Q,c = A.T@A,A.T@b
    H = Q+rho*np.eye(2)
    z,u = np.array(inputs['z0']),np.array(inputs['u0'])
    initial_objective = objective(z,A,b,lam)
    initial_gap = stable_gap(z,A,star,subgradient,lam)
    rows = [dict(iteration=0,x=None,z=z.tolist(),u=u.tolist(),y=(rho*u).tolist(),
                 x_target=None,x_rhs=None,x_equation_residual=None,shrink_input=None,
                 primal_residual=None,dual_residual=None,primal_norm=None,dual_norm=None,
                 eps_primal=None,eps_dual=None,stopping_passed=None,
                 dual_stationarity=None,dual_identity_residual=None,dual_box_excess=None,
                 objective_x=None,objective_z=initial_objective,split_objective=None,
                 stable_gap_x=None,stable_gap_z=initial_gap,raw_gap_z=initial_objective-fstar,
                 gap_roundoff_difference=(initial_objective-fstar)-initial_gap,split_minus_optimum=None)]
    first_pass = None
    for k in range(1,inputs['steps']+1):
        previous = z.copy()
        target = z-u
        rhs = c+rho*target
        x = np.linalg.solve(H,rhs)
        shrink_input = x+u
        z = np.sign(shrink_input)*np.maximum(np.abs(shrink_input)-lam/rho,0.)
        primal = x-z
        u = u+primal
        y = rho*u
        dual = -rho*(z-previous)
        rn,sn = float(np.linalg.norm(primal)),float(np.linalg.norm(dual))
        ep = math.sqrt(2)*inputs['abs_tol']+inputs['rel_tol']*max(float(np.linalg.norm(x)),float(np.linalg.norm(z)))
        ed = math.sqrt(2)*inputs['abs_tol']+inputs['rel_tol']*float(np.linalg.norm(y))
        passed = rn<=ep and sn<=ed
        if passed and first_pass is None:
            first_pass = k
        smooth_residual = A@x-b
        stationarity = A.T@smooth_residual+y
        fz = objective(z,A,b,lam)
        gapz = stable_gap(z,A,star,subgradient,lam)
        split = float(.5*(smooth_residual@smooth_residual)+lam*np.sum(np.abs(z)))
        rows.append(dict(iteration=k,x=x.tolist(),z=z.tolist(),u=u.tolist(),y=y.tolist(),
            x_target=target.tolist(),x_rhs=rhs.tolist(),x_equation_residual=(H@x-rhs).tolist(),
            shrink_input=shrink_input.tolist(),primal_residual=primal.tolist(),dual_residual=dual.tolist(),
            primal_norm=rn,dual_norm=sn,eps_primal=ep,eps_dual=ed,stopping_passed=passed,
            dual_stationarity=stationarity.tolist(),dual_identity_residual=(stationarity-dual).tolist(),
            dual_box_excess=(np.abs(y)-lam).tolist(),objective_x=objective(x,A,b,lam),objective_z=fz,
            split_objective=split,stable_gap_x=stable_gap(x,A,star,subgradient,lam),stable_gap_z=gapz,
            raw_gap_z=fz-fstar,gap_roundoff_difference=(fz-fstar)-gapz,split_minus_optimum=split-fstar))
    return dict(rows=rows,updates=inputs['steps'],termination='fixed_budget',first_residual_pass=first_pass,
                observations=dict(final_primal_norm=rows[-1]['primal_norm'],final_dual_norm=rows[-1]['dual_norm'],
                    final_stable_gap=rows[-1]['stable_gap_z'],final_residual_pass=rows[-1]['stopping_passed'],
                    split_below_optimum_rounds=[r['iteration'] for r in rows[1:] if r['split_minus_optimum']<0],
                    primal_objective_increase_rounds=[k for k in range(1,len(rows))
                        if rows[k]['objective_z']-rows[k-1]['objective_z']>1e-12]))


def run_admm_geometry(steps: int = 60) -> dict:
    if type(steps) is not int or not 1<=steps<=160:
        raise ValueError('steps must be an integer between 1 and 160')
    cases = []
    for family,matrix in FAMILIES.items():
        A,b = np.array(matrix),np.array(B)
        maximum = float(np.max(np.abs(A.T@b)))
        for fraction in FRACTIONS:
            lam = fraction*maximum
            star,subgradient,kkt_residual = _optimum(A,b,lam)
            fstar = objective(star,A,b,lam)
            for start_name,start in STARTS.items():
                for rho in RHOS:
                    inputs = dict(A=A.tolist(),b=b.tolist(),dimension=2,
                        lambda_fraction=fraction,lambda_max=maximum,**{'lambda':lam},rho=rho,
                        z0=list(start),u0=[0.,0.],initial_x=None,relaxation=1.,
                        abs_tol=1e-4,rel_tol=1e-2,steps=steps,
                        penalty_policy='fixed rho',stopping_policy='fixed budget; record <= residual test without early exit')
                    digest = hashlib.sha256(json.dumps(inputs,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
                    run = _run(inputs,star,subgradient,fstar)
                    cases.append(dict(id=f'{family}-lambda{fraction:g}-{start_name}-rho{rho:g}',
                        family=family,start_name=start_name,inputs=inputs,input_sha256=digest,
                        optimum=dict(point=star.tolist(),value=fstar,subgradient=subgradient.tolist(),
                            stationarity_residual=kkt_residual.tolist(),active_coordinates=np.flatnonzero(star).tolist(),
                            method='enumerate all nine 2D sign patterns and check LASSO KKT conditions'),
                        smooth_spectrum=[1.,9.],smooth_condition=9.,
                        native_iterations=sorted({k for k in (0,1,2,5,10,30,60,160,steps) if k<=steps}),**run))
    # A shared square contains every original-primal x/z point, including starts
    # and optima. The scaled-dual and shrink-input spaces have their own units.
    points = [r[key] for c in cases for r in c['rows'] for key in ('x','z') if r[key] is not None]
    points += [c['optimum']['point'] for c in cases]
    radius = max(1.,math.ceil(max(abs(v) for p in points for v in p)*1.1*2)/2)
    result = dict(kind='chainbench.admm-lasso-geometry',schema_version=1,
        evidence_level='controlled-geometric-illustrations',
        source=dict(url=SOURCE,authors=['Stephen Boyd','Neal Parikh','Eric Chu','Borja Peleato','Jonathan Eckstein'],
            title='Distributed Optimization and Statistical Learning via the Alternating Direction Method of Multipliers',
            year=2011,role='review of an algorithm originating in the 1970s',
            recurrence='Section 6.4 / Eq. (6.2) and displayed updates, printed p.43 / PDF page 46',
            residuals='Section 3.3, printed pp.18-19 / PDF pages 21-22; Eq. (3.12)',
            objective_scope='Section 11.1.1 / Figure 11.2, printed p.89 / PDF page 92 evaluates the original objective at z',
            example_url='https://web.stanford.edu/~boyd/papers/admm/lasso/lasso_example.html'),
        problem=dict(objective='F(w)=0.5||Aw-b||_2^2+lambda||w||_1',split='f(x)+g(z), subject to x-z=0',
            constraint_matrices='I and -I, distinct from the feature matrix A',domain='R^2',seed=None,
            optimum='unique original-primal solution, since both declared A^T A have spectrum [1,9]'),
        parameters=dict(steps=steps,families=list(FAMILIES),lambda_fractions=list(FRACTIONS),
            starts=list(STARTS),rhos=list(RHOS),abs_tol=1e-4,rel_tol=1e-2,relaxation=1.),
        design='all 2 matrices x 3 lambda fractions x 2 starts x 3 fixed penalties; no outcome filtering',
        geometry=dict(primal_bounds=[-radius,radius,-radius,radius],
            bounds_scope='shared square for all original-primal x/z paths and optima in this finite budget',
            surface_height='stable algebraic F(w)-F*, not the infeasible split value f(x)+g(z)-F*',
            dual_coordinates='y=rho*u in feature coordinates; not measurement-space residual dual variables',
            dual_box='[-lambda,lambda]^2; retain raw floating-point excess, no clipping of recorded y'),
        input_hash_encoding='SHA-256 of sorted-key compact UTF-8 JSON inputs',
        cases=cases,environment=dict(chainbench=__version__,numpy=np.__version__,python=platform.python_version()),
        limits=[
            'New controlled 2D inputs, not the original 1500x5000 dense experiment or its RNG, optimum, timing or stop count.',
            'The source is a 2011 review; ADMM is not attributed as a new 2011 algorithm.',
            'No over-relaxation, adaptive penalty, distributed execution or general solver API.',
            'The split objective at x!=z is not an original-primal gap or a certified lower bound.',
            'Residual thresholds are finite stopping diagnostics, not an accuracy theorem or a method ranking.',
            'x at iteration zero is undefined; no initial solve, residual or split objective is invented.',
            'Surface chords join actual endpoints; they are not continuous optimizer trajectories.',
            'Floating-point solve, stationarity, dual-box and gap-subtraction differences are retained.',
        ])
    json.dumps(result,allow_nan=False)
    return result
