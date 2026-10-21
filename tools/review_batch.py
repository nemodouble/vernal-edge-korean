"""Print review batches without relying on the terminal's output encoding."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding='utf-8')
parser=argparse.ArgumentParser()
parser.add_argument('start',type=int);parser.add_argument('end',type=int)
parser.add_argument('--paired',action='store_true')
args=parser.parse_args()
rows=json.loads((ROOT/'translation/worktable.json').read_text(encoding='utf-8'))
for row in rows[args.start:args.end]:
    if args.paired:print(f"{row['id']} {row['english']} → {row['korean']}")
    else:print(f"{row['id']} {row['korean']}")
