"""24hrsprinting — quote and proof-request API. Not a payment processor."""
import os, time, secrets, hashlib, hmac, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager
import jwt
from fastapi import FastAPI, HTTPException, Request, Header, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field, HttpUrl
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, Boolean, ForeignKey, DateTime, select, func, JSON, text as sql_text
from sqlalchemy.exc import IntegrityError

DB_URL = os.getenv("DATABASE_URL", "sqlite:///./24hrsprinting.db")
if DB_URL.startswith("postgres://"): DB_URL = "postgresql+psycopg://" + DB_URL[11:]
elif DB_URL.startswith("postgresql://"): DB_URL = "postgresql+psycopg://" + DB_URL[13:]
# Supabase Postgres: keep customer data in a private schema, not the public Data API schema.
# Never expose DATABASE_URL or admin secrets in the browser.
IS_SQLITE = DB_URL.startswith("sqlite")
DB_SCHEMA = None if IS_SQLITE else "app_private"
engine = create_engine(
    DB_URL, pool_pre_ping=True, pool_size=2, max_overflow=0, pool_recycle=300,
    connect_args={"check_same_thread": False} if IS_SQLITE else {"sslmode": "require"}
)
if DB_SCHEMA:
    with engine.begin() as conn:
        conn.execute(sql_text("CREATE SCHEMA IF NOT EXISTS app_private"))
        conn.execute(sql_text("REVOKE ALL ON SCHEMA app_private FROM PUBLIC"))
meta = MetaData(schema=DB_SCHEMA)
products = Table("products",meta,Column("id",String(60),primary_key=True),Column("name",String(160),nullable=False),Column("category",String(80),nullable=False),Column("minimum",Integer,nullable=False),Column("unit_cents",Integer,nullable=False),Column("active",Boolean,default=True))
contacts = Table("contacts",meta,Column("id",Integer,primary_key=True,autoincrement=True),Column("email",String(254),unique=True,nullable=False),Column("name",String(100),nullable=False),Column("company",String(140)),Column("phone",String(40)))
quotes = Table("quotes",meta,Column("id",String(42),primary_key=True),Column("contact_id",ForeignKey("contacts.id")),Column("product_id",ForeignKey("products.id")),Column("quantity",Integer),Column("notes",Text),Column("delivery_zip",String(15)),Column("event_date",String(20)),Column("status",String(30),default="new"),Column("created_at",DateTime,default=datetime.utcnow))
orders = Table("orders",meta,Column("id",String(42),primary_key=True),Column("contact_id",ForeignKey("contacts.id")),Column("delivery_zip",String(15)),Column("notes",Text),Column("items",JSON),Column("estimated_subtotal_cents",Integer),Column("status",String(30),default="proof_requested"),Column("created_at",DateTime,default=datetime.utcnow))
users = Table("users",meta,Column("id",Integer,primary_key=True,autoincrement=True),Column("email",String(254),unique=True,nullable=False),Column("name",String(100)),Column("role",String(30)),Column("password_hash",String(200)),Column("active",Boolean,default=True))
audit = Table("audit",meta,Column("id",Integer,primary_key=True,autoincrement=True),Column("actor",String(254)),Column("action",String(90)),Column("reference",String(42)),Column("created_at",DateTime,default=datetime.utcnow))
# SaaS test foundation: lead review and content approval are internal only.
# No external scraping, campaign sending, OAuth or publishing is attempted here.
leads = Table("prospect_leads",meta,
    Column("id",Integer,primary_key=True,autoincrement=True),
    Column("organization",String(160),nullable=False),
    Column("website",String(255),nullable=False),
    Column("segment",String(80),nullable=False),
    Column("country",String(80),nullable=False,default="United States"),
    Column("contact_name",String(100),nullable=False,default=""),
    Column("contact_email",String(254),nullable=False,default=""),
    Column("source_url",String(1000),nullable=False),
    Column("notes",Text,nullable=False,default=""),
    Column("status",String(24),nullable=False,default="needs_review"),
    Column("created_at",DateTime,default=datetime.utcnow))
content_drafts = Table("content_drafts",meta,
    Column("id",String(42),primary_key=True),
    Column("channel",String(45),nullable=False),
    Column("title",String(160),nullable=False),
    Column("body",Text,nullable=False),
    Column("status",String(24),nullable=False,default="draft"),
    Column("created_at",DateTime,default=datetime.utcnow))
# Registry entries represent documented capabilities, NOT connected accounts.
INTEGRATION_REGISTRY = [
    ("facebook","social","Facebook Page","publish","OAuth + Page permissions","https://developers.facebook.com/docs/graph-api/reference/page/feed/"),
    ("instagram","social","Instagram Professional","publish","Meta app permissions + professional account","https://developers.facebook.com/docs/instagram-platform/"),
    ("linkedin","social","LinkedIn Organization","publish","OAuth + approved organization social scopes","https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api"),
    ("x","social","X","publish","Developer credits and account OAuth","https://developer.x.com/"),
    ("tiktok","social","TikTok","publish","Content Posting API audit + consent","https://developers.tiktok.com/docs/en/content-posting-api-get-started"),
    ("pinterest","social","Pinterest","publish","Developer app + authorized account","https://developers.pinterest.com/docs/work-with-organic-content-and-users/create-boards-and-pins/"),
    ("youtube","social","YouTube","publish","Google Cloud OAuth and Data API","https://developers.google.com/youtube/v3/docs/videos/insert"),
    ("reddit","community","Reddit","limited","API/developer approval and community rules","https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data"),
    ("telegram","messaging","Telegram Channel","publish","Bot token + channel admin rights","https://core.telegram.org/bots/api"),
    ("whatsapp_business","messaging","WhatsApp Business","messages","WhatsApp Business Platform and opt-in","https://developers.facebook.com/documentation/business-messaging/whatsapp/overview"),
    ("whatsapp_channel","messaging","WhatsApp Channel","manual","No verified official public publishing API","https://faq.whatsapp.com/794229125227200/"),
    ("google_business","directory","Google Business Profile","publish","Verified eligible locations and approved API access","https://developers.google.com/my-business/"),
    ("craigslist","directory","Craigslist","manual","Review individual posting rules; no general approved auto-posting connector","https://www.craigslist.org/about/help/"),
    ("yelp","directory","Yelp","limited","Business management tools and official API eligibility","https://docs.developer.yelp.com/"),
    ("bbb","directory","BBB","manual","Business profile management; no general posting API verified","https://www.bbb.org/"),
    ("alignable","directory","Alignable","manual","Business profile management; no general publishing API verified","https://www.alignable.com/"),
    ("rss","content","RSS/Atom","feed","Owned-site generated feed","https://www.rssboard.org/rss-specification"),
    ("getresponse","marketing","GetResponse","email","API account access and compliant consent","https://apidocs.getresponse.com/"),
    ("shopify","store","Shopify","sync","OAuth app and Admin GraphQL scopes","https://shopify.dev/docs/api/admin-graphql/latest"),
    ("woocommerce","store","WooCommerce","sync","Site REST API credentials and webhooks","https://developer.woocommerce.com/docs/apis/rest-api/"),
    ("oscommerce","store","osCommerce","custom","Version-dependent custom connector; verify existing store API","https://library.oscommerce.com/"),
    ("etsy","store","Etsy","sync","OAuth app approval and listing scopes","https://developer.etsy.com/documentation/"),
    ("ebay","store","eBay","sync","Sell API OAuth and listing policies","https://developer.ebay.com/api-docs/sell/static/inventory/managing-inventory-and-offers.html"),
    ("google_merchant","store","Google Merchant Center","feed","Merchant API account and developer registration","https://developers.google.com/merchant/api"),
    ("faire","store","Faire","sync","Authorized brand/partner API access","https://faire.github.io/external-api-v2-docs/"),
    ("amazon","store","Amazon SP-API","sync","Selling Partner authorization and approved app","https://developer-docs.amazon/sp-api/docs/what-is-the-selling-partner-api"),
    ("tiktok_shop","store","TikTok Shop","sync","Region-specific shop and partner API authorization","https://partner.tiktokshop.com/"),
    ("apollo","leads","Apollo","discover","Licensed API access and appropriate commercial use","https://docs.apollo.io/"),
    ("hunter","leads","Hunter","verify","API key + legal use of email discovery","https://hunter.io/api-documentation"),
    ("asi","suppliers","ASI/ESP","limited","Eligible account and partner integration approval","https://developers.asicentral.com/EspUpdates"),
]


# Database-backed website controls; external integrations and customer artwork remain separate.
product_display = Table("product_display",meta,
    Column("product_id",String(60),ForeignKey("products.id"),primary_key=True),
    Column("description",Text,nullable=False,default=""),
    Column("featured",Boolean,nullable=False,default=True),
    Column("sort_order",Integer,nullable=False,default=100))
product_images = Table("product_images",meta,
    Column("id",Integer,primary_key=True,autoincrement=True),
    Column("product_id",String(60),ForeignKey("products.id"),nullable=False),
    Column("url",String(2048),nullable=False),
    Column("alt",String(240),nullable=False,default=""),
    Column("source_url",String(2048),nullable=False,default=""),
    Column("storage_key",String(255),nullable=False,default=""),
    Column("is_primary",Boolean,nullable=False,default=False),
    Column("active",Boolean,nullable=False,default=True),
    Column("sort_order",Integer,nullable=False,default=100))
site_flags = Table("site_flags",meta,
    Column("key",String(80),primary_key=True),
    Column("enabled",Boolean,nullable=False,default=True))
FEATURE_DEFINITIONS = [
    ("storefront_enabled","Entire storefront","Temporarily hides the product catalog and quote/order entry points"),
    ("catalog_enabled","Product catalog","Shows browse products and product-detail pages"),
    ("show_hero","Homepage hero","Shows the homepage introduction and hero image"),
    ("show_categories","Shop by category","Shows category tiles on the homepage"),
    ("show_featured","Featured products","Shows popular picks on the homepage"),
    ("show_search","Catalog search","Shows catalog keyword search"),
    ("customizer_enabled","Product customization","Allows product configuration and adding items to the proof-request cart"),
    ("cart_enabled","Cart and checkout preview","Enables cart and proof-request checkout steps"),
    ("quotes_enabled","Free proof quotation requests","Allows new quote requests through the public API"),
    ("proof_requests_enabled","Proof-request submissions","Allows new non-paid proof orders through the public API"),
    ("show_process","How it works","Shows homepage process explanation"),
]
FEATURE_DEFAULTS={x[0]:True for x in FEATURE_DEFINITIONS}
INITIAL_PRODUCT_PHOTOS={"lanyard":["https://images.pexels.com/photos/8761304/pexels-photo-8761304.jpeg?auto=compress&cs=tinysrgb&w=1100","https://www.pexels.com/photo/badges-on-lanyards-8761304/"],"wristband":["https://upload.wikimedia.org/wikipedia/commons/8/88/Custom_Wristbands.jpg","https://commons.wikimedia.org/wiki/File:Custom_Wristbands.jpg"],"bags":["https://images.pexels.com/photos/9603488/pexels-photo-9603488.jpeg?auto=compress&cs=tinysrgb&w=1100","https://www.pexels.com/photo/a-person-holding-a-drawstring-bag-9603488/"],"can-cooler":["https://upload.wikimedia.org/wikipedia/commons/1/1a/KOOZIE_Picture.jpg","https://commons.wikimedia.org/wiki/File:KOOZIE_Picture.jpg"],"totes":["https://images.pexels.com/photos/9869067/pexels-photo-9869067.jpeg?auto=compress&cs=tinysrgb&w=1100","https://www.pexels.com/photo/plain-tote-bag-9869067/"],"socks":["https://images.pexels.com/photos/15195384/pexels-photo-15195384.jpeg?auto=compress&cs=tinysrgb&w=1100","https://www.pexels.com/photo/colorful-socks-on-legs-15195384/"],"keychains":["https://images.pexels.com/photos/26730920/pexels-photo-26730920.jpeg?auto=compress&cs=tinysrgb&w=1100","https://www.pexels.com/photo/souvenirs-in-a-shop-26730920/"],"tumblers":["https://images.pexels.com/photos/19155039/pexels-photo-19155039.jpeg?auto=compress&cs=tinysrgb&w=1100","https://www.pexels.com/photo/steel-travel-mug-on-table-19155039/"]}
def active_features(con):
    found=con.execute(select(site_flags.c.key,site_flags.c.enabled)).all()
    return {**FEATURE_DEFAULTS,**{key:bool(enabled) for key,enabled in found}}

def public_product_records(con, include_hidden=False):
    selected=con.execute(select(products,product_display.c.description,product_display.c.featured,product_display.c.sort_order)
        .outerjoin(product_display,product_display.c.product_id==products.c.id)
        .order_by(product_display.c.sort_order.asc(),products.c.name.asc())).mappings().all()
    photos=con.execute(select(product_images).order_by(product_images.c.sort_order,product_images.c.id)).mappings().all()
    grouped={}
    for image in photos:
        if include_hidden or image["active"]:
            grouped.setdefault(image["product_id"],[]).append({
                "id":image["id"],"url":image["url"],"alt":image["alt"],
                "source_url":image["source_url"],"is_primary":bool(image["is_primary"]),
                "active":bool(image["active"]),"sort_order":image["sort_order"],
                **({"storage_managed":bool(image["storage_key"])} if include_hidden else {})
            })
    result=[]
    for row in selected:
        if not include_hidden and not row["active"]:continue
        imgs=grouped.get(row["id"],[])
        shown=[i for i in imgs if i["active"]]
        primary=next((i for i in shown if i["is_primary"]),shown[0] if shown else None)
        result.append({
            "id":row["id"],"name":row["name"],"category":row["category"],
            "minimum":row["minimum"],"estimate_unit_usd":f'{row["unit_cents"]/100:.2f}',
            "pricing_note":"Illustrative only","active":bool(row["active"]),
            "description":row["description"] or "",
            "featured":bool(row["featured"]) if row["featured"] is not None else True,
            "sort_order":row["sort_order"] if row["sort_order"] is not None else 100,
            "photo":primary["url"] if primary else "",
            "images":imgs if include_hidden else shown,
        })
    return result

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
    for key in FEATURE_DEFAULTS:
        if not con.execute(select(site_flags.c.key).where(site_flags.c.key==key)).first():
            con.execute(site_flags.insert().values(key=key,enabled=FEATURE_DEFAULTS[key]))
    for pid,name,cat,minimum,cents in catalog:
        if not con.execute(select(product_display.c.product_id).where(product_display.c.product_id==pid)).first():
            con.execute(product_display.insert().values(product_id=pid,description="",featured=True,sort_order=100))
            seed=INITIAL_PRODUCT_PHOTOS.get(pid)
            if seed:
                con.execute(product_images.insert().values(product_id=pid,url=seed[0],
                    source_url=seed[1],alt=name+" reference photo",storage_key="",is_primary=True,active=True,sort_order=0))
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

class ProductUpdateInput(BaseModel):
    name: str=Field(min_length=3,max_length=160)
    minimum: int=Field(ge=1,le=200000)
    unit_cents: int=Field(ge=1,le=10000000)



class ProductCreateInput(BaseModel):
    id: str=Field(pattern=r"^[a-z0-9][a-z0-9-]{1,58}$")
    name: str=Field(min_length=3,max_length=160)
    category: str=Field(min_length=2,max_length=80)
    minimum: int=Field(ge=1,le=200000)
    unit_cents: int=Field(ge=1,le=10000000)
    description: str=Field(default="",max_length=2000)
    featured: bool=True
    sort_order: int=Field(default=100,ge=0,le=100000)
    active: bool=True

class ProductVisibilityInput(BaseModel):
    active: bool

class ProductDisplayInput(BaseModel):
    description: str=Field(default="",max_length=2000)
    featured: bool=True
    sort_order: int=Field(default=100,ge=0,le=100000)

class ImageURLInput(BaseModel):
    url: HttpUrl
    alt: str=Field(min_length=3,max_length=240)
    source_url: HttpUrl|None=None

class FeatureFlagInput(BaseModel):
    enabled: bool

class LeadCreateInput(BaseModel):
    organization: str=Field(min_length=2,max_length=160)
    website: str=Field(min_length=4,max_length=255)
    segment: str=Field(min_length=2,max_length=80)
    country: str=Field(default="United States",max_length=80)
    contact_name: str=Field(default="",max_length=100)
    contact_email: EmailStr|None=None
    source_url: str=Field(min_length=8,max_length=1000)
    notes: str=Field(default="",max_length=1000)

class LeadStatusInput(BaseModel):
    status: str

class DraftCreateInput(BaseModel):
    channel: str=Field(min_length=2,max_length=45)
    title: str=Field(min_length=3,max_length=160)
    body: str=Field(min_length=5,max_length=5000)

class DraftStatusInput(BaseModel):
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

@app.get("/api/v1/site-config")
def site_config():
    with engine.connect() as con:
        flags=active_features(con)
    return {"features":flags,"pricing_note":"Illustrative only","payments_enabled":False}

@app.get("/api/v1/products")
def list_products():
    with engine.connect() as con:
        flags=active_features(con)
        result=public_product_records(con) if flags["storefront_enabled"] and flags["catalog_enabled"] else []
    return {"products":result}

@app.post("/api/v1/quotes",status_code=201)
def create_quote(payload:QuoteInput,request:Request):
    limit(request,"quote",10)
    # Check business controls on the server, never trust hidden client buttons.
    with engine.begin() as con:
        flags=active_features(con)
        if not flags["storefront_enabled"] or not flags["quotes_enabled"]:raise HTTPException(503,"Quote requests are currently disabled")
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
    # Check business controls on the server, never trust hidden client buttons.
    with engine.begin() as con:
        flags=active_features(con)
        if not flags["storefront_enabled"] or not flags["proof_requests_enabled"] or not flags["cart_enabled"]:raise HTTPException(503,"Proof requests are currently disabled")
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

@app.patch("/api/v1/admin/products/{product_id}")
def update_product(product_id:str,payload:ProductUpdateInput,user=Depends(auth)):
    allowed(user,{"admin"})
    with engine.begin() as con:
        exists=con.execute(select(products.c.id).where(products.c.id==product_id)).first()
        if not exists: raise HTTPException(404,"Product not found")
        con.execute(products.update().where(products.c.id==product_id).values(
            name=payload.name.strip(),minimum=payload.minimum,unit_cents=payload.unit_cents))
        con.execute(audit.insert().values(actor=user["email"],action="product_update",reference=product_id))
    return {"id":product_id,"name":payload.name.strip(),"minimum":payload.minimum,"estimate_unit_usd":f"{payload.unit_cents/100:.2f}","pricing_note":"Illustrative only"}


@app.get("/api/v1/admin/catalog")
def admin_catalog(user=Depends(auth)):
    allowed(user,{"admin","sales","ops","viewer"})
    with engine.connect() as con:
        return {"products":public_product_records(con,include_hidden=True)}

@app.post("/api/v1/admin/products",status_code=201)
def create_product(payload:ProductCreateInput,user=Depends(auth)):
    allowed(user,{"admin"})
    with engine.begin() as con:
        if con.execute(select(products.c.id).where(products.c.id==payload.id)).first():
            raise HTTPException(409,"Product ID already exists")
        con.execute(products.insert().values(id=payload.id,name=payload.name.strip(),category=payload.category.strip(),
           minimum=payload.minimum,unit_cents=payload.unit_cents,active=payload.active))
        con.execute(product_display.insert().values(product_id=payload.id,description=payload.description.strip(),
           featured=payload.featured,sort_order=payload.sort_order))
        con.execute(audit.insert().values(actor=user["email"],action="product_created",reference=payload.id))
    return {"id":payload.id,"active":payload.active}

@app.patch("/api/v1/admin/products/{product_id}/visibility")
def set_product_visibility(product_id:str,payload:ProductVisibilityInput,user=Depends(auth)):
    allowed(user,{"admin"})
    with engine.begin() as con:
        if not con.execute(select(products.c.id).where(products.c.id==product_id)).first():
            raise HTTPException(404,"Product not found")
        con.execute(products.update().where(products.c.id==product_id).values(active=payload.active))
        con.execute(audit.insert().values(actor=user["email"],action="product_visibility",reference=product_id))
    return {"id":product_id,"active":payload.active}

@app.patch("/api/v1/admin/products/{product_id}/display")
def set_product_display(product_id:str,payload:ProductDisplayInput,user=Depends(auth)):
    allowed(user,{"admin"})
    with engine.begin() as con:
        if not con.execute(select(products.c.id).where(products.c.id==product_id)).first():
            raise HTTPException(404,"Product not found")
        vals={"description":payload.description.strip(),"featured":payload.featured,"sort_order":payload.sort_order}
        present=con.execute(select(product_display.c.product_id).where(product_display.c.product_id==product_id)).first()
        if present:con.execute(product_display.update().where(product_display.c.product_id==product_id).values(**vals))
        else:con.execute(product_display.insert().values(product_id=product_id,**vals))
        con.execute(audit.insert().values(actor=user["email"],action="product_display",reference=product_id))
    return {"id":product_id,**vals}

@app.get("/api/v1/admin/features")
def admin_features(user=Depends(auth)):
    allowed(user,{"admin","sales","ops","viewer"})
    with engine.connect() as con:flags=active_features(con)
    return {"features":[{"key":key,"name":name,"description":description,"enabled":flags[key]}
        for key,name,description in FEATURE_DEFINITIONS]}

@app.patch("/api/v1/admin/features/{key}")
def set_feature(key:str,payload:FeatureFlagInput,user=Depends(auth)):
    allowed(user,{"admin"})
    if key not in FEATURE_DEFAULTS:raise HTTPException(404,"Unknown feature")
    with engine.begin() as con:
        exists=con.execute(select(site_flags.c.key).where(site_flags.c.key==key)).first()
        if exists:con.execute(site_flags.update().where(site_flags.c.key==key).values(enabled=payload.enabled))
        else:con.execute(site_flags.insert().values(key=key,enabled=payload.enabled))
        con.execute(audit.insert().values(actor=user["email"],action="feature_changed",reference=key))
    return {"key":key,"enabled":payload.enabled}

def safe_public_image_url(link):
    parsed=urllib.parse.urlsplit(str(link))
    if parsed.scheme!="https" or not parsed.hostname or parsed.username or parsed.password:
        raise HTTPException(422,"Use a public HTTPS image URL without credentials")
    host=parsed.hostname.lower()
    if host in {"localhost","localhost.localdomain"} or host.endswith((".local",".internal")) or host.startswith(("127.","10.","192.168.","169.254.","172.16.","172.17.","172.18.","172.19.","172.2","172.30.","172.31.","0.","[::")):
        raise HTTPException(422,"Private network links cannot be used for product photos")
    return str(link)

@app.post("/api/v1/admin/products/{product_id}/images",status_code=201)
def add_product_image(product_id:str,payload:ImageURLInput,user=Depends(auth)):
    allowed(user,{"admin"})
    link=safe_public_image_url(payload.url)
    source=safe_public_image_url(payload.source_url) if payload.source_url else ""
    with engine.begin() as con:
        if not con.execute(select(products.c.id).where(products.c.id==product_id)).first():
            raise HTTPException(404,"Product not found")
        count=con.scalar(select(func.count()).select_from(product_images).where(product_images.c.product_id==product_id,product_images.c.active==True))
        if count>=20:raise HTTPException(422,"Maximum 20 active photos per product")
        result=con.execute(product_images.insert().values(product_id=product_id,url=link,
            alt=payload.alt.strip(),source_url=source,is_primary=(count==0),active=True,sort_order=count+1))
        photo_id=result.inserted_primary_key[0]
        con.execute(audit.insert().values(actor=user["email"],action="image_added",reference=product_id))
    return {"id":photo_id,"product_id":product_id,"url":link,"active":True}

@app.patch("/api/v1/admin/products/{product_id}/images/{image_id}/primary")
def set_primary_image(product_id:str,image_id:int,user=Depends(auth)):
    allowed(user,{"admin"})
    with engine.begin() as con:
        found=con.execute(select(product_images.c.id).where(product_images.c.id==image_id,
            product_images.c.product_id==product_id,product_images.c.active==True)).first()
        if not found:raise HTTPException(404,"Photo not found")
        con.execute(product_images.update().where(product_images.c.product_id==product_id).values(is_primary=False))
        con.execute(product_images.update().where(product_images.c.id==image_id).values(is_primary=True))
        con.execute(audit.insert().values(actor=user["email"],action="image_primary",reference=product_id))
    return {"id":image_id,"is_primary":True}

@app.delete("/api/v1/admin/products/{product_id}/images/{image_id}")
def remove_image(product_id:str,image_id:int,user=Depends(auth)):
    allowed(user,{"admin"})
    with engine.begin() as con:
        found=con.execute(select(product_images).where(product_images.c.id==image_id,
            product_images.c.product_id==product_id,product_images.c.active==True)).mappings().first()
        if not found:raise HTTPException(404,"Photo not found")
        # Soft delete retains audit history and avoids deleting shared remote images.
        con.execute(product_images.update().where(product_images.c.id==image_id).values(active=False,is_primary=False))
        nextimg=con.execute(select(product_images.c.id).where(product_images.c.product_id==product_id,
            product_images.c.active==True).order_by(product_images.c.sort_order,product_images.c.id)).first()
        if nextimg:
            already=con.execute(select(product_images.c.id).where(product_images.c.product_id==product_id,
                product_images.c.active==True,product_images.c.is_primary==True)).first()
            if not already:con.execute(product_images.update().where(product_images.c.id==nextimg.id).values(is_primary=True))
        con.execute(audit.insert().values(actor=user["email"],action="image_removed",reference=product_id))
    return {"id":image_id,"active":False}

@app.post("/api/v1/admin/products/{product_id}/images/upload",status_code=201)
async def upload_product_image(product_id:str,file:UploadFile=File(...),alt:str=Form(...),user=Depends(auth)):
    allowed(user,{"admin"})
    base=os.getenv("SUPABASE_URL","").strip().rstrip("/")
    secret=os.getenv("SUPABASE_SERVICE_ROLE_KEY","").strip()
    bucket=os.getenv("PRODUCT_MEDIA_BUCKET","product-media").strip()
    if not base or not secret:raise HTTPException(503,"Product uploads require SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in Render")
    if file.content_type not in {"image/jpeg","image/png","image/webp"}:
        raise HTTPException(422,"Only JPEG, PNG and WebP images are accepted")
    data=await file.read(5_000_001)
    if len(data)>5_000_000:raise HTTPException(413,"Image exceeds 5 MB")
    valid=((data.startswith(b"\xff\xd8\xff") and file.content_type=="image/jpeg")
        or (data.startswith(b"\x89PNG\r\n\x1a\n") and file.content_type=="image/png")
        or (data.startswith(b"RIFF") and data[8:12]==b"WEBP" and file.content_type=="image/webp"))
    if not valid:raise HTTPException(422,"Invalid image data")
    alt=alt.strip()
    if not (3<=len(alt)<=240):raise HTTPException(422,"Alt text must be 3–240 characters")
    with engine.connect() as con:
        if not con.execute(select(products.c.id).where(products.c.id==product_id)).first():
            raise HTTPException(404,"Product not found")
        count=con.scalar(select(func.count()).select_from(product_images).where(product_images.c.product_id==product_id,product_images.c.active==True))
        if count>=20:raise HTTPException(422,"Maximum 20 active photos per product")
    ext={"image/jpeg":"jpg","image/png":"png","image/webp":"webp"}[file.content_type]
    key=product_id+"/"+secrets.token_hex(16)+"."+ext
    resource=base+"/storage/v1/object/"+urllib.parse.quote(bucket,safe="")+"/"+urllib.parse.quote(key,safe="/")
    request=urllib.request.Request(resource,data=data,method="POST",
        headers={"Authorization":"Bearer "+secret,"apikey":secret,"Content-Type":file.content_type,
                 "x-upsert":"false","cache-control":"3600"})
    try:
        with urllib.request.urlopen(request,timeout=12) as response: response.read()
    except urllib.error.HTTPError as err:
        raise HTTPException(502,"Image storage upload failed ("+str(err.code)+"). Check bucket and storage policy.")
    except (OSError,TimeoutError):
        raise HTTPException(502,"Image storage temporarily unavailable")
    public_url=base+"/storage/v1/object/public/"+urllib.parse.quote(bucket,safe="")+"/"+urllib.parse.quote(key,safe="/")
    with engine.begin() as con:
        result=con.execute(product_images.insert().values(product_id=product_id,url=public_url,
            alt=alt,source_url="",storage_key=key,is_primary=(count==0),active=True,sort_order=count+1))
        photo_id=result.inserted_primary_key[0]
        con.execute(audit.insert().values(actor=user["email"],action="image_uploaded",reference=product_id))
    return {"id":photo_id,"product_id":product_id,"url":public_url,"active":True}

@app.get("/api/v1/admin/contacts")
def admin_contacts(user=Depends(auth)):
    allowed(user,{"admin","sales","ops","viewer"})
    with engine.connect() as con:
        found=con.execute(select(contacts).order_by(contacts.c.id.desc()).limit(150)).mappings().all()
    return {"contacts":[{"id":x["id"],"name":x["name"],"email":x["email"],"company":x["company"] or "", "phone":x["phone"] or ""} for x in found]}

@app.get("/api/v1/admin/audit")
def admin_audit(user=Depends(auth)):
    allowed(user,{"admin"})
    with engine.connect() as con:
        found=con.execute(select(audit).order_by(audit.c.id.desc()).limit(40)).mappings().all()
    return {"events":[{"action":x["action"],"actor":x["actor"],"reference":x["reference"],"created_at":x["created_at"].isoformat() if x["created_at"] else ""} for x in found]}


@app.get("/api/v1/admin/integrations")
def get_integrations(user=Depends(auth)):
    allowed(user,{"admin","sales","ops","viewer"})
    # Static readiness catalog, never implies successful OAuth authorization or publishing.
    return {"integrations":[{
        "id":key,"kind":kind,"name":name,"capability":capability,
        "status":"not_connected","requirement":requirement,"docs":docs,
        "test_status":"not_run"
    } for key,kind,name,capability,requirement,docs in INTEGRATION_REGISTRY],
    "message":"Provider documentation checked; no external channel tokens are configured or tested."}

@app.get("/api/v1/admin/leads")
def get_leads(user=Depends(auth)):
    allowed(user,{"admin","sales","ops","viewer"})
    with engine.connect() as con:
        found=con.execute(select(leads).order_by(leads.c.id.desc()).limit(200)).mappings().all()
    return {"leads":[{
        "id":x["id"],"organization":x["organization"],"website":x["website"],
        "segment":x["segment"],"country":x["country"],"contact_name":x["contact_name"],
        "contact_email":x["contact_email"],"source_url":x["source_url"],
        "notes":x["notes"],"status":x["status"],
        "created_at":x["created_at"].isoformat() if x["created_at"] else ""
    } for x in found]}

@app.post("/api/v1/admin/leads",status_code=201)
def add_lead(payload:LeadCreateInput,user=Depends(auth)):
    allowed(user,{"admin","sales"})
    if not payload.website.startswith(("https://","http://")) or not payload.source_url.startswith(("https://","http://")):
        raise HTTPException(422,"Website and provenance URLs must use HTTP(S)")
    email=str(payload.contact_email).lower() if payload.contact_email else ""
    with engine.begin() as con:
        duplicate=con.execute(select(leads.c.id).where(leads.c.website==payload.website.strip().lower())).first()
        if duplicate: raise HTTPException(409,"Organization website already exists in review queue")
        result=con.execute(leads.insert().values(
            organization=payload.organization.strip(),website=payload.website.strip().lower(),
            segment=payload.segment.strip(),country=payload.country.strip(),
            contact_name=payload.contact_name.strip(),contact_email=email,
            source_url=payload.source_url.strip(),notes=payload.notes.strip(),status="needs_review"))
        ident=result.inserted_primary_key[0]
        con.execute(audit.insert().values(actor=user["email"],action="lead_created",reference=str(ident)))
    return {"id":ident,"status":"needs_review","message":"Lead saved for human review; no outreach sent"}

@app.patch("/api/v1/admin/leads/{lead_id}")
def review_lead(lead_id:int,payload:LeadStatusInput,user=Depends(auth)):
    allowed(user,{"admin","sales"})
    if payload.status not in {"needs_review","qualified","rejected","suppressed"}:
        raise HTTPException(422,"Invalid lead status")
    with engine.begin() as con:
        if not con.execute(select(leads.c.id).where(leads.c.id==lead_id)).first():raise HTTPException(404,"Lead not found")
        con.execute(leads.update().where(leads.c.id==lead_id).values(status=payload.status))
        con.execute(audit.insert().values(actor=user["email"],action="lead_review",reference=str(lead_id)))
    return {"id":lead_id,"status":payload.status,"outreach_sent":False}

@app.get("/api/v1/admin/content-drafts")
def get_content_drafts(user=Depends(auth)):
    allowed(user,{"admin","sales","ops","viewer"})
    with engine.connect() as con:
        found=con.execute(select(content_drafts).order_by(content_drafts.c.created_at.desc()).limit(150)).mappings().all()
    return {"drafts":[{
        "reference":x["id"],"channel":x["channel"],"title":x["title"],"body":x["body"],
        "status":x["status"],"created_at":x["created_at"].isoformat() if x["created_at"] else ""
    } for x in found]}

@app.post("/api/v1/admin/content-drafts",status_code=201)
def create_content_draft(payload:DraftCreateInput,user=Depends(auth)):
    allowed(user,{"admin","sales"})
    known={entry[0] for entry in INTEGRATION_REGISTRY}
    if payload.channel not in known:raise HTTPException(422,"Unknown channel")
    ref=new_reference("CD")
    with engine.begin() as con:
        con.execute(content_drafts.insert().values(id=ref,channel=payload.channel,
            title=payload.title.strip(),body=payload.body.strip(),status="draft"))
        con.execute(audit.insert().values(actor=user["email"],action="draft_created",reference=ref))
    return {"reference":ref,"status":"draft","published":False}

@app.patch("/api/v1/admin/content-drafts/{reference}")
def review_content_draft(reference:str,payload:DraftStatusInput,user=Depends(auth)):
    allowed(user,{"admin"})
    if payload.status not in {"draft","approved","rejected"}:raise HTTPException(422,"Invalid approval status")
    with engine.begin() as con:
        if not con.execute(select(content_drafts.c.id).where(content_drafts.c.id==reference)).first():
            raise HTTPException(404,"Draft not found")
        con.execute(content_drafts.update().where(content_drafts.c.id==reference).values(status=payload.status))
        con.execute(audit.insert().values(actor=user["email"],action="draft_review",reference=reference))
    return {"reference":reference,"status":payload.status,"published":False,
        "message":"Approval saved internally; no external publish integration is configured"}

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


# Register safe, allow-listed AI page design drafts, publishing and rollback.
from cms_brain import register_cms_brain
register_cms_brain(app,engine,DB_SCHEMA,auth,allowed,audit,limit)
