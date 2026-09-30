"""Capture the complete UI through its documented API (server must be running)."""
import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen

parser=argparse.ArgumentParser()
parser.add_argument("--url",default="http://127.0.0.1:8765")
parser.add_argument("--output",default="artifacts/mosswood.png")
parser.add_argument("--view",choices=["overview","home","follow"],default="overview")
parser.add_argument("--tab",choices=["overview","mind","journal","details"],default="overview")
parser.add_argument("--actor",default="resident_001")
parser.add_argument("--grid",action="store_true")
args=parser.parse_args()
request=Request(args.url+"/api/capture",data=json.dumps({"view":args.view,"tab":args.tab,"actor_id":args.actor,"grid":args.grid}).encode(),headers={"Content-Type":"application/json"},method="POST")
with urlopen(request,timeout=60) as response:
    content=response.read()
target=Path(args.output)
target.parent.mkdir(parents=True,exist_ok=True)
target.write_bytes(content)
print(str(target.resolve()))
