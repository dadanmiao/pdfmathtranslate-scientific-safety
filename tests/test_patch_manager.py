import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("manager", Path(__file__).resolve().parents[1] / "scripts/manage_patch.py")
manager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manager)


class PatchManagerTests(unittest.TestCase):
    def setUp(self):
        temporary_root = Path(__file__).resolve().parents[1] / "artifacts/deployment-tests"
        temporary_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=temporary_root)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.app = self.root / "app"
        self.bundle = self.root / "patches"
        for package, version in (("pdf2zh_next", "2.9.0"), ("babeldoc", "0.6.4")):
            target = self.app / f"site-packages/{package}-{version}.dist-info/METADATA"
            target.parent.mkdir(parents=True)
            target.write_text(f"Version: {version}\n")
        self.target = self.app / "site-packages/component.py"
        self.target.write_bytes(b"old\n")
        self.manifest = {"app_version": "2.9.0", "babeldoc_version": "0.6.4", "files": []}
        for name, old, new in (("site-packages/component.py", b"old\n", b"new\n"), ("site-packages/helper.py", None, b"helper\n")):
            item = {"path": name, "sha256": hashlib.sha256(new).hexdigest()}
            for folder, content in (("original", old), ("patched", new)):
                if content is not None:
                    file = self.bundle / folder / name
                    file.parent.mkdir(parents=True, exist_ok=True)
                    file.write_bytes(content)
            if old is not None:
                item["original_sha256"] = hashlib.sha256(old).hexdigest()
            else:
                item["new_file"] = True
            self.manifest["files"].append(item)
        self.save_manifest()

    def save_manifest(self):
        (self.bundle / "manifest.json").write_text(json.dumps(self.manifest))

    def test_apply_is_idempotent_and_verifiable(self):
        self.assertEqual(manager.manage(self.app, "apply", self.bundle), 2)
        self.assertEqual(manager.manage(self.app, "apply", self.bundle), 0)
        manager.manage(self.app, "verify", self.bundle)
        self.assertEqual(self.target.read_bytes(), b"new\n")

    def test_restores_baseline_and_removes_added_module(self):
        manager.manage(self.app, "apply", self.bundle)
        manager.manage(self.app, "restore", self.bundle)
        self.assertEqual(self.target.read_bytes(), b"old\n")
        self.assertFalse((self.app / "site-packages/helper.py").exists())
        self.assertTrue(list((self.app.parent / "patch-backups").rglob("component.py")))

    def test_unknown_local_edit_refuses_entire_batch(self):
        (self.app / "site-packages/helper.py").write_bytes(b"personal edit")
        with self.assertRaises(ValueError):
            manager.manage(self.app, "apply", self.bundle)
        self.assertEqual(self.target.read_bytes(), b"old\n")

    def test_corrupt_payload_refuses_entire_batch(self):
        (self.bundle / "patched/site-packages/helper.py").write_bytes(b"corrupt")
        with self.assertRaises(ValueError):
            manager.manage(self.app, "apply", self.bundle)
        self.assertEqual(self.target.read_bytes(), b"old\n")

    def test_known_previous_patch_can_be_upgraded(self):
        previous = b'previous patch\n'
        self.target.write_bytes(previous)
        self.manifest['files'][0]['previous_sha256'] = [hashlib.sha256(previous).hexdigest()]
        self.save_manifest()
        manager.manage(self.app, 'apply', self.bundle)
        self.assertEqual(self.target.read_bytes(), b'new\n')

    def test_other_release_is_refused(self):
        metadata = self.app / "site-packages/babeldoc-0.6.4.dist-info/METADATA"
        metadata.write_text("Version: 0.7.0\n")
        with self.assertRaises(ValueError):
            manager.manage(self.app, "apply", self.bundle)
        self.assertEqual(self.target.read_bytes(), b"old\n")

    def test_path_escape_is_refused(self):
        self.manifest["files"][0]["path"] = "../outside.py"
        self.save_manifest()
        with self.assertRaises(ValueError):
            manager.manage(self.app, "apply", self.bundle)

    def test_repository_payload_hashes_match_manifest(self):
        bundle = Path(__file__).resolve().parents[1] / "patches"
        manifest = json.loads((bundle / "manifest.json").read_text("utf-8"))
        for item in manifest["files"]:
            self.assertEqual(manager.digest(bundle / "patched" / item["path"]), item["sha256"])
            if "original_sha256" in item:
                self.assertEqual(manager.digest(bundle / "original" / item["path"]), item["original_sha256"])

    def test_full_patch_applies_to_official_baseline_and_restores(self):
        bundle = Path(__file__).resolve().parents[1] / "patches"
        manifest = json.loads((bundle / "manifest.json").read_text("utf-8"))
        for item in manifest["files"]:
            if "original_sha256" in item:
                target = manager.inside(self.app, item["path"])
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((bundle / "original" / item["path"]).read_bytes())
        manager.manage(self.app, "apply", bundle)
        manager.manage(self.app, "verify", bundle)
        manager.manage(self.app, "restore", bundle)
        for item in manifest["files"]:
            target = manager.inside(self.app, item["path"])
            self.assertEqual(manager.digest(target), item.get("original_sha256"))


if __name__ == "__main__":
    unittest.main()
