"""Digest mã nguồn ổn định; không băm secret, log, artifact hay báo cáo."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

def build(root):
    def git(*args): return subprocess.check_output(["git","-C",str(root),*args])
    paths=set(git("ls-files","-z").decode().split("\0"))|set(git("ls-files","--others","--exclude-standard","-z").decode().split("\0"))
    configs={".env.example","docker-compose.yml","pytest.ini","render.yaml","vercel.json",".gitignore",".python-version"}
    files=[];deleted=[]
    for name in sorted(paths):
        path=Path(name)
        if not name or not (name.startswith(("backend/","frontend/",".github/")) or name in configs): continue
        if set(path.parts)&{"node_modules","dist","__pycache__",".pytest_cache","test-results","playwright-report"}: continue
        if path.name.startswith(".env") and path.name!=".env.example": continue
        if path.suffix in {".log",".db",".sqlite",".sqlite3",".pyc",".tsbuildinfo"}: continue
        source=root/name
        if source.is_file(): files.append({"path":name,"sha256":hashlib.sha256(source.read_bytes()).hexdigest()})
        else: deleted.append(name)
    payload={"head":git("rev-parse","HEAD").decode().strip(),"files":files,"deleted":deleted}
    payload["digest"]=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",", ":")).encode()).hexdigest()
    return payload

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--output",required=True);args=parser.parse_args()
    data=build(Path(__file__).resolve().parents[2]);Path(args.output).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    print(data["digest"],len(data["files"]),"source files")
