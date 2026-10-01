"""Render affine-oracle values and an optimal-value bracket from computed rows."""

from __future__ import annotations

from html import escape


def certificate_svg(case: dict, *, bracket: bool = False) -> str:
    rows = case['rows']
    values = [v for r in rows for v in r['certificate']['affine_vertices']]
    values += [r['certificate']['upper'] for r in rows] + [0.]
    lo, hi = min(values), max(values)
    padding = max(hi-lo, 1e-6)*.12
    lo, hi = lo-padding, hi+padding

    def y(value):
        return 306-220*(value-lo)/(hi-lo)

    def text(x, yy, label, size=13, anchor='start'):
        return (f'<text x="{x}" y="{yy:.3f}" font-size="{size}" '
                f'text-anchor="{anchor}" fill="#334155">{escape(label)}</text>')

    def moving(tag, attrs, frames, extra):
        encoded = '|'.join(','.join(f'{v:.3f}' for v in row) for row in frames)
        initial = ' '.join(f'{key}="{v:.3f}"' for key, v in zip(attrs.split(','), frames[0]))
        return (f'<{tag} data-fw-attrs="{attrs}" data-frames="{encoded}" '
                f'{initial} {extra}/>')

    title = 'Bracket the unknown optimal value' if bracket else 'Minimize the affine lower model'
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 520 390" '
             f'data-fw-certificate="{"bracket" if bracket else "vertices"}" '
             f'data-y-min="{lo:.17g}" data-y-max="{hi:.17g}" '
             f'role="img" aria-label="{title}">',
             '<rect width="520" height="390" rx="16" fill="#f5f8fb"/>',
             text(22, 28, title, 17),
             text(22, 52, 'Same objective-value scale throughout this case', 12)]
    for value in (lo+padding, 0., hi-padding):
        yy = y(value)
        parts += [f'<line x1="75" x2="476" y1="{yy:.3f}" y2="{yy:.3f}" '
                  'stroke="#ced9e1" stroke-dasharray="3 4"/>',
                  text(65, yy+4, f'{value:.3g}', 11, 'end')]
    if bracket:
        frames = [(y(r['certificate']['upper']), y(r['certificate']['lower'])) for r in rows]
        parts.append(moving('line', 'y1,y2', frames,
                            'x1="264" x2="264" stroke="#287698" stroke-width="8" '
                            'data-certificate-span=""'))
        for key, color in [('lower', '#b77912'), ('upper', '#287698')]:
            parts.append(moving('circle', 'cy', [(y(r['certificate'][key]),) for r in rows],
                                f'cx="264" r="7" fill="{color}" '
                                f'data-certificate-end="{key}"'))
        parts += [f'<path d="M252,{y(0):.3f} l12,-7 l12,7 l-12,7 Z" fill="#15293f"/>',
                  text(292, y(0)+4, 'known f* = 0', 13),
                  text(22, 337, 'Amber: lower = min ℓ(eᵢ) = f(x) − g_FW', 13),
                  text(22, 361, 'Blue: upper = f(x) · width = g_FW', 13)]
    else:
        for j, xx in enumerate((132, 264, 396)):
            frames = [(y(r['certificate']['affine_vertices'][j]),) for r in rows]
            parts.append(moving('circle', 'cy', frames,
                                f'cx="{xx}" r="5" fill="#64748b" data-affine-vertex="{j}"'))
            parts.append(text(xx, 325, f'e{j+1}', 15, 'middle'))
        frames = [(132+132*r['vertex_index'], y(r['certificate']['lower'])) for r in rows]
        parts.append(moving('circle', 'cx,cy', frames,
                            'r="9" fill="none" stroke="#b77912" stroke-width="3" '
                            'data-affine-oracle=""'))
        parts += [text(22, 353, 'ℓ(v) = f(x) + ∇f(x)ᵀ(v−x)', 14),
                  text(22, 376, 'Amber ring: exact oracle · values may be negative', 12)]
    parts.append('</svg>')
    return ''.join(parts)
