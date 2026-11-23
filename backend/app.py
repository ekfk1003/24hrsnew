"""24hrsprinting — quote and proof-request API. Not a payment processor."""
import os, time, secrets, hashlib, hmac
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager
import jwt
from fastapi import FastAPI, HTTPException, Request, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, Boolean, ForeignKey, DateTime, select, func, JSON
from sqlalchemy.exc import IntegrityError

DB_URL = os.getenv("DATABASE_URL", "sqlite:///./24hrsprinting.db")
if DB_URL.startswith("postgres://"): DB_URL = "postgresql+psycopg://" + DB_URL[11:]
elif DB_URL.startswith("postgresql://"): DB_URL = "postgresql+psycopg://" + DB_URL[13:]
engine = create_engine(DB_URL, pool_pre_ping=True, connect_args={"check_same_thread":False} if DB_URL.startswith("sqlite") else {})
meta = MetaData()
products = Table("products",meta,Column("id",String(60),primary_key=True),Column("name",String(160),nullable=False),Column("category",String(80),nullable=False),Column("minimum",Integer,nullable=False),Column("unit_cents",Integer,nullable=False),Column("active",Boolean,default=True))
contacts = Table("contacts",meta,Column("id",Integer,primary_key=True,autoincrement=True),Column("email",String(254),unique=True,nullable=False),Column("name",String(100),nullable=False),Column("company",String(140)),Column("phone",String(40)))
quotes = Table("quotes",meta,Column("id",String(42),primary_key=True),Column("contact_id",ForeignKey("contacts.id")),Column("product_id",ForeignKey("products.id")),Column("quantity",Integer),Column("notes",Text),Column("delivery_zip",String(15)),Column("event_date",String(20)),Column("status",String(30),default="new"),Column("created_at",DateTime,default=datetime.utcnow))
orders = Table("orders",meta,Column("id",String(42),primary_key=True),Column("contact_id",ForeignKey("contacts.id")),Column("delivery_zip",String(15)),Column("notes",Text),Column("items",JSON),Column("estimated_subtotal_cents",Integer),Column("status",String(30),default="proof_requested"),Column("created_at",DateTime,default=datetime.utcnow))
users = Table("users",meta,Column("id",Integer,primary_key=True,autoincrement=True),Column("email",String(254),unique=True,nullable=False),Column("name",String(100)),Column("role",String(30)),Column("password_hash",String(200)),Column("active",Boolean,default=True))
audit = Table("audit",meta,Column("id",Integer,primary_key=True,autoincrement=True),Column("actor",String(254)),Column("action",String(90)),Column("reference",String(42)),Column("created_at",DateTime,default=datetime.utcnow))
catalog = [
("lanyard","Full-Color Sublimation Lanyards","Lanyards",100,92),
("wristband","Custom Silicone Wristbands","Wristbands",100,68),
("bags","210D Drawstring Backpacks","Bags",100,158),
("can-cooler","Custom Neoprene Can Coolers","Drinkware",100,138),
("totes","Custom Reusable Tote Bags","Bags",100,216),
("socks","Custom Knit Logo Socks","Apparel",100,495),
("keychains","Custom PVC Keychains","Accessories",100,185),
("tumblers","Personalized Travel Tumblers","Drinkware",50,825)
]
def hash_password(password):
    salt = secrets.token_bytes(16)
    hashed = hashlib.pbkdf2_hmac("sha256",password.encode(),salt,600000)
    return salt.hex()+":"+hashed.hex()

def check_password(password,saved):
    try:
        salt,expected=saved.split(":")
        calculated=hashlib.pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(salt),600000)
        return hmac.compare_digest(calculated.hex(),expected)
    except (ValueError,TypeError):
        return False

meta.create_all(engine)
with engine.begin() as con:
    for pid,name,cat,minimum,cents in catalog:
        if not con.execute(select(products.c.id).where(products.c.id==pid)).first():
            con.execute(products.insert().values(id=pid,name=name,category=cat,minimum=minimum,unit_cents=cents,active=True))
    email=os.getenv("ADMIN_EMAIL","").strip().lower()
    password=os.getenv("ADMIN_PASSWORD","")
    if email and len(password)>=14 and not con.execute(select(users.c.id).where(users.c.email==email)).first():
        con.execute(users.insert().values(email=email,name="Administrator",role="admin",password_hash=hash_password(password),active=True))

app=FastAPI(title="24hrsprinting API",version="0.1.0",docs_url=None if os.getenv("APP_ENV")=="production" else "/docs")
origins=[x.strip() for x in os.getenv("ALLOWED_ORIGINS","https://ekfk1003.github.io,http://127.0.0.1:8000").split(",") if x.strip()]
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_methods=["GET","POST","PATCH"],allow_headers=["Authorization","Content-Type"])
rate_buckets={}
def limit(request,kind,count,window=60):
    key=(kind,request.client.host if request.client else "unknown")
    now=time.monotonic()
    recent=[t for t in rate_buckets.get(key,[]) if t>now-window]
    if len(recent)>=count: raise HTTPException(429,"Too many requests")
    recent.append(now);rate_buckets[key]=recent
    if len(rate_buckets)>10000: rate_buckets.clear()

class Buyer(BaseModel):
    name: str=Field(min_length=2,max_length=100)
    email: EmailStr
    company: str=Field("",max_length=140)
    phone: str=Field("",max_length=40)
class QuoteInput(Buyer):
    product_id: str=Field(max_length=60)
    quantity: int=Field(ge=1,le=200000)
    notes: str=Field("",max_length=2000)
    event_date: str=Field("",max_length=20)
    delivery_zip: str=Field("",max_length=15)
class ItemInput(BaseModel):
    product_id: str=Field(max_length=60)
    quantity: int=Field(ge=1,le=200000)
    option: str=Field("",max_length=100)
    finish: str=Field("",max_length=100)
    color: str=Field("",max_length=40)
    artwork_filename: str=Field("",max_length=160)
class OrderInput(Buyer):
    items: list[ItemInput]=Field(min_length=1,max_length=30)
    notes: str=Field("",max_length=2000)
    delivery_zip: str=Field("",max_length=15)
class LoginInput(BaseModel):
    email: EmailStr
    password: str
class StatusInput(BaseModel):
    status: str

def contact_id(con,payload):
    email=str(payload.email).strip().lower()
    row=con.execute(select(contacts.c.id).where(contacts.c.email==email)).first()
    if row:
        con.execute(contacts.update().where(contacts.c.id==row.id).values(name=payload.name,company=payload.company,phone=payload.phone))
        return row.id
    result=con.execute(contacts.insert().values(name=payload.name,email=email,company=payload.company,phone=payload.phone))
    return result.inserted_primary_key[0]

def new_reference(prefix): return prefix+"-"+secrets.token_hex(7).upper()

@app.get("/health")
def health(): return {"status":"ok","payments_enabled":False}

@app.get("/api/v1/products")
def list_products():
    with engine.connect() as con:
        found=con.execute(select(products).where(products.c.active==True)).mappings().all()
    return {"products":[{"id":x["id"],"name":x["name"],"category":x["category"],"minimum":x["minimum"],"estimate_unit_usd":f'{x["unit_cents"]/100:.2f}',"pricing_note":"Illustrative only"} for x in found]}

@app.post("/api/v1/quotes",status_code=201)
def create_quote(payload:QuoteInput,request:Request):
    limit(request,"quote",10)
    with engine.begin() as con:
        p=con.execute(select(products).where(products.c.id==payload.product_id,products.c.active==True)).mappings().first()
        if not p: raise HTTPException(422,"Invalid product")
        if payload.quantity<p["minimum"]: raise HTTPException(422,f'Minimum quantity: {p["minimum"]}')
        cid=contact_id(con,payload)
        reference=new_reference("Q")
        con.execute(quotes.insert().values(id=reference,contact_id=cid,product_id=payload.product_id,quantity=payload.quantity,notes=payload.notes,event_date=payload.event_date,delivery_zip=payload.delivery_zip,status="new"))
    return {"reference":reference,"status":"new","message":"Quote received for manual review; no payment taken"}

@app.post("/api/v1/orders",status_code=201)
def create_order(payload:OrderInput,request:Request):
    limit(request,"order",6)
    with engine.begin() as con:
        subtotal=0
        lines=[]
        for item in payload.items:
            p=con.execute(select(products).where(products.c.id==item.product_id,products.c.active==True)).mappings().first()
            if not p: raise HTTPException(422,f"Invalid product: {item.product_id}")
            if item.quantity<p["minimum"]: raise HTTPException(422,f'Minimum quantity for {p["name"]}: {p["minimum"]}')
            subtotal+=item.quantity*p["unit_cents"]
            lines.append(item.model_dump())
        if subtotal>100000000: raise HTTPException(422,"Please request a custom quote")
        cid=contact_id(con,payload)
        reference=new_reference("PR")
        con.execute(orders.insert().values(id=reference,contact_id=cid,delivery_zip=payload.delivery_zip,notes=payload.notes,items=lines,estimated_subtotal_cents=subtotal,status="proof_requested"))
    return {"reference":reference,"status":"proof_requested","estimated_subtotal_usd":f"{subtotal/100:.2f}","message":"Proof request received. Not a paid or accepted production order."}

JWT_SECRET=os.getenv("JWT_SECRET","")
def auth(authorization:str|None=Header(None)):
    if len(JWT_SECRET)<32: raise HTTPException(503,"Admin authentication not configured")
    if not authorization or not authorization.startswith("Bearer "): raise HTTPException(401,"Sign in required")
    try:
        claims=jwt.decode(authorization[7:],JWT_SECRET,algorithms=["HS256"],issuer="24hrsprinting")
        with engine.connect() as con:
            user=con.execute(select(users).where(users.c.id==int(claims["sub"]),users.c.active==True)).mappings().first()
        if not user: raise ValueError()
        return dict(user)
    except (jwt.PyJWTError,ValueError,KeyError): raise HTTPException(401,"Invalid or expired session")

def allowed(user,roles):
    if user["role"] not in roles: raise HTTPException(403,"Insufficient permission")

@app.post("/api/v1/admin/login")
def login(payload:LoginInput,request:Request):
    limit(request,"login",6,300)
    if len(JWT_SECRET)<32: raise HTTPException(503,"Configure JWT_SECRET")
    with engine.connect() as con:
        user=con.execute(select(users).where(users.c.email==str(payload.email).lower(),users.c.active==True)).mappings().first()
    if not user or not check_password(payload.password,user["password_hash"]): raise HTTPException(401,"Invalid credentials")
    issued=datetime.now(timezone.utc)
    token=jwt.encode({"sub":str(user["id"]),"iss":"24hrsprinting","iat":issued,"exp":issued+timedelta(hours=2)},JWT_SECRET,algorithm="HS256")
    return {"access_token":token,"token_type":"bearer","expires_in":7200,"role":user["role"]}

@app.get("/api/v1/admin/dashboard")
def dashboard(user=Depends(auth)):
    allowed(user,{"admin","sales","ops","viewer"})
    with engine.connect() as con:
        return {"contacts":con.scalar(select(func.count()).select_from(contacts)), "quotes":con.scalar(select(func.count()).select_from(quotes)), "orders":con.scalar(select(func.count()).select_from(orders)), "products":con.scalar(select(func.count()).select_from(products)), "paid_orders":0,"user_role":user["role"]}

def list_records(table,kind,user):
    allowed(user,{"admin","sales","ops","viewer"})
    with engine.connect() as con:
        rows=con.execute(select(table,contacts.c.name,contacts.c.email,contacts.c.company).join(contacts,table.c.contact_id==contacts.c.id).order_by(table.c.created_at.desc()).limit(150)).mappings().all()
        result=[]
        for row in rows:
            r=dict(row)
            r["reference"]=r.pop("id")
            r["created_at"]=r["created_at"].isoformat() if r.get("created_at") else ""
            if kind=="orders": r["estimated_subtotal_usd"]=f'{r.pop("estimated_subtotal_cents")/100:.2f}'
            result.append(r)
    return {kind:result}

@app.get("/api/v1/admin/quotes")
def admin_quotes(user=Depends(auth)): return list_records(quotes,"quotes",user)

@app.get("/api/v1/admin/orders")
def admin_orders(user=Depends(auth)): return list_records(orders,"orders",user)

@app.patch("/api/v1/admin/quotes/{reference}")
def quote_status(reference:str,payload:StatusInput,user=Depends(auth)):
    allowed(user,{"admin","sales"})
    if payload.status not in {"new","reviewing","proof_in_progress","proof_sent","awaiting_approval","approved","closed","cancelled"}: raise HTTPException(422,"Invalid status")
    with engine.begin() as con:
        if not con.execute(select(quotes.c.id).where(quotes.c.id==reference)).first(): raise HTTPException(404,"Not found")
        con.execute(quotes.update().where(quotes.c.id==reference).values(status=payload.status))
        con.execute(audit.insert().values(actor=user["email"],action="quote_status",reference=reference))
    return {"reference":reference,"status":payload.status}

@app.patch("/api/v1/admin/orders/{reference}")
def order_status(reference:str,payload:StatusInput,user=Depends(auth)):
    allowed(user,{"admin","sales","ops"})
    if payload.status not in {"proof_requested","reviewing","proof_in_progress","proof_sent","awaiting_approval","approved","closed","cancelled"}: raise HTTPException(422,"Invalid status")
    with engine.begin() as con:
        if not con.execute(select(orders.c.id).where(orders.c.id==reference)).first(): raise HTTPException(404,"Not found")
        con.execute(orders.update().where(orders.c.id==reference).values(status=payload.status))
        con.execute(audit.insert().values(actor=user["email"],action="order_status",reference=reference))
    return {"reference":reference,"status":payload.status}
