"""Import user-owned course sources; no third-party dataset ships with the repo."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from chemtutor.knowledge_index import KnowledgeIndex

def main():
 p=argparse.ArgumentParser();p.add_argument('file',type=Path);p.add_argument('--course',required=True);p.add_argument('--version',required=True);a=p.parse_args()
 records=json.loads(a.file.read_text())
 if not isinstance(records,list):p.error('资料文件应为JSON数组')
 print(json.dumps(KnowledgeIndex(ROOT/'var/knowledge.sqlite3').ingest(a.course,a.version,records),ensure_ascii=False))
if __name__=='__main__':main()
