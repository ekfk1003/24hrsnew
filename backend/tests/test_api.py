import os
import tempfile
from pathlib import Path
os.environ["DATABASE_URL"]="sqlite:///"+str(Path(tempfile.mkdtemp())/"test.db")
os.environ["ADMIN_EMAIL"]="admin@example.com"
os.environ["ADMIN_PASSWORD"]="unique-password-test-only"
os.environ["JWT_SECRET"]="0123456789abcdef0123456789abcdef01234567"
from fastapi.testclient import TestClient
from app import app
client=TestClient(app)
def test_product_catalog():
    assert client.get("/health").json()["status"]=="ok"
    assert len(client.get("/api/v1/products").json()["products"])==8
def test_quote_order_admin_flow():
    details={"name":"Example Buyer","email":"buyer@example.com"}
    assert client.post("/api/v1/quotes",json={**details,"product_id":"lanyard","quantity":3}).status_code==422
    quote=client.post("/api/v1/quotes",json={**details,"product_id":"lanyard","quantity":100})
    assert quote.status_code==201,quote.text
    order=client.post("/api/v1/orders",json={**details,"items":[{"product_id":"lanyard","quantity":100}]})
    assert order.status_code==201,order.text
    assert client.get("/api/v1/admin/dashboard").status_code==401
    login=client.post("/api/v1/admin/login",json={"email":"admin@example.com","password":"unique-password-test-only"})
    assert login.status_code==200,login.text
    headers={"Authorization":"Bearer "+login.json()["access_token"]}
    dashboard=client.get("/api/v1/admin/dashboard",headers=headers)
    assert dashboard.status_code==200,dashboard.text
    assert dashboard.json()["contacts"]==1
    assert len(client.get("/api/v1/admin/quotes",headers=headers).json()["quotes"])==1
    assert len(client.get("/api/v1/admin/orders",headers=headers).json()["orders"])==1
    assert client.patch("/api/v1/admin/orders/"+order.json()["reference"],headers=headers,json={"status":"reviewing"}).status_code==200

def test_authenticated_catalog_edit_and_contacts():
    assert client.patch("/api/v1/admin/products/lanyard",json={"name":"Edited Lanyard","minimum":200,"unit_cents":105}).status_code==401
    login=client.post("/api/v1/admin/login",json={"email":"admin@example.com","password":"unique-password-test-only"})
    assert login.status_code==200
    headers={"Authorization":"Bearer "+login.json()["access_token"]}
    changed=client.patch("/api/v1/admin/products/lanyard",headers=headers,json={"name":"Edited Lanyard","minimum":200,"unit_cents":105})
    assert changed.status_code==200,changed.text
    product=next(p for p in client.get("/api/v1/products").json()["products"] if p["id"]=="lanyard")
    assert product["name"]=="Edited Lanyard"
    assert product["minimum"]==200
    assert product["estimate_unit_usd"]=="1.05"
    refused=client.post("/api/v1/quotes",json={"name":"Test Buyer","email":"test-buyer@example.com","product_id":"lanyard","quantity":100})
    assert refused.status_code==422
    quoted=client.post("/api/v1/quotes",json={"name":"Test Buyer","email":"test-buyer@example.com","product_id":"lanyard","quantity":200})
    assert quoted.status_code==201,quoted.text
    contacts=client.get("/api/v1/admin/contacts",headers=headers)
    assert contacts.status_code==200
    assert any(c["email"]=="test-buyer@example.com" for c in contacts.json()["contacts"])
    audit=client.get("/api/v1/admin/audit",headers=headers)
    assert audit.status_code==200
    assert any(e["action"]=="product_update" for e in audit.json()["events"])

def test_saas_registry_and_review_workflows():
    # All provider states must remain unconnected absent OAuth and live checks.
    assert client.get("/api/v1/admin/integrations").status_code==401
    login=client.post("/api/v1/admin/login",json={"email":"admin@example.com","password":"unique-password-test-only"})
    assert login.status_code==200,login.text
    headers={"Authorization":"Bearer "+login.json()["access_token"]}
    registry=client.get("/api/v1/admin/integrations",headers=headers)
    assert registry.status_code==200,registry.text
    connections=registry.json()["integrations"]
    assert len(connections)>=20
    assert all(i["status"]=="not_connected" and i["test_status"]=="not_run" for i in connections)
    assert {"shopify","woocommerce","instagram","linkedin","getresponse","whatsapp_channel"}.issubset({i["id"] for i in connections})
    lead={"organization":"Sample School Test","website":"https://example.org","segment":"Schools & universities","source_url":"https://example.org/about","notes":"Synthetic test lead. No outreach."}
    assert client.post("/api/v1/admin/leads",json=lead).status_code==401
    made=client.post("/api/v1/admin/leads",headers=headers,json=lead)
    assert made.status_code==201,made.text
    lead_id=made.json()["id"]
    assert made.json()["status"]=="needs_review"
    assert client.post("/api/v1/admin/leads",headers=headers,json=lead).status_code==409
    saved=client.get("/api/v1/admin/leads",headers=headers)
    assert saved.status_code==200 and any(i["id"]==lead_id for i in saved.json()["leads"])
    updated=client.patch("/api/v1/admin/leads/"+str(lead_id),headers=headers,json={"status":"qualified"})
    assert updated.status_code==200 and updated.json()["outreach_sent"] is False
    draft=client.post("/api/v1/admin/content-drafts",headers=headers,json={"channel":"linkedin","title":"Synthetic social campaign","body":"This is an internal draft; nothing should be published."})
    assert draft.status_code==201,draft.text
    ref=draft.json()["reference"]
    assert draft.json()["published"] is False
    assert client.post("/api/v1/admin/content-drafts",headers=headers,json={"channel":"unknown","title":"Not supported","body":"Bad channel example."}).status_code==422
    review=client.patch("/api/v1/admin/content-drafts/"+ref,headers=headers,json={"status":"approved"})
    assert review.status_code==200 and review.json()["published"] is False
    list_result=client.get("/api/v1/admin/content-drafts",headers=headers)
    assert any(d["reference"]==ref and d["status"]=="approved" for d in list_result.json()["drafts"])
