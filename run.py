"""Run the neighborhood, or evaluate the exact same engine without a browser."""
import argparse
import json
from pathlib import Path
import threading
import time
import webbrowser


def main():
    parser=argparse.ArgumentParser(description="Mosswood · Procedural Living World")
    parser.add_argument("--port",type=int,default=8765)
    parser.add_argument("--seed",type=int,default=42)
    parser.add_argument('--layout',choices=['legacy','neighborhood-v1'],default='legacy',help='Layout for a new database; saved layouts are restored exactly.')
    parser.add_argument('--paused',action='store_true',help='Open the world paused for inspection.')
    parser.add_argument("--database",default=str(Path(__file__).parent/"data"/"mosswood.sqlite3"))
    parser.add_argument("--no-browser",action="store_true")
    parser.add_argument("--headless",action="store_true")
    parser.add_argument("--hours",type=float,default=24)
    args=parser.parse_args()
    if args.headless:
        from living_world.engine import World
        w=World(args.seed,layout=args.layout)
        started=time.perf_counter()
        w.advance(round(args.hours*3600))
        result={"hours":args.hours,"seed":args.seed,"elapsed_seconds":round(time.perf_counter()-started,3),"invariants":w.invariants(),"replay_matches":w.store.replay()==w.canonical_state(),"metrics":w.snapshot()["metrics"],"activities":w.snapshot()["activity_counts"]}
        print(json.dumps(result,indent=2))
        w.close()
        raise SystemExit(1 if result["invariants"] or not result["replay_matches"] else 0)
    import uvicorn
    from living_world.server import create_app
    if not args.no_browser:
        threading.Timer(1.5,lambda:webbrowser.open(f"http://127.0.0.1:{args.port}")).start()
    uvicorn.run(create_app(args.database,args.seed,args.port,layout=args.layout,paused=args.paused),host="127.0.0.1",port=args.port,log_level="warning")


if __name__=="__main__":
    main()
