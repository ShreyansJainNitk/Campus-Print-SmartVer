from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional
import hashlib
import shutil
from zoneinfo import ZoneInfo

import pandas as pd
from fastapi import FastAPI, Depends, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
EXCEL_FILE = BASE_DIR / "use in code.xlsx"

engine = create_engine(f"sqlite:///{BASE_DIR / 'campusprint.db'}",
                       connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True)
    registration_number = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    order_code = Column(String, unique=True, index=True, nullable=False)
    registration_number = Column(String, nullable=False)
    roll_number = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    stored_filename = Column(String, nullable=False)
    printer = Column(String, nullable=False)
    print_type = Column(String, nullable=False)
    sides = Column(String, nullable=False)
    pages = Column(Integer, nullable=False)
    copies = Column(Integer, nullable=False)
    total_pages = Column(Integer, nullable=False)
    priority_slot = Column(String, nullable=False)
    print_cost = Column(Float, nullable=False)
    priority_fee = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    payment_status = Column(String, nullable=False, default="unpaid")
    payment_method = Column(String, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    status = Column(String, nullable=False, default="Pending")
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="CampusPrint. API", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

PRINTERS = {"Girls Co-op Printer", "Boys Co-op Printer"}
STATUSES = {"Pending", "Ready", "Completed"}
PRICE = {"bw": 2, "color": 10}
URGENT_FEE = 5
ADMIN_CREDENTIALS = {
    "boyscoop": {"password": "boys123", "printer": "Boys Co-op Printer"},
    "girlscoop": {"password": "girls123", "printer": "Girls Co-op Printer"},
}


# Deterministic queue settings — no AI.
# A job is estimated at 1 minute per printed page, with a 2-minute setup buffer.
SETUP_MINUTES = 2
MINUTES_PER_PAGE = 1
IST = ZoneInfo("Asia/Kolkata")

def now_ist():
    return datetime.now(IST)

def to_ist(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        # SQLite stores our UTC naive timestamps.
        return dt.replace(tzinfo=timezone.utc).astimezone(IST)
    return dt.astimezone(IST)

# Smart Queue settings — deterministic, no AI.
SETUP_MINUTES = 2
MINUTES_PER_PAGE = 1

# Aging/fairness:
# A normal (Green Slot) job receives an aging bonus as it waits.
# Every AGING_STEP_MINUTES of waiting reduces its effective page score by
# AGING_PAGE_BONUS pages. Once a job reaches MAX_WAIT_MINUTES, it is promoted
# ahead of newer jobs, preventing starvation.
AGING_STEP_MINUTES = 10
AGING_PAGE_BONUS = 5
MAX_WAIT_MINUTES = 20

# Urgent jobs always stay ahead of Green Slot jobs. Within each priority class,
# the effective page count is used: shorter jobs first, with waiting time
# gradually making older jobs more competitive.
def effective_page_score(order, now=None):
    now = now or datetime.now(timezone.utc)
    created = order.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    waited_minutes = max(0, (now - created).total_seconds() / 60)
    aging_bonus = int(waited_minutes // AGING_STEP_MINUTES) * AGING_PAGE_BONUS
    return max(0, order.total_pages - aging_bonus)

def priority_key(order, now=None):
    now = now or datetime.now(timezone.utc)
    created = order.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    waited_minutes = max(0, (now - created).total_seconds() / 60)

    # A job waiting >= MAX_WAIT_MINUTES is protected from starvation.
    starvation_protected = waited_minutes >= MAX_WAIT_MINUTES
    urgent_rank = 0 if order.priority_slot == "Urgent" else 1

    # Protected jobs come before newer jobs in the same urgency class.
    protection_rank = 0 if starvation_protected else 1

    return (
        urgent_rank,
        protection_rank,
        effective_page_score(order, now),
        created,
        order.id,
    )

def queue_for_printer(db, printer):
    return db.query(Order).filter(
        Order.printer == printer,
        Order.status == "Pending",
        Order.payment_status == "paid"
    ).all()

def build_queue(db, printer):
    now_utc = datetime.now(timezone.utc)
    orders = sorted(queue_for_printer(db, printer), key=lambda o: priority_key(o, now_utc))
    result = []
    minutes_before = 0

    for position, order in enumerate(orders, start=1):
        duration = SETUP_MINUTES + (order.total_pages * MINUTES_PER_PAGE)
        created = order.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        waited_minutes = max(0, (now_utc - created).total_seconds() / 60)
        aging_steps = int(waited_minutes // AGING_STEP_MINUTES)
        aging_bonus = aging_steps * AGING_PAGE_BONUS
        starvation_protected = waited_minutes >= MAX_WAIT_MINUTES
        eta = now_ist() + timedelta(minutes=minutes_before + duration)

        result.append({
            "queuePosition": position,
            "orderId": order.order_code,
            "registrationNumber": order.registration_number,
            "printer": order.printer,
            "priority": order.priority_slot,
            "totalPages": order.total_pages,
            "effectivePageScore": effective_page_score(order, now_utc),
            "agingSteps": aging_steps,
            "agingBonusPages": aging_bonus,
            "waitedMinutes": round(waited_minutes, 1),
            "starvationProtected": starvation_protected,
            "estimatedPrintMinutes": duration,
            "minutesAhead": minutes_before,
            "estimatedWaitMinutes": minutes_before,
            "etaUtc": eta.isoformat(),
            "createdAt": to_ist(order.created_at).isoformat() if order.created_at else None,
            "status": order.status,
        })
        minutes_before += duration

    return result

def get_queue_item(db, order):
    if order.status != "Pending" or order.payment_status != "paid":
        return {
            "queuePosition": None, "minutesAhead": 0, "estimatedWaitMinutes": 0,
            "estimatedPrintMinutes": SETUP_MINUTES + order.total_pages * MINUTES_PER_PAGE,
            "etaUtc": None, "effectivePageScore": order.total_pages,
            "agingSteps": 0, "agingBonusPages": 0, "waitedMinutes": 0,
            "starvationProtected": False
        }

    queue = build_queue(db, order.printer)
    for item in queue:
        if item["orderId"] == order.order_code:
            return {
                "queuePosition": item["queuePosition"],
                "minutesAhead": item["minutesAhead"],
                "estimatedWaitMinutes": item["estimatedWaitMinutes"],
                "estimatedPrintMinutes": item["estimatedPrintMinutes"],
                "etaUtc": item["etaUtc"],
                "effectivePageScore": item["effectivePageScore"],
                "agingSteps": item["agingSteps"],
                "agingBonusPages": item["agingBonusPages"],
                "waitedMinutes": item["waitedMinutes"],
                "starvationProtected": item["starvationProtected"],
            }

    return {"queuePosition": None, "minutesAhead": 0, "estimatedWaitMinutes": 0,
            "estimatedPrintMinutes": 0, "etaUtc": None, "effectivePageScore": None,
            "agingSteps": 0, "agingBonusPages": 0, "waitedMinutes": 0,
            "starvationProtected": False}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def hash_password(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def order_json(o, db=None):
    q = get_queue_item(db, o) if db else {
        "queuePosition": None, "minutesAhead": 0, "estimatedWaitMinutes": 0,
        "estimatedPrintMinutes": 0, "etaUtc": None
    }
    return {
        "id": o.order_code,
        "databaseId": o.id,
        "registrationNumber": o.registration_number,
        "rollNumber": o.roll_number,
        "filename": o.filename,
        "printer": o.printer,
        "printType": o.print_type,
        "sides": o.sides,
        "pages": o.pages,
        "copies": o.copies,
        "totalPages": o.total_pages,
        "slot": o.priority_slot,
        "printCost": o.print_cost,
        "priorityFee": o.priority_fee,
        "amount": o.amount,
        "paymentStatus": o.payment_status,
        "paymentMethod": o.payment_method,
        "paidAt": to_ist(o.paid_at).isoformat() if o.paid_at else None,
        "status": o.status,
        "effectivePageScore": q.get("effectivePageScore"),
        "agingSteps": q.get("agingSteps"),
        "agingBonusPages": q.get("agingBonusPages"),
        "waitedMinutes": q.get("waitedMinutes"),
        "starvationProtected": q.get("starvationProtected"),
        "createdAt": to_ist(o.created_at).isoformat() if o.created_at else None,
        **q,
    }

def import_students_from_excel():
    if not EXCEL_FILE.exists():
        print("WARNING: use in code.xlsx not found.")
        return
    workbook = pd.ExcelFile(EXCEL_FILE)
    sheet = "Group-wise List" if "Group-wise List" in workbook.sheet_names else workbook.sheet_names[0]
    data = pd.read_excel(EXCEL_FILE, sheet_name=sheet)
    columns = {str(c).strip().lower(): c for c in data.columns}
    iris = next((c for k, c in columns.items() if "iris" in k and "reference" in k), None)
    admission = next((c for k, c in columns.items() if "admission" in k), None)
    if iris is None or admission is None:
        raise RuntimeError(f"Required Excel columns not found: {list(data.columns)}")

    db = SessionLocal()
    try:
        count = 0
        for _, row in data[[iris, admission]].dropna().iterrows():
            reg = str(row[iris]).strip()
            password = str(row[admission]).strip()
            if reg.endswith(".0"): reg = reg[:-2]
            if password.endswith(".0"): password = password[:-2]
            if not reg or not password: continue
            student = db.query(Student).filter(Student.registration_number == reg).first()
            if student:
                student.password_hash = hash_password(password)
            else:
                db.add(Student(registration_number=reg, password_hash=hash_password(password)))
            count += 1
        db.commit()
        print(f"Imported/updated {count} student credentials from Excel.")
    finally:
        db.close()

@app.on_event("startup")
def startup():
    import_students_from_excel()

@app.get("/")
def root():
    return {"application": "CampusPrint.", "status": "running",
            "queue_management": "deterministic", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/time/ist")
def current_ist_time():
    t = now_ist()
    return {"timezone":"Asia/Kolkata","time":t.isoformat(),"unixMs":int(t.timestamp()*1000)}

@app.get("/api/student/count")
def student_count(db: Session = Depends(get_db)):
    return {"count": db.query(Student).count()}

@app.post("/api/student/login")
def student_login(registration_number: str = Form(...), password: str = Form(...),
                  db: Session = Depends(get_db)):
    s = db.query(Student).filter(Student.registration_number == registration_number.strip()).first()
    if not s or s.password_hash != hash_password(password.strip()):
        raise HTTPException(401, "Invalid registration number or roll/admission number.")
    return {"success": True, "registrationNumber": s.registration_number,
            "rollNumber": password.strip()}

@app.post("/api/admin/login")
def admin_login(admin_id: str = Form(...), password: str = Form(...)):
    admin_id = admin_id.strip().lower()
    password = password.strip()
    account = ADMIN_CREDENTIALS.get(admin_id)
    if not account or account["password"] != password:
        raise HTTPException(401, "Invalid printer ID or password.")
    return {
        "success": True,
        "adminId": admin_id,
        "printer": account["printer"],
    }

@app.post("/api/orders")
def create_order(registration_number: str = Form(...), roll_number: str = Form(...),
                 printer: str = Form(...), print_type: str = Form("bw"),
                 sides: str = Form("single"), pages: int = Form(...),
                 copies: int = Form(1), priority_slot: str = Form(...),
                 document: UploadFile = File(...), db: Session = Depends(get_db)):
    s = db.query(Student).filter(Student.registration_number == registration_number.strip()).first()
    if not s or s.password_hash != hash_password(roll_number.strip()):
        raise HTTPException(401, "Student credentials are invalid.")
    if printer not in PRINTERS: raise HTTPException(400, "Invalid printer.")
    if print_type not in PRICE: raise HTTPException(400, "Invalid print type.")
    if sides not in {"single", "double"}: raise HTTPException(400, "Invalid sides option.")
    if priority_slot not in {"Urgent", "Green Slot"}: raise HTTPException(400, "Invalid priority slot.")
    if pages < 1 or copies < 1: raise HTTPException(400, "Pages and copies must be at least 1.")

    filename = Path(document.filename or "").name
    if Path(filename).suffix.lower() not in {".pdf", ".doc", ".docx", ".ppt", ".pptx"}:
        raise HTTPException(400, "Unsupported file type.")

    total = pages * copies
    print_cost = total * PRICE[print_type]
    fee = URGENT_FEE if priority_slot == "Urgent" else 0
    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    stored = f"{stamp}_{filename}"
    with (UPLOAD_DIR / stored).open("wb") as f:
        shutil.copyfileobj(document.file, f)

    last = db.query(Order).order_by(Order.id.desc()).first()
    number = (last.id + 1001) if last else 1001
    order = Order(
        order_code=f"CP{number}",
        registration_number=registration_number.strip(),
        roll_number=roll_number.strip(),
        filename=filename, stored_filename=stored, printer=printer,
        print_type=print_type, sides=sides, pages=pages, copies=copies,
        total_pages=total, priority_slot=priority_slot, print_cost=print_cost,
        priority_fee=fee, amount=print_cost + fee, status="Pending"
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order_json(order, db)

@app.post("/api/orders/{code}/payment/demo")
def demo_payment(code: str, payment_method: str = Form("CampusPrint Demo Payment"),
                 db: Session = Depends(get_db)):
    o = db.query(Order).filter(Order.order_code == code).first()
    if not o: raise HTTPException(404, "Order not found.")
    o.payment_status = "paid"
    o.payment_method = payment_method
    o.paid_at = datetime.utcnow()
    o.status = "Pending"
    db.commit()
    db.refresh(o)
    return {"success": True, "message": "Demo payment completed.", "order": order_json(o, db)}

@app.get("/api/queue/{printer}")
def printer_queue(printer: str, db: Session = Depends(get_db)):
    if printer not in PRINTERS:
        raise HTTPException(400, "Invalid printer.")
    queue = build_queue(db, printer)
    total_wait = sum(item["estimatedPrintMinutes"] for item in queue)
    return {
        "printer": printer,
        "queueLength": len(queue),
        "estimatedTotalMinutes": total_wait,
        "orders": queue
    }

@app.get("/api/orders/{code}")
def get_order(code: str, db: Session = Depends(get_db)):
    o = db.query(Order).filter(Order.order_code == code).first()
    if not o: raise HTTPException(404, "Order not found.")
    return order_json(o, db)

@app.get("/api/orders")
def list_orders(roll_number: Optional[str] = None,
                registration_number: Optional[str] = None,
                status: Optional[str] = None,
                db: Session = Depends(get_db)):
    q = db.query(Order)
    if roll_number: q = q.filter(Order.roll_number == roll_number.strip())
    if registration_number: q = q.filter(Order.registration_number == registration_number.strip())
    if status: q = q.filter(Order.status == status)
    orders = q.order_by(Order.created_at.desc()).all()
    return [order_json(o, db) for o in orders]

@app.patch("/api/orders/{code}/status")
def update_status(code: str, status: str = Form(...), db: Session = Depends(get_db)):
    if status not in STATUSES:
        raise HTTPException(400, "Status must be Pending, Ready or Completed.")
    o = db.query(Order).filter(Order.order_code == code).first()
    if not o: raise HTTPException(404, "Order not found.")
    o.status = status
    db.commit()
    db.refresh(o)
    return order_json(o, db)

@app.get("/api/orders/{code}/file")
def download_file(code: str, db: Session = Depends(get_db)):
    o = db.query(Order).filter(Order.order_code == code).first()
    if not o: raise HTTPException(404, "Order not found.")
    p = UPLOAD_DIR / o.stored_filename
    if not p.exists(): raise HTTPException(404, "Uploaded file not found.")
    return FileResponse(p, filename=o.filename)
