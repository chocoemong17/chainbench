import importlib.util
import json
from html import escape
from pathlib import Path

import pytest


def smoke_module():
    spec = importlib.util.spec_from_file_location('document_smoke',
        Path(__file__).resolve().parents[1]/'scripts/smoke_workflows.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_links_and_evidence_keep_html_entity_and_raw_text_semantics():
    module = smoke_module()
    record = {'label':'x < y & "quoted"', 'literal':'<a id="fake" href="missing.html">',
              'values':[None, 0., -1e-12]}
    text = ('<main id="real"><a href="index.html#x&amp;y">return</a>'
            '<script>const fake="<a id=\'script\' href=\'absent.html\'>";</script>'
            '<!-- <a id="comment" href="absent.html"> -->'
            '<pre>{"unrelated":true}</pre><PRE ID="chainbench-evidence">'
            +escape(json.dumps(record))+'</PRE></main><a href="#real">back</a>')
    document = module.EvidenceDocument(text)
    assert document.take_record() == module.extract_record(text) == record
    assert document.ids == {'real', 'chainbench-evidence'}
    assert document.links == ['index.html#x&y', '#real']
    assert not document.chunks  # Avoid retaining both decoded data and raw JSON.


@pytest.mark.parametrize('text', [
    '<pre>{"unrelated":true}</pre>',
    '<script>"<pre id=\'chainbench-evidence\'>{}</pre>"</script>',
    '<pre id="chainbench-evidence">{"truncated":</pre>',
    '<pre id="chainbench-evidence">{}</pre><pre id="chainbench-evidence">{}</pre>',
    '<pre id="chainbench-evidence"></pre><pre id="chainbench-evidence">{}</pre>',
    '<pre id="chainbench-evidence">{}</pre><pre id="chainbench-evidence"></pre>',
    '<pre id="chainbench-evidence">{"split":</pre><pre id="chainbench-evidence">1}</pre>',
    '<div id="chainbench-evidence"></div><pre id="chainbench-evidence">{}</pre>',
    '<script id="chainbench-evidence">{"other":1}</script><pre id="chainbench-evidence">{}</pre>',
    '<pre id="other" id="chainbench-evidence">{}</pre>',
    '<div id="chainbench-evidence" id="other"></div><pre id="chainbench-evidence">{}</pre>',
])
def test_absent_malformed_or_multiple_evidence_never_becomes_a_record(text):
    with pytest.raises(json.JSONDecodeError):
        smoke_module().extract_record(text)
