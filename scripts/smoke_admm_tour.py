"""Bind a tour preview to its named report, and require its comparison links."""
import base64
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser


class Elements(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.links = []
        self.images = []
        self.card = None
        self.flows = []
        self.meanings = []
        self.feed(text)

    def handle_starttag(self, tag, attributes):
        a = dict(attributes)
        if tag=='a':
            self.links.append(a)
            self.card = a.get('href') if 'tour-card' in a.get('class','').split() else None
        if tag=='img' and self.card=='admm.html':
            self.images.append(a.get('src'))
        if 'data-split-method' in a:
            self.flows.append(a['data-split-method'])
        if 'data-split-meaning' in a:
            self.meanings.append(a['data-split-meaning'])

    def handle_endtag(self, tag):
        if tag=='a':
            self.card = None


def validate_admm_tour_presentation(folder):
    index = (folder/'index.html').read_text(encoding='utf8')
    report = (folder/'admm.html').read_text(encoding='utf8')
    parsed = Elements(index)
    if (parsed.flows!=['proximal','admm']
            or parsed.meanings!=['y','z','threshold','objective','dual geometry']
            or len(parsed.images)!=1):
        raise RuntimeError('ADMM tour comparison coverage differs')
    case = re.search(r'<details\b[^>]*data-admm-case="coupled-lambda0.1-zero-rho1"[^>]*>(.*?)(?=<details\b[^>]*data-admm-case=|\Z)',report,flags=re.S)
    surface = re.search(r'<svg\b[^>]*data-admm-primal="surface".*?</svg>',case[1],flags=re.S) if case else None
    prefix = 'data:image/svg+xml;base64,'
    if surface is None or not parsed.images[0].startswith(prefix):
        raise RuntimeError('ADMM tour preview source differs')
    try:
        raw = base64.b64decode(parsed.images[0][len(prefix):],validate=True).decode('utf8')
        element = ET.fromstring(raw)
    except (ValueError,UnicodeError,ET.ParseError) as exc:
        raise RuntimeError('ADMM tour preview is not a standalone SVG') from exc
    if raw!=surface[0] or element.tag!='{http://www.w3.org/2000/svg}svg':
        raise RuntimeError('ADMM tour preview differs from its actual source surface')
    for name,target in (('proximal.html','admm.html'),('admm.html','proximal.html'),('atlas.html','admm.html')):
        links = Elements((folder/name).read_text(encoding='utf8')).links
        if ([a.get('href') for a in links if 'data-tour-splitting' in a]!=[target]
                or [a.get('href') for a in links if 'data-tour-splitting-guide' in a]!=['index.html#variable-splitting']):
            raise RuntimeError('ADMM tour comparison navigation differs')
