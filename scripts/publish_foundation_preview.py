"""Publish only small review images to a dedicated branch, never to Pages."""
import base64
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path


def main():
    repo=os.environ['GITHUB_REPOSITORY']
    source=os.environ['GITHUB_SHA']
    assert repo=='chocoemong17/chainbench'
    assert os.environ['GITHUB_REF']=='refs/heads/feat/learning-foundations'
    assert re.fullmatch('[a-f0-9]{40}',source)
    base='https://api.github.com/repos/'+repo
    def api(path,body=None,method=None):
        data=None if body is None else json.dumps(body).encode()
        req=urllib.request.Request(base+path,data=data,method=method,headers={
            'Authorization':'Bearer '+os.environ['GH_TOKEN'],
            'Accept':'application/vnd.github+json','Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=60) as response:
            return json.load(response)
    branch='study/foundations-polish'
    try:
        parent=api('/git/ref/heads/'+branch)['object']['sha']
    except urllib.error.HTTPError as exc:
        if exc.code!=404:
            raise
        parent=source
    tree=[]
    for directory in (Path('foundation-preview'),Path('foundation-browser')):
        for path in sorted(directory.glob('*')):
            if path.suffix not in ('.jpg','.png','.json') or path.is_symlink():
                continue
            raw=path.read_bytes()
            assert len(raw)<4_000_000
            blob=api('/git/blobs',dict(content=base64.b64encode(raw).decode(),encoding='base64'))
            tree.append(dict(path='docs/reviews/foundations-polish/'+directory.name+'/'+path.name,
                             mode='100644',type='blob',sha=blob['sha']))
    assert tree
    metadata=json.dumps(dict(source=source,run=os.environ['GITHUB_RUN_ID'],files=len(tree)),indent=2)+'\n'
    tree.append(dict(path='docs/reviews/foundations-polish/source.json',mode='100644',type='blob',content=metadata))
    # Review files are additive on the exact feature source, with a separate history.
    source_tree=api('/git/commits/'+source)['tree']['sha']
    created=api('/git/trees',dict(base_tree=source_tree,tree=tree))
    commit=api('/git/commits',dict(message='Review rendered foundations for '+source[:12],tree=created['sha'],parents=[parent]))
    # Ensure the feature source did not move while the rendering ran.
    assert api('/git/ref/heads/feat/learning-foundations')['object']['sha']==source
    if parent==source:
        api('/git/refs',dict(ref='refs/heads/'+branch,sha=commit['sha']))
    else:
        api('/git/refs/heads/'+branch,dict(sha=commit['sha'],force=False),method='PATCH')
    print(json.dumps(dict(review_commit=commit['sha'],source=source,files=len(tree))),flush=True)


if __name__=='__main__':
    main()
