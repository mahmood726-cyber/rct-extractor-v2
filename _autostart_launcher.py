# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
﻿import os, sys, datetime
log_dir = os.path.join(os.environ.get('LOCALAPPDATA', '.'), 'allmeta-rct-extractor')
os.makedirs(log_dir, exist_ok=True)
log = os.path.join(log_dir, 'server.log')
sys.stdout = sys.stderr = open(log, 'a', encoding='utf-8', buffering=1)
print('--- launch', datetime.datetime.now().isoformat(), flush=True)
import uvicorn
uvicorn.run('src.api.main:app', host='127.0.0.1', port=8000, log_level='info')
