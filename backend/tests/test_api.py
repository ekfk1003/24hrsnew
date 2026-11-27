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

def test_store_controls_media_visibility_and_feature_flags():
    login=client.post("/api/v1/admin/login",json={"email":"admin@example.com","password":"unique-password-test-only"})
    assert login.status_code==200,login.text
    h={"Authorization":"Bearer "+login.json()["access_token"]}
    assert client.get("/api/v1/admin/catalog").status_code==401
    cat=client.get("/api/v1/admin/catalog",headers=h)
    assert cat.status_code==200,cat.text
    assert any(p["id"]=="lanyard" for p in cat.json()["products"])
    flags=client.get("/api/v1/admin/features",headers=h)
    assert flags.status_code==200 and len(flags.json()["features"])>=10
    product=client.post("/api/v1/admin/products",headers=h,json={
        "id":"internal-test-hats","name":"Internal Test Hats","category":"Apparel",
        "minimum":40,"unit_cents":220,"description":"Do not fulfill","active":False})
    assert product.status_code==201,product.text
    assert not any(p["id"]=="internal-test-hats" for p in client.get("/api/v1/products").json()["products"])
    assert client.post("/api/v1/quotes",json={"name":"Synthetic Buyer","email":"test@example.com","product_id":"internal-test-hats","quantity":40}).status_code==422
    enable=client.patch("/api/v1/admin/products/internal-test-hats/visibility",headers=h,json={"active":True})
    assert enable.status_code==200,enable.text
    assert any(p["id"]=="internal-test-hats" for p in client.get("/api/v1/products").json()["products"])
    display=client.patch("/api/v1/admin/products/internal-test-hats/display",headers=h,json={
        "description":"Brandable caps","featured":False,"sort_order":5})
    assert display.status_code==200,display.text
    assert next(p for p in client.get("/api/v1/products").json()["products"] if p["id"]=="internal-test-hats")["featured"] is False
    image=client.post("/api/v1/admin/products/internal-test-hats/images",headers=h,json={
        "url":"https://example.org/hats.jpg","alt":"Sample image of hats"})
    assert image.status_code==201,image.text
    photo_id=image.json()["id"]
    record=next(p for p in client.get("/api/v1/products").json()["products"] if p["id"]=="internal-test-hats")
    assert record["photo"]=="https://example.org/hats.jpg"
    assert client.patch("/api/v1/admin/products/internal-test-hats/images/"+str(photo_id)+"/primary",headers=h).status_code==200
    removed=client.delete("/api/v1/admin/products/internal-test-hats/images/"+str(photo_id),headers=h)
    assert removed.status_code==200
    assert not next(p for p in client.get("/api/v1/products").json()["products"] if p["id"]=="internal-test-hats")["photo"]
    assert client.patch("/api/v1/admin/features/unknown",headers=h,json={"enabled":False}).status_code==404
    off=client.patch("/api/v1/admin/features/quotes_enabled",headers=h,json={"enabled":False})
    assert off.status_code==200,off.text
    quote=client.post("/api/v1/quotes",json={
        "name":"Synthetic Buyer","email":"test@example.com","product_id":"internal-test-hats","quantity":40})
    assert quote.status_code==503
    client.patch("/api/v1/admin/features/quotes_enabled",headers=h,json={"enabled":True})
    hidden=client.patch("/api/v1/admin/products/internal-test-hats/visibility",headers=h,json={"active":False})
    assert hidden.status_code==200
    assert not any(p["id"]=="internal-test-hats" for p in client.get("/api/v1/products").json()["products"])

def test_design_studio_draft_approval_and_rollback():
    from fastapi.testclient import TestClient
    auth=client.post("/api/v1/admin/login",json={"email":"admin@example.com","password":"unique-password-test-only"})
    assert auth.status_code==200,auth.text
    headers={"Authorization":"Bearer "+auth.json()["access_token"]}
    before=client.get("/api/v1/site-content")
    assert before.status_code==200
    old=before.json()["pages"]["home"]
    assert client.get("/api/v1/admin/design/status").status_code==401
    status=client.get("/api/v1/admin/design/status",headers=headers)
    assert status.status_code==200
    assert status.json()["requires_approval"] is True
    assert "home" in status.json()["pages"]
    first=client.post("/api/v1/admin/design/manual-draft",headers=headers,json={
        "page":"home","changes":{"hero_title":"A better new test headline.","hero_layout":"centered"},
        "note":"Test only"})
    assert first.status_code==201,first.text
    ref=first.json()["reference"]
    assert first.json()["published"] is False
    unchanged=client.get("/api/v1/site-content").json()["pages"]["home"]
    assert unchanged==old
    drafts=client.get("/api/v1/admin/design/drafts",headers=headers)
    assert drafts.status_code==200
    assert any(x["reference"]==ref for x in drafts.json()["drafts"])
    published=client.post("/api/v1/admin/design/drafts/"+ref+"/publish",headers=headers)
    assert published.status_code==200,published.text
    changed=client.get("/api/v1/site-content").json()["pages"]["home"]
    assert changed["config"]["hero_title"]=="A better new test headline."
    assert changed["config"]["hero_layout"]=="centered"
    assert changed["version"]==old["version"]+1
    assert client.post("/api/v1/admin/design/drafts/"+ref+"/publish",headers=headers).status_code==409
    invalid=client.post("/api/v1/admin/design/manual-draft",headers=headers,json={
        "page":"home","changes":{"hero_title":"<script>alert(1)</script>"}})
    # Text is escaped in the UI, but arbitrary markup must never be processed as code.
    assert invalid.status_code in (201,422)
    forbidden=client.post("/api/v1/admin/design/manual-draft",headers=headers,json={
        "page":"home","changes":{"api_key":"test"}})
    assert forbidden.status_code==422
    history=client.get("/api/v1/admin/design/history/home",headers=headers)
    assert history.status_code==200
    assert any(h["version"]==old["version"] for h in history.json()["versions"])
    restored=client.post("/api/v1/admin/design/rollback/home/"+str(old["version"]),headers=headers)
    assert restored.status_code==200,restored.text
    current=client.get("/api/v1/site-content").json()["pages"]["home"]
    assert current["config"]==old["config"]
    assert current["version"]==old["version"]+2

def test_design_studio_conflict_and_theme_validation():
    auth=client.post("/api/v1/admin/login",json={"email":"admin@example.com","password":"unique-password-test-only"})
    h={"Authorization":"Bearer "+auth.json()["access_token"]}
    invalid=client.post("/api/v1/admin/design/manual-draft",headers=h,json={
        "page":"global","changes":{"primary_color":"url(javascript:evil())"}})
    assert invalid.status_code==422
    one=client.post("/api/v1/admin/design/manual-draft",headers=h,json={
        "page":"cart","changes":{"title":"First draft is old"}})
    two=client.post("/api/v1/admin/design/manual-draft",headers=h,json={
        "page":"cart","changes":{"title":"New cart name"}})
    assert one.status_code==201 and two.status_code==201
    assert client.post("/api/v1/admin/design/drafts/"+two.json()["reference"]+"/publish",headers=h).status_code==200
    assert client.post("/api/v1/admin/design/drafts/"+one.json()["reference"]+"/publish",headers=h).status_code==409
