import ast
import hashlib
import pathlib
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
ADDON = ROOT / "businesstogo_connector"


class AddonPackageTests(unittest.TestCase):
    def setUp(self):
        self.manifest = ast.literal_eval((ADDON / "__manifest__.py").read_text())

    def test_manifest_targets_odoo_19_without_automatic_installation(self):
        self.assertEqual(self.manifest["version"], "19.0.1.0.0")
        self.assertEqual(self.manifest["depends"], ["base", "web"])
        self.assertTrue(self.manifest["installable"])
        self.assertFalse(self.manifest["auto_install"])
        self.assertFalse(self.manifest["application"])
        self.assertEqual(self.manifest["license"], "LGPL-3")
        for filename in self.manifest["data"] + self.manifest["images"]:
            self.assertTrue((ADDON / filename).is_file(), filename)

    def test_group_is_explicit_and_does_not_grant_acl_or_internal_status(self):
        tree = ET.parse(ADDON / "security/connector_groups.xml")
        records = tree.findall("record")
        self.assertEqual([r.attrib["model"] for r in records],
                         ["ir.module.category", "res.groups.privilege", "res.groups"])
        group = records[-1]
        self.assertEqual(group.attrib["id"], "group_connector_user")
        fields = {f.attrib["name"] for f in group.findall("field")}
        self.assertNotIn("user_ids", fields)
        self.assertNotIn("implied_ids", fields)
        self.assertNotIn("implied_by_ids", fields)
        self.assertFalse(list(ADDON.rglob("ir.model.access.csv")))

    def test_icon_is_identical_to_erp_source(self):
        data = (ADDON / "static/description/icon.png").read_bytes()
        self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertEqual(hashlib.sha256(data).hexdigest(),
                         "d42f191bbad585284106fb092a6448981874df445b2628fbf8c4cf67758a38c2")

    def test_capabilities_version_matches_manifest(self):
        source = ast.parse((ADDON / "discovery/app/connector.py").read_text())
        model = next(n for n in source.body if isinstance(n, ast.ClassDef))
        method = next(n for n in model.body
                      if isinstance(n, ast.FunctionDef) and n.name == "capabilities")
        response = ast.literal_eval(next(n.value for n in method.body
                                         if isinstance(n, ast.Return)))
        self.assertEqual(response["addon_version"], self.manifest["version"])

    def test_documentation_links_resolve(self):
        for document in [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]:
            for link in re.findall(r"\]\(([^)]+)\)", document.read_text()):
                if "://" not in link and not link.startswith("#"):
                    self.assertTrue((document.parent / link.split("#")[0]).exists(),
                                    f"{document.name}: {link}")

    def test_integration_test_module_is_discoverable_by_odoo(self):
        self.assertIn("test_discovery", (ADDON / "tests/__init__.py").read_text())
        source = ast.parse((ADDON / "tests/test_discovery.py").read_text())
        cases = [n for n in ast.walk(source)
                 if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]
        self.assertGreaterEqual(len(cases), 14)
