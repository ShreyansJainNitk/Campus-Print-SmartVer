# CampusPrint. — Smart Queue Management

Deterministic queue management, no AI.

### Queue priority
Each printer has its own queue:
1. Urgent first
2. Earlier order placement first (FCFS)
3. Fewer total pages first when the above are tied

### ETA
Prototype calculation:
- 2-minute setup per job
- 1 minute per printed page
- Estimated wait = total estimated time of orders ahead
- ETA = current backend time + wait + this job's estimated print time

### Student tracking
Shows queue position, estimated wait, estimated ready time, and estimated print time for Pending orders.

### Admin dashboard
Shows queue position, estimated wait and ETA for Pending orders.

The UI refreshes queue data every 30 seconds.

### Statuses
Pending, Ready, Completed only.

### Payment
Demo payment only; no real gateway.

### Student authentication
Registration Number = Excel IRIS Reference No.
Password = Excel Admission Number.

### Mac
```bash
cd ~/Downloads/CampusPrint_SmartQueue/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```
Then open `frontend/index.html`.

Queue APIs:
`GET /api/queue/Girls%20Co-op%20Printer`
`GET /api/queue/Boys%20Co-op%20Printer`


## IST live ETA

ETA timestamps are now returned in **India Standard Time (Asia/Kolkata, UTC+05:30)**.

The browser keeps the displayed **time remaining live every second** using the ETA timestamp. Queue data is refreshed from the backend every 30 seconds, while the countdown itself updates every second.

Backend current-time endpoint:

```text
GET /api/time/ist
```

This returns the current IST time and Unix timestamp, which can be used to synchronize the UI.

The ETA remains an estimate based on:
- 2-minute setup per job
- 1 minute per printed page
- printer-specific queue
- Urgent → FCFS → fewer pages priority


## Admin login
Boys Co-op:
- ID: `boyscoop`
- Password: `boys123`

Girls Co-op:
- ID: `girlscoop`
- Password: `girls123`

If you previously ran an older copy of the backend, stop it with Ctrl+C and start the backend from THIS folder so the corrected admin credentials are loaded.


## Updated Smart Queue Algorithm — Aging + Shortest Job First

Within each printer, the queue now uses:

1. **Urgent before Green Slot**
2. **Starvation protection:** an order waiting 20+ minutes gets a fairness boost
3. **Shortest effective job first:** fewer pages get priority
4. **Aging:** every 10 minutes of waiting reduces the job's effective page score by 5 pages
5. Earlier order time is used as the final tie-breaker

Example:

A 40-page Green Slot order starts with an effective score of 40.

After 10 minutes:
`40 - 5 = 35`

After 20 minutes:
`40 - 10 = 30`

At 20+ minutes it is marked **Fairness Boost** and is protected from being starved by newer jobs.

This is deterministic scheduling — **no AI is used**.

ETA remains live in IST. The browser updates the countdown every second and refreshes queue data every 30 seconds.

Terminal Commands
cd ~/Downloads/CampusPrint_SmartQueue_Aging/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload

http://127.0.0.1:8000/health?utm_source=chatgpt.com- should get status ok
http://127.0.0.1:8000/api/student/count?utm_source=chatgpt.com
{
  "count": 1064
}