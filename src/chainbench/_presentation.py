"""Shared, dependency-free typography and readable mathematical scripts."""

CSS = """
:root{--ink:#152d30;--muted:#506669;--line:#dce4e3;--blue:#087e80;--cream:#fafbf8}
body{background:#f7f9f7;color:var(--ink)}main{max-width:1240px;padding-top:24px}
header{background:#123a3e;border-radius:8px;padding:40px;box-shadow:none}
header:after{display:none}h1,h2{font-family:ui-sans-serif,system-ui,-apple-system,'Segoe UI',sans-serif;letter-spacing:-.04em}
h1{font-size:clamp(32px,4.5vw,54px);line-height:1.12}h2{font-size:clamp(24px,3vw,32px)}
.eyebrow{color:#9bd7cc}section,.panel{border-radius:8px;padding:28px;box-shadow:none}
.card{border-radius:8px;box-shadow:none;background:white}.card:before{background:#087e80;height:2px}
button,input,select{border-radius:6px}button{min-height:44px}a{color:#087779}
.formula{font-family:'Cambria Math','STIX Two Math','Noto Sans Math',Georgia,serif;
font-size:18px;line-height:2.1;background:#f4f7f5;border:1px solid #dae4e0;border-radius:6px;
white-space:pre;overflow-x:auto;overflow-wrap:normal;word-break:normal;max-width:100%}
.formula sub,.formula sup,.method-flow code sub,.method-flow code sup{font-size:.72em;line-height:0}
.formula sub{vertical-align:-.3em}.formula sup{vertical-align:.6em}
.method-flow code{font-family:'Cambria Math',Georgia,serif;font-size:16px;line-height:1.9;
overflow-x:auto;white-space:pre;overflow-wrap:normal}.formula math{font-size:1.1em}
.pairs>*,.deep-grid>*,.visual-grid>*{min-width:0}
.trajectory-player{background:#123a3e;border-radius:8px}
input[type=range]{accent-color:#0d8e89;min-height:44px;cursor:ew-resize;touch-action:pan-y}
.math-line{display:block;white-space:nowrap}.math-line math{font-family:math,'Cambria Math',serif}
@media(max-width:760px){header{padding:26px 20px}section,.panel{padding:18px}.formula{font-size:16px;padding:14px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*:before,*:after{animation:none!important;transition:none!important}}
"""

# Work only on authored explanation nodes, never numerical JSON, SVG labels or code
# commands. Real sub/sup elements avoid sparse Unicode subscript font coverage.
SCRIPT = r"""
(()=>{
 const subs='₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ',
       subplain='0123456789+-=()aehijklmnoprstuvx',
       sups='⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ᵀᵏ',supplain='0123456789+-=()Tk';
 const convert=text=>{
  const fragment=document.createDocumentFragment();let pos=0;
  const pattern=/[₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ]+|[⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ᵀᵏ]+/gu;
  for(const match of text.matchAll(pattern)){
   fragment.append(document.createTextNode(text.slice(pos,match.index)));
   const isSub=subs.includes(match[0][0]),el=document.createElement(isSub?'sub':'sup');
   const alphabet=isSub?subs:sups,plain=isSub?subplain:supplain;
   el.textContent=[...match[0]].map(c=>plain[alphabet.indexOf(c)]).join('');
   fragment.append(el);pos=match.index+match[0].length;
  }
  fragment.append(document.createTextNode(text.slice(pos)));return fragment;
 };
 document.querySelectorAll('.formula,.method-flow code,.bt-flows code').forEach(block=>{
  if(block.textContent.trim().startsWith('chainbench '))return;
  const walker=document.createTreeWalker(block,NodeFilter.SHOW_TEXT);const nodes=[];
  while(walker.nextNode())if(!walker.currentNode.parentElement.closest('math,sub,sup'))nodes.push(walker.currentNode);
  nodes.forEach(node=>node.replaceWith(convert(node.textContent)));
 });
})();
"""
