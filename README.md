# CampusPrint.

## Project Name

**CampusPrint. — Smart Campus Printing & Queue Management System**

A web-based campus printing platform that allows students to upload documents, select a printer, choose print settings, make a demo payment, and track their print order in real time.

---

## Problem Statement

Students on campus often have to:

- Physically visit printing facilities to submit documents.
- Wait in long and unpredictable queues.
- Spend time finding an available printer.
- Have little visibility into when their documents will be ready.
- Depend on manual order handling by printer operators.
- Face inefficient queue management when small and large print jobs are mixed together.

Printer operators also need a simple way to manage orders, prioritize jobs, and track their progress.

**CampusPrint. solves this by digitizing the complete campus printing workflow.**

---

## Solution Logic

The system follows this workflow:

```text
Student Login
      ↓
Upload Document
      ↓
Select Printer
      ↓
Select Print Settings
      ↓
Select Priority
      ↓
Create Order
      ↓
Demo Payment
      ↓
Smart Queue
      ↓
Queue Position + ETA
      ↓
Printer Admin
      ↓
Pending → Ready → Completed
      ↓
Student Tracks Order
```

### Smart Queue Logic

Each printer has its own independent queue:

```text
Girls Co-op Printer → Girls Queue
Boys Co-op Printer  → Boys Queue
```

The queue uses a deterministic scheduling algorithm — **no AI is used**.

Priority is calculated using:

1. **Urgent priority** — Urgent orders are considered before Green Slot orders.
2. **Aging/Fairness** — older orders receive increasing priority so that large jobs cannot wait indefinitely.
3. **Shortest effective job first** — orders with fewer effective pages are prioritized.
4. **Order time** — earlier orders win if the relevant priority values are tied.

### Aging Mechanism

Every **10 minutes** an order waits, its effective page score is reduced by **5 pages**.

Example:

```text
40-page order

0 minutes  → 40 effective pages
10 minutes → 35 effective pages
20 minutes → 30 effective pages + Fairness Boost
```

After **20 minutes**, the order receives starvation protection.

This combines:

```text
Efficiency + Fairness
```

### ETA Logic

The prototype estimates:

```text
Setup time = 2 minutes/job
Printing time = 1 minute/page
```

Therefore:

```text
Estimated Print Time
= 2 + Total Pages
```

The estimated waiting time is based on the jobs ahead in the same printer queue.

```text
ETA
= Current IST Time
+ Estimated Waiting Time
+ Current Job Print Time
```

The countdown is updated live in the browser.

---

## Features

### Student Features

- Student login using Excel-based credentials.
- Registration Number as login.
- Admission/Roll Number as password.
- Upload PDF, DOC, DOCX, PPT and PPTX files.
- Select printer:
  - Boys Co-op Printer
  - Girls Co-op Printer
- Black & White printing — **₹2/page**.
- Colour printing — **₹10/page**.
- Single-sided / double-sided printing.
- Multiple copies.
- Urgent printing — **₹5 priority fee**.
- Green Slot printing.
- Demo payment window.
- Automatic order generation.
- Live order tracking.
- Queue position.
- Estimated waiting time.
- Estimated print time.
- ETA in **IST**.
- Live countdown of remaining time.

### Admin Features

Separate printer-specific admin accounts:

| Printer | ID | Password |
|---|---|---|
| Boys Co-op | `boyscoop` | `boys123` |
| Girls Co-op | `girlscoop` | `girls123` |

Each admin can view orders for their own printer.

Admin can view:

- Order ID.
- Student roll number.
- Printer.
- Priority.
- Queue position.
- Estimated wait.
- ETA.
- Amount.
- Payment information.
- Order status.

Available statuses:

```text
Pending
Ready
Completed
```

### Backend Features

- FastAPI REST API.
- SQLite database.
- SQLAlchemy ORM.
- Excel student authentication.
- Automatic Excel-to-database import.
- Document upload storage.
- Demo payment processing.
- Printer-specific queues.
- Smart queue scheduling.
- Aging/fairness mechanism.
- Live IST time endpoint.
- ETA calculation.
- Order status management.

### Payment

The current version uses a **demo payment system**.

No real payment is processed.

There is:

```text
No Razorpay
No payment API
No API key
No real money transfer
```

---

## Running Commands

### 1. Open Terminal

Open Terminal on macOS.

### 2. Navigate to the backend

If the project is in Downloads:

```bash
cd ~/Downloads/CampusPrint_README_Formatted/backend
```

If you extracted the main CampusPrint project instead, use its corresponding `backend` folder.

Check the folder:

```bash
ls
```

You should see:

```text
main.py
requirements.txt
use in code.xlsx
uploads
```

### 3. Create a virtual environment

```bash
python3 -m venv .venv
```

### 4. Activate the environment

```bash
source .venv/bin/activate
```

### 5. Install dependencies

```bash
pip install -r requirements.txt
```

### 6. Start the backend

```bash
uvicorn main:app --reload
```

The backend should start at:

```text
http://127.0.0.1:8000
```

### 7. Check the backend

Open:

```text
http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "ok"
}
```

### 8. Open API documentation

```text
http://127.0.0.1:8000/docs
```

### 9. Open the frontend

Keep the backend Terminal running.

Then open:

```text
frontend/index.html
```

in your browser.

---

## Quick Demo Commands

### Start backend

```bash
cd ~/Downloads/CampusPrint_SmartQueue_Aging/backend
source .venv/bin/activate
uvicorn main:app --reload
```

### Open frontend

```text
frontend/index.html
```

### Admin accounts

```text
Boys Co-op
ID: boyscoop
Password: boys123
```

```text
Girls Co-op
ID: girlscoop
Password: girls123
```

---

## Technology Stack

```text
Frontend:
HTML + CSS + JavaScript

Backend:
Python + FastAPI + Uvicorn

Database:
SQLite + SQLAlchemy

Student Data:
Excel + Pandas + OpenPyXL
```

**Queue management is algorithmic and does not use AI.**
