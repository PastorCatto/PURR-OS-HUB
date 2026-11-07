"""Self-test for hubsign.py: python3 tools/test_hubsign.py  (needs the cryptography package; makes a throwaway key, touches nothing in the repository)."""
import hashlib
import json
import os
import shutil
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hubsign as hs  # noqa: E402


def package(name, version, itype=hs.IMG_MODULE, subtype=hs.MOD_SHELL, signed=True, payload=b"payload-bytes" * 20, key_id=5):
    sig = b"\x11" * 64 if signed else b"\0" * 64
    head = struct.pack(hs.HEADER_FORMAT, hs.MAGIC, 1, hs.HEADER_SIZE, 9, itype, key_id, subtype if itype != hs.IMG_APP else 0, name.encode(), version.encode(), b"",
                       hs.HEADER_SIZE, len(payload), hashlib.sha256(payload).digest(), sig)
    return head + payload


class HubSign(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        hs.ROOT = self.tmp
        self.folder = os.path.join(self.tmp, "repos", "ui")
        os.makedirs(os.path.join(self.folder, "items"))
        with open(os.path.join(self.folder, "repo.toml"), "w") as fh:
            fh.write('[repo]\nname = "Test"\ndescription = "d"\nmaintainer = "m"\nurl = "https://example.org"\nmin_os = "1.0.0"\nendorse_key_id = 5\n')
        self.add("w10m", "1.0.32", package("w10m", "1.0.32"))
        os.environ["PURRHUB_KEY_PASSWORD"] = "test-pass-1"
        self.key = os.path.join(self.tmp, "signing_keys", "hub.key")
        self.pub = hs.keygen(self.key)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def add(self, name, version, data, kind="shell", extra=""):
        with open(os.path.join(self.folder, "%s-%s.cat" % (name, version)), "wb") as fh:
            fh.write(data)
        with open(os.path.join(self.folder, "items", name + ".toml"), "w") as fh:
            fh.write('[item]\nname = "%s"\nversion = "%s"\ntype = "%s"\ntitle = "T"\ndesc = "d"\ndest = "shell.cat"\nmin_os = "1.0.32"\nperms = []\n%s' % (name, version, kind, extra))

    def build(self):
        return hs.main(["build", "--key", self.key, "--now", "1000"])

    def test_build_and_check(self):
        self.assertEqual(self.build(), 0)
        self.assertEqual(hs.main(["check", "--strict"]), 0)
        repo = json.load(open(os.path.join(self.folder, "repo.json")))
        index = json.load(open(os.path.join(self.folder, "index.json")))
        self.assertEqual(repo["id"], hs.fingerprint(self.pub))
        self.assertEqual(index["apps"][0]["sha256"], hashlib.sha256(open(os.path.join(self.folder, "w10m-1.0.32.cat"), "rb").read()).hexdigest())
        self.assertEqual(index["apps"][0]["url"], "w10m-1.0.32.cat")
        self.assertTrue(index["apps"][0]["signed"])
        # the endorsement is over "PURRREPO\0" + SHA-256(pub), as a device checks it
        end = repo["endorsement"]
        self.assertEqual(end["key_id"], 5)
        self.assertTrue(hs.verify_bytes(self.pub, hs.ENDORSE_PREFIX + hashlib.sha256(self.pub).digest(), bytes.fromhex(end["sig"])))

    def test_build_twice_changes_nothing(self):
        self.build()
        before = {f: open(os.path.join(self.folder, f), "rb").read() for f in ("repo.json", "repo.json.sig", "index.json", "index.json.sig")}
        hs.main(["build", "--key", self.key, "--now", "5000"])
        after = {f: open(os.path.join(self.folder, f), "rb").read() for f in before}
        self.assertEqual(before, after)

    def test_a_changed_package_is_noticed(self):
        self.build()
        with open(os.path.join(self.folder, "w10m-1.0.32.cat"), "ab") as fh:
            fh.write(b"x")
        self.assertEqual(hs.main(["check"]), 0)                # still readable, but the index no longer matches
        out = hs.main(["check", "--strict"])
        self.assertEqual(out, 1)

    def test_bad_signature_is_a_problem(self):
        self.build()
        with open(os.path.join(self.folder, "index.json"), "ab") as fh:
            fh.write(b" ")
        self.assertEqual(hs.main(["check"]), 1)

    def test_unsigned_shell_refused(self):
        self.add("w10m", "1.0.32", package("w10m", "1.0.32", signed=False))
        self.assertEqual(self.build(), 1)
        self.assertFalse(os.path.exists(os.path.join(self.folder, "index.json")))

    def test_version_mismatch_and_damage_refused(self):
        self.add("w10m", "1.0.33", package("w10m", "1.0.32"))
        self.assertEqual(hs.main(["check"]), 1)
        data = bytearray(package("w10m", "1.0.32"))
        data[-1] ^= 1
        self.add("w10m", "1.0.32", bytes(data))
        os.remove(os.path.join(self.folder, "w10m-1.0.33.cat"))
        self.assertEqual(hs.main(["check"]), 1)

    def test_shell_is_not_a_driver_or_an_app(self):
        self.add("w10m", "1.0.32", package("w10m", "1.0.32", subtype=5))
        self.assertEqual(hs.main(["check"]), 1)
        self.add("clock", "1.0.0", package("clock", "1.0.0", itype=hs.IMG_APP), kind="app")
        os.remove(os.path.join(self.folder, "w10m-1.0.32.cat"))
        os.remove(os.path.join(self.folder, "items", "w10m.toml"))
        self.assertEqual(hs.main(["check"]), 0)

    def test_packages_may_sit_in_subfolders(self):
        os.makedirs(os.path.join(self.folder, "shells"))
        os.rename(os.path.join(self.folder, "w10m-1.0.32.cat"), os.path.join(self.folder, "shells", "w10m-1.0.32.cat"))
        self.assertEqual(self.build(), 0)
        self.assertEqual(hs.main(["check", "--strict"]), 0)
        index = json.load(open(os.path.join(self.folder, "index.json")))
        self.assertEqual(index["apps"][0]["url"], "shells/w10m-1.0.32.cat")
        # the same package twice (root and subfolder) is ambiguous
        shutil.copy(os.path.join(self.folder, "shells", "w10m-1.0.32.cat"), os.path.join(self.folder, "w10m-1.0.32.cat"))
        self.assertEqual(hs.main(["check"]), 1)
        # a path a device would refuse (a hidden folder) is not searched
        os.remove(os.path.join(self.folder, "w10m-1.0.32.cat"))
        os.rename(os.path.join(self.folder, "shells"), os.path.join(self.folder, ".hidden"))
        self.assertEqual(hs.main(["check"]), 1)

    def test_item_without_package_and_bad_name(self):
        os.remove(os.path.join(self.folder, "w10m-1.0.32.cat"))
        self.assertEqual(hs.main(["check"]), 1)
        self.add("W10M", "1.0.32", package("w10m", "1.0.32"))
        self.assertEqual(hs.main(["check"]), 1)

    def test_a_fork_without_endorsement(self):
        with open(os.path.join(self.folder, "repo.toml"), "w") as fh:
            fh.write('[repo]\nname = "Fork"\nurl = "https://example.org/fork"\n')
        self.assertEqual(self.build(), 0)
        self.assertNotIn("endorsement", json.load(open(os.path.join(self.folder, "repo.json"))))

    def test_fields_longer_than_the_device_keeps_are_refused(self):
        self.add("w10m", "1.0.32", package("w10m", "1.0.32"), extra='')
        path = os.path.join(self.folder, "items", "w10m.toml")
        text = open(path).read().replace('desc = "d"', 'desc = "%s"' % ("x" * 80))
        open(path, "w").write(text)
        self.assertEqual(hs.main(["check"]), 1)
        open(path, "w").write(text.replace("x" * 80, "x" * 79))
        self.assertEqual(hs.main(["check"]), 0)

    def test_version_the_device_cannot_read(self):
        self.add("w10m", "1.0_32", package("w10m", "1.0_32"))
        self.assertEqual(hs.main(["check"]), 1)

    def test_one_key_is_one_repository(self):
        self.assertEqual(self.build(), 0)
        other = os.path.join(self.tmp, "repos", "games")
        os.makedirs(os.path.join(other, "items"))
        with open(os.path.join(other, "repo.toml"), "w") as fh:
            fh.write('[repo]\nname = "Games"\n')
        self.assertEqual(hs.main(["build", "--key", self.key, "--only", "games", "--now", "1000"]), 1)   # the same key already signs repos/ui
        self.assertEqual(hs.main(["build", "--key", self.key, "--now", "1000"]), 1)                       # two folders in one run
        self.assertFalse(os.path.exists(os.path.join(other, "repo.json")))

    def test_check_finds_two_folders_with_one_key(self):
        self.build()
        other = os.path.join(self.tmp, "repos", "games")
        os.makedirs(os.path.join(other, "items"))
        shutil.copy(os.path.join(self.folder, "repo.toml"), os.path.join(other, "repo.toml"))
        shutil.copy(os.path.join(self.folder, "repo.json"), os.path.join(other, "repo.json"))
        self.assertEqual(hs.main(["check", "--only", "ui"]), 1)

    def test_wrong_passphrase(self):
        os.environ["PURRHUB_KEY_PASSWORD"] = "nope-nope"
        self.assertEqual(self.build(), 1)

    def test_keygen_never_overwrites(self):
        with self.assertRaises(hs.HubError):
            hs.keygen(self.key)


if __name__ == "__main__":
    unittest.main()
