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
