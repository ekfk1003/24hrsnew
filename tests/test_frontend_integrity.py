"""Static frontend integrity checks; these do not substitute for browser E2E tests."""
from html.parser import HTMLParser
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]

class Document(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids=[]
        self.refs=[]
        self.scripts=[]
        self.in_script=False
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if "id" in a:self.ids.append(a["id"])
        if tag=="script":
            if a.get("src"):self.refs.append(a["src"])
            else:self.in_script=True;self.scripts.append("")
        if tag=="link" and a.get("href"):self.refs.append(a["href"])
    def handle_data(self, data):
        if self.in_script:self.scripts[-1]+=data
    def handle_endtag(self, tag):
        if tag=="script":self.in_script=False

class FrontendContract(unittest.TestCase):
    def parse(self,path):
        doc=Document();doc.feed((ROOT/path).read_text(encoding="utf-8"));return doc
    def test_admin_references_exist(self):
        doc=self.parse("admin.html")
        self.assertEqual(len(doc.ids),len(set(doc.ids)),"Duplicate HTML IDs")
        for ident in ["dashboard","hqNav","loginForm","records","showQuotes","showOrders","showContacts","showProducts","showTest","showAudit","showReference","role","logout"]:
            self.assertIn(ident,doc.ids)
        for filename in ["config.js","./hq-experience.css","./hq-experience.js"]:
            self.assertIn(filename,doc.refs)
            self.assertTrue((ROOT/filename).exists())
    def test_storefront_real_api_configuration(self):
        config=(ROOT/"config.js").read_text()
        self.assertIn("https://two4hrsnew.onrender.com",config)
        self.assertNotIn("postgresql://",config)
        self.assertNotIn("JWT_SECRET=",config)
        doc=self.parse("index.html")
        self.assertIn("config.js",doc.refs)
    def test_frontend_script_syntax(self):
        for path in ["admin.html","index.html"]:
            doc=self.parse(path)
            with TemporaryDirectory() as tmp:
                for i,js in enumerate(doc.scripts):
                    p=Path(tmp)/f"inline_{i}.js"
                    p.write_text(js,encoding="utf-8")
                    subprocess.run(["node","--check",str(p)],check=True,capture_output=True,text=True)
        subprocess.run(["node","--check",str(ROOT/"hq-experience.js")],check=True,capture_output=True,text=True)
    def test_admin_ui_module_routing(self):
        s=(ROOT/"hq-experience.js").read_text()
        for route in ["showQuotes","showOrders","showContacts","showProducts","showTest","showAudit","system","artwork","vendors","production","payments","marketing","security"]:
            self.assertIn(route,s)
        self.assertIn("dashboard.insertBefore(menu,nav)",s,"Mobile menu must stay in hidden auth workspace")
    def test_no_payment_claim(self):
        s=(ROOT/"index.html").read_text()
        self.assertIn("proof",s.lower())
        self.assertIn("no payments",s.lower())

if __name__=="__main__":
    unittest.main()
