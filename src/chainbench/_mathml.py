"""Authored MathML for the learning atlas's source-mapped bounds.

This is presentation only. No formula is parsed or evaluated as a solver.
"""
from html import escape


def tag(name, *children):
    return '<' + name + '>' + ''.join(children) + '</' + name + '>'


def atom(value):
    return tag('mn' if str(value).isdigit() else 'mi', escape(str(value)))


def row(*children):
    return tag('mrow', *children)


def op(value):
    return tag('mo', escape(value))


def sub(value, index):
    return tag('msub', atom(value), atom(index))


def power(value, exponent):
    return tag('msup', value, atom(exponent))


def fraction(top, bottom):
    return tag('mfrac', top, bottom)


def sqrt(value):
    return tag('msqrt', atom(value))


def parens(value):
    return row(op('('), value, op(')'))


def math_line(content, label):
    return ('<span class="math-line"><math xmlns="http://www.w3.org/1998/Math/MathML" '
            'aria-label="' + escape(label, quote=True) + '">' + content + '</math></span>')


def bound_math(slug, original):
    gap = row(atom('f'), parens(sub('x', 'k')), op('−'), power(atom('f'), '*'))
    composite = row(atom('F'), parens(sub('x', 'k')), op('−'), power(atom('F'), '*'))
    lr2 = row(atom('L'), power(atom('R'), '2'))
    kp1 = row(atom('k'), op('+'), atom('1'))
    norm = lambda index: row(op('‖'), sub('x', index), op('−'), power(atom('x'), '*'), op('‖'))  # noqa: E731
    if slug == 'gd-baseline':
        content = row(gap, op('≤'), fraction(lr2, row(atom('2'), atom('k'))))
    elif slug in ('nesterov-1983', 'beck-teboulle-2009'):
        content = row(composite if slug == 'beck-teboulle-2009' else gap, op('≤'),
                      fraction(row(atom('2'), lr2), power(parens(kp1), '2')))
    elif slug == 'polyak-1964':
        content = row(atom('ρ'), op('='), fraction(row(sqrt('L'), op('−'), sqrt('μ')),
                                                  row(sqrt('L'), op('+'), sqrt('μ'))))
    elif slug == 'hestenes-stiefel-1952':
        ratio = fraction(row(sqrt('κ'), op('−'), atom('1')), row(sqrt('κ'), op('+'), atom('1')))
        content = row(tag('msub', norm('k'), atom('Q')), op('≤'), atom('2'),
                      power(parens(ratio), 'k'), tag('msub', norm('0'), atom('Q')))
    elif slug == 'jaggi-2013':
        content = row(gap, op('≤'), fraction(row(atom('2'), sub('C', 'f')),
                                            row(atom('k'), op('+'), atom('2'))),
                      op(','), atom('k'), op('≥'), atom('1'))
    elif slug == 'rockafellar-1976':
        # The authored statement uses k+1 against k, with Euclidean distance.
        content = row(tag('msub', row(op('‖'), tag('msub', atom('x'), kp1), op('−'),
                                    power(atom('x'), '*'), op('‖')), atom('2')), op('≤'),
                      fraction(tag('msub', norm('k'), atom('2')),
                               row(atom('1'), op('+'), atom('c'), atom('μ'))))
    else:
        return escape(original)
    return math_line(content, original)
