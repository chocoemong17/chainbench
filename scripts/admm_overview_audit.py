"""Read the rendered factorial table; compare it with an audited ADMM record."""
import itertools
import math

SNAPSHOT = r'''()=>[...document.querySelectorAll('[data-admm-overview-group]')].map(group=>({
 id:group.dataset.admmOverviewGroup,
 caption:group.querySelector('caption').textContent,
 columns:[...group.querySelectorAll('thead th')].map(n=>n.textContent),
 rows:[...group.querySelectorAll('tbody tr')].map(row=>({
  fraction:row.querySelector('th').textContent,
  cells:[...row.querySelectorAll('td')].map(cell=>{
   const link=cell.querySelector('[data-admm-overview-link]'),
    target=link&&document.getElementById(link.getAttribute('href').slice(1)),
    first=cell.querySelector('[data-admm-outcome-first]'),
    text=(n,lang)=>n.querySelector('[lang="'+lang+'"]')?.textContent??null;
   return {id:cell.dataset.admmOutcome,passed:cell.dataset.admmOutcomePass,
    status:['ko','en'].map(lang=>text(cell.querySelector('.admm-outcome-status'),lang)),
    values:[...cell.querySelectorAll('[data-admm-outcome-value]')].map(n=>[n.dataset.admmOutcomeValue,n.textContent]),
    first:{text:first.textContent,ko:text(first,'ko'),en:text(first,'en')},
    link:link&&{id:link.dataset.admmOverviewLink,href:link.getAttribute('href'),label:link.getAttribute('aria-label')},
    target:target&&{case:target.closest('[data-admm-case]')?.dataset.admmCase,
      k:target.dataset.admmNative,count:document.querySelectorAll('[id="'+target.id+'"]').length}
   };
  })
 }))
}))'''


def require(condition, message):
    if not condition:
        raise RuntimeError('ADMM overview: '+message)


def validate_overview(record, view):
    parameters = record['parameters']
    families,starts = parameters['families'],parameters['starts']
    fractions,rhos = parameters['lambda_fractions'],parameters['rhos']
    steps = parameters['steps']
    cases = {(c['family'],c['start_name'],c['inputs']['lambda_fraction'],c['inputs']['rho']):c
             for c in record['cases']}
    groups = list(itertools.product(families,starts))
    require(len(view)==len(groups),'matrix/start group coverage differs')
    seen = []
    for group,(family,start) in zip(view,groups):
        require(group['id']==family+'-'+start,'matrix/start order differs')
        sample = cases[family,start,fractions[0],rhos[0]]
        require('A='+str(sample['inputs']['A']) in group['caption']
                and 'z₀='+str(sample['inputs']['z0']) in group['caption'],'actual matrix or start label differs')
        require(group['columns']==['λ/λ_max',*[f'ρ={rho:g}' for rho in rhos]],'penalty columns differ')
        require(len(group['rows'])==len(fractions),'regularization row coverage differs')
        for row,fraction in zip(group['rows'],fractions):
            require(row['fraction']==f'{fraction:g}','regularization label differs')
            require(len(row['cells'])==len(rhos),'penalty cell coverage differs')
            for cell,rho in zip(row['cells'],rhos):
                case = cases[family,start,fraction,rho]
                final = case['rows'][-1]
                require(cell['id']==case['id'],'case is in the wrong grid position')
                seen.append(cell['id'])
                passed = final['stopping_passed']
                require(cell['passed']==str(passed).lower(),'final residual status differs')
                require(cell['status']==(['마지막 통과','Final pass'] if passed else ['마지막 미충족','Final unmet']),
                        'visible final residual label differs')
                values = cell['values']
                require([v[0] for v in values]==['primal_ratio','dual_ratio','gap'],'metric coverage differs')
                expected = [final['primal_norm']/final['eps_primal'],
                            final['dual_norm']/final['eps_dual'],final['stable_gap_z']]
                for (_,text),value in zip(values,expected):
                    actual = float(text)
                    require(math.isfinite(actual) and math.isclose(actual,value,rel_tol=5.1e-7,abs_tol=0),
                            'displayed residual ratio or original gap differs')
                first = case['first_residual_pass']
                if first is None:
                    require(cell['first']['ko']=='예산 안에서 없음' and cell['first']['en']=='none within budget',
                            'absent first pass was invented')
                else:
                    require(cell['first']['text']==str(first) and cell['first']['ko'] is None
                            and cell['first']['en'] is None,'first pass differs')
                link = cell['link']
                require(link and link['id']==case['id'] and link['href']==f'#admm-{case["id"]}-k{steps}',
                        'case link does not reach the final native row')
                require(link['label']==f'{family} · λ/λ_max={fraction:g} · {start} · ρ={rho:g} · k={steps}',
                        'accessible link context differs')
                require(cell['target']==dict(case=case['id'],k=str(steps),count=1),'native link target differs')
    require(len(seen)==len(set(seen))==36,'missing, duplicated or extra outcome')
    return len(seen)
