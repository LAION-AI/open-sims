"""Read-only HTTP + screenshot acceptance check for the separate running save."""
import json
from pathlib import Path
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
URL='http://127.0.0.1:8769'


def request(path,body=None):
    req=urllib.request.Request(URL+path,data=None if body is None else json.dumps(body).encode(),
        headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=90) as response:
        return response.headers.get_content_type(),response.read()


def main():
    out=ROOT/'artifacts'/'lindenviertel'
    out.mkdir(parents=True,exist_ok=True)
    health=json.loads(request('/api/health')[1])
    geometry=json.loads(request('/api/world')[1])
    state=json.loads(request('/api/state')[1])
    report={'url':URL,'health':health,'clock':state['clock'],'paused':state['paused'],
        'layout':geometry['planning_metadata']['layout_id'],'captures':[]}
    assert health['status']=='ok' and not health['invariants']
    assert report['layout']=='neighborhood-v1'
    for name,options in (
            ('api-school.png',{'building_id':'school','actor_id':'resident_004','tab':'mind'}),
            ('api-relationships.png',{'actor_id':'resident_001','overlay':'relationships','tab':'mind'})):
        mime,data=request('/api/capture',{'width':1440,'height':1000,**options})
        assert mime=='image/png' and data.startswith(b'\x89PNG\r\n\x1a\n')
        (out/name).write_bytes(data)
        report['captures'].append({'file':name,'bytes':len(data),'mime':mime})
    after=json.loads(request('/api/state')[1])
    report['unchanged_clock']=after['clock']==state['clock']
    assert report['unchanged_clock'], 'Read-only capture of a paused world must not step it'
    report['passed']=True
    (out/'api-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
