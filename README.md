### Terminal 2 — Model service (GPU) on 7001
```bash
cd /root/gisul_model
source venv/bin/activate
set -a; source backend/.env; set +a
PYTHONPATH=backend uvicorn model_app.main:app --host 0.0.0.0 --port 7001
```
 
### Terminal 3 — Gateway on 7000
```bash
cd /root/gisul_model
source venv/bin/activate
set -a; source backend/.env; set +a
PYTHONPATH=. uvicorn backend.gateway.main:app --host 0.0.0.0 --port 7000
```
 
### Terminal 4 — Frontend on 7002
```bash
cd /root/gisul_model/frontend/web
npm ci
PORT=7002 npm run dev -- -p 7002
```
 
Open:
- `http://127.0.0.1:7002`