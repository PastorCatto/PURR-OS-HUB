#!/usr/bin/env python3
"""hubsign: check and sign the repositories in repos/.

This one file is all it takes to run a store like this one, so anyone can fork the hub and recreate it with their own key.
It needs Python 3.9 or newer and the `cryptography` package. It does not need the firmware repository.

  python3 tools/hubsign.py keygen            make this store's key (signing_keys/hub.key, which git ignores)
  python3 tools/hubsign.py check             look at every repository: items, packages, sizes, existing signatures. Needs no key.
  python3 tools/hubsign.py build             check, then rewrite repo.json and index.json (and their .sig files) with the key

A repository is a folder repos/<name>/ with a repo.toml, the packages, and items/<name>.toml next to each (the small description of one package).
A device knows a repository by its key, so every repository needs its OWN key: two folders signed with one key would be the same repository on a device.
`build` therefore signs one folder per run (--only <name>) and refuses a key that already signs another folder.
The format is Repositories/SPEC.md in the firmware repository (https://github.com/PastorCatto/PURR-OS-ESP32). The key's passphrase is asked for,
or taken from PURRHUB_KEY_PASSWORD in the environment of the one command; it is never written anywhere.
"""

import argparse
import getpass
import hashlib
import json
import os
import re
import struct
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORMAT = 2
ENDORSE_PREFIX = b"PURRREPO\0"
MAX_INDEX = 24 * 1024                 # a device refuses an index over 24 KB
MAX_SHELL = 1024 * 1024               # a device loads at most 1 MB as a shell
MAX_THEME = 4 * 1024 * 1024
MAX_PACKAGE = 16 * 1024 * 1024
TYPES = ("app", "asset", "extra", "theme", "shell")
TARGETS = ("flash", "sd", "any")
MOD_SHELL = 11                        # the module subtype of a loadable shell
IMG_MODULE, IMG_APP = 3, 4
MAGIC = 0x50555252                    # the package header, as in the firmware's purrstrap/lib/image.py
HEADER_FORMAT = "<IBHHBBH32s12s12sII32s64s"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,30}$")
VERSION_RE = re.compile(r"^[0-9][0-9A-Za-z.+-]{0,14}$")                # a device reads at most 15 characters and no underscore
URL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,94}$")              # a device refuses a longer path, one starting with a dot, ".." or "//"
# The longest text a device keeps for each field (its buffer less the end mark). A longer one makes the device drop the WHOLE entry: it would never be offered.
FIELD_MAX = {"title": 31, "desc": 79, "category": 15, "min_os": 11, "dest": 63, "chip": 11}
PERM_MAX = 23
NOT_PACKAGES = (".json", ".sig", ".toml", ".md", ".txt")


class HubError(Exception):
    pass


# ------------------------------------------------------------------------------------------------------------------ small readers

def _strip_comment(line):
    out, quote, esc = [], None, False
    for ch in line:
        if quote:
            out.append(ch)
            if esc:
                esc = False
            elif ch == "\\" and quote == '"':
                esc = True
            elif ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            out.append(ch)
        elif ch == "#":
            break
        else:
            out.append(ch)
    return "".join(out).strip()


def load_toml(path):
    """A table of key = value lines. Python 3.11+ reads it with tomllib; before that this reads the subset the item files use
    (tables, "strings", integers, true/false, flat arrays)."""
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    try:
        import tomllib
        return tomllib.loads(text)
    except ImportError:
        pass
    out, cur = {}, None
    for n, raw in enumerate(text.splitlines(), 1):
        line = _strip_comment(raw)
        if not line:
            continue
        if line.startswith("[") and line.endswith("]") and not line.startswith("[["):
            cur = out.setdefault(line[1:-1].strip(), {})
            continue
        if "=" not in line or cur is None:
            raise HubError("%s line %d: I expected [table] and key = value lines." % (path, n))
        key, val = line.split("=", 1)
        try:
            cur[key.strip()] = json.loads(val.strip())
        except ValueError:
            raise HubError("%s line %d: I could not read the value %r (use \"double quotes\")." % (path, n, val.strip()))
    return out


def package_info(data):
    """What the package header says (the same facts the firmware's SDK reads). {} if it is not a PURR package."""
    if len(data) < HEADER_SIZE or struct.unpack_from("<I", data, 0)[0] != MAGIC:
        return {}
    (_m, _v, _hs, chip, itype, key_id, flags, name, version, _mb, poff, psize, phash, sig) = struct.unpack_from(HEADER_FORMAT, data, 0)
    return {"type": "app" if itype == IMG_APP else "module", "chip": {9: "esp32s3", 0: "esp32", 0xFFFF: "any"}.get(chip, "any"), "key_id": key_id,
            "signed": sig not in (b"\0" * 64, b"\xff" * 64), "subtype": (flags & 0xFF) if itype != IMG_APP else 0,
            "name": name.rstrip(b"\0").decode("ascii", "replace"), "version": version.rstrip(b"\0").decode("ascii", "replace"),
            "payload_ok": data[poff:poff + psize] != b"" and len(data) >= poff + psize and hashlib.sha256(data[poff:poff + psize]).digest() == phash}


# ------------------------------------------------------------------------------------------------------------------ keys and signatures

def _crypto():
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec, utils
    except ImportError:
        raise HubError("This needs the cryptography package (pip install cryptography).")
    return hashes, serialization, ec, utils


def raw_pub(public_key):
    n = public_key.public_numbers()
    return n.x.to_bytes(32, "big") + n.y.to_bytes(32, "big")


def fingerprint(pub):
    return hashlib.sha256(pub).hexdigest()[:16]


def sign_bytes(priv, data):
    """Raw 64-byte r||s over SHA-256 of data."""
    hashes, _s, ec, utils = _crypto()
    der = priv.sign(hashlib.sha256(data).digest(), ec.ECDSA(utils.Prehashed(hashes.SHA256())))
    r, s = utils.decode_dss_signature(der)
    return r.to_bytes(32, "big") + s.to_bytes(32, "big")


def verify_bytes(pub, data, sig):
    hashes, _s, ec, utils = _crypto()
    if len(pub) != 64 or len(sig) != 64:
        return False
    try:
        key = ec.EllipticCurvePublicNumbers(int.from_bytes(pub[:32], "big"), int.from_bytes(pub[32:], "big"), ec.SECP256R1()).public_key()
        key.verify(utils.encode_dss_signature(int.from_bytes(sig[:32], "big"), int.from_bytes(sig[32:], "big")), data, ec.ECDSA(hashes.SHA256()))
        return True
    except Exception:
        return False


def _password(prompt="Passphrase for the key: "):
    pw = os.environ.get("PURRHUB_KEY_PASSWORD")
    return pw if pw else getpass.getpass(prompt)


def load_private(path):
    _h, serialization, _e, _u = _crypto()
    if not os.path.isfile(path):
        raise HubError("There is no key at %s. `hubsign.py keygen` makes one, or point --key at yours." % path)
    pw = _password()
    try:
        with open(path, "rb") as fh:
            return serialization.load_pem_private_key(fh.read(), pw.encode() if pw else None)
    except Exception as e:
        raise HubError("I could not open the key %s (wrong passphrase?): %s" % (path, e))


def keygen(path):
    _h, serialization, ec, _u = _crypto()
    if os.path.exists(path):
        raise HubError("%s already exists. I will not overwrite a key." % path)
    pw = _password("Choose a passphrase (at least 6 characters): ")
    if len(pw) < 6:
        raise HubError("Pick a passphrase of at least 6 characters: it protects the private key.")
    if "PURRHUB_KEY_PASSWORD" not in os.environ and getpass.getpass("Again: ") != pw:
        raise HubError("The two passphrases differ.")
    priv = ec.generate_private_key(ec.SECP256R1())
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as fh:
        fh.write(priv.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.BestAvailableEncryption(pw.encode())))
    pub = raw_pub(priv.public_key())
    base = os.path.splitext(path)[0]
    with open(base + ".pub", "wb") as fh:
        fh.write(priv.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    with open(base + ".pub.bin", "wb") as fh:
        fh.write(pub)
    return pub


# ------------------------------------------------------------------------------------------------------------------ a repository

def _check_dest(dest):
    parts = dest.split("/")
    return not (dest.startswith("/") or "\\" in dest or any(p in ("", ".", "..") for p in parts) or len(dest) > 80)


def repositories(only=None):
    base = os.path.join(ROOT, "repos")
    out = []
    for kind in sorted(os.listdir(base)) if os.path.isdir(base) else []:
        folder = os.path.join(base, kind)
        if os.path.isfile(os.path.join(folder, "repo.toml")) and (not only or kind in only):
            out.append((kind, folder))
    return out


def read_items(folder):
    """Returns (items, problems, warnings). items: [{"file", "data", "item", "info"}] sorted by package file name."""
    problems, warnings, items = [], [], []
    idir = os.path.join(folder, "items")
    files = sorted(f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f)) and not f.endswith(NOT_PACKAGES) and not f.startswith("."))
    used = set()
    for t in sorted(os.listdir(idir)) if os.path.isdir(idir) else []:
        if not t.endswith(".toml"):
            continue
        where = "items/" + t
        try:
            item = load_toml(os.path.join(idir, t)).get("item")
        except HubError as e:
            problems.append(str(e))
            continue
        if not isinstance(item, dict):
            problems.append("%s: there is no [item] table." % where)
            continue
        name, version, kind = str(item.get("name", "")), str(item.get("version", "")), item.get("type", "app")
        if not NAME_RE.match(name) or name != t[:-5]:
            problems.append("%s: the name %r must be lower-case letters, digits, - or _ (at most 31) and equal the file name." % (where, name))
            continue
        if not VERSION_RE.match(version):
            problems.append("%s: the version %r is not a plain version like 1.2.0." % (where, version))
            continue
        if kind not in TYPES:
            problems.append("%s: type is one of %s." % (where, ", ".join(TYPES)))
            continue
        if item.get("target", "flash") not in TARGETS:
            problems.append("%s: target is one of %s." % (where, ", ".join(TARGETS)))
            continue
        for field, longest in sorted(FIELD_MAX.items()):
            if len(str(item.get(field, ""))) > longest:
                problems.append("%s: %s is %d characters; a device keeps at most %d and would drop the whole entry." % (where, field, len(str(item[field])), longest))
        for perm in item.get("perms", []) or []:
            if len(str(perm)) > PERM_MAX:
                problems.append("%s: the permission %r is longer than %d characters." % (where, perm, PERM_MAX))
        matches = [f for f in files if f.startswith("%s-%s." % (name, version))]
        if len(matches) != 1:
            problems.append("%s: I need exactly one package file named %s-%s.<ext> next to repo.toml (found %d)." % (where, name, version, len(matches)))
            continue
        fname = matches[0]
        used.add(fname)
        if not URL_RE.match(fname) or ".." in fname or "//" in fname:
            problems.append("%s: the package file name %s is not one a device accepts (letters, digits, . _ - only, at most 95)." % (where, fname))
        with open(os.path.join(folder, fname), "rb") as fh:
            data = fh.read()
        info = package_info(data)
        p = problems.append
        if len(data) > MAX_PACKAGE:
            p("%s: %s is over 16 MB." % (where, fname))
        if info:
            if info["name"] != name and kind in ("app", "shell"):
                p("%s: the package says its name is %r." % (where, info["name"]))
            if info["version"] != version:
                p("%s: the package says its version is %r, the item says %r." % (where, info["version"], version))
            if not info["payload_ok"]:
                p("%s: %s is damaged (its payload does not match its header)." % (where, fname))
        if kind == "app" and info.get("type") != "app":
            p("%s: an app must be a PURR app package." % where)
        if kind == "shell":
            if info.get("type") != "module" or info.get("subtype") != MOD_SHELL:
                p("%s: a shell must be a loadable shell module." % where)
            elif not info.get("signed"):
                p("%s: a shell must be signed: a device loads one only if a key it trusts for shells signed it." % where)
            if len(data) > MAX_SHELL:
                p("%s: a shell is at most 1 MB." % where)
            if item.get("dest") != "shell.cat":
                p("%s: a shell has dest = \"shell.cat\"." % where)
        elif info.get("type") == "module":
            p("%s: a module or a driver is not an item of a repository." % where)
        if kind == "theme" and (item.get("dest") != "pack.bin" or len(data) > MAX_THEME):
            p("%s: a theme has dest = \"pack.bin\" and is at most 4 MB." % where)
        if kind not in ("app", "shell") and not _check_dest(str(item.get("dest", ""))):
            p("%s: dest must be a plain relative path like fonts/mono.bin." % where)
        items.append({"file": fname, "data": data, "item": item, "info": info})
    for f in files:
        if f not in used:
            warnings.append("%s is in the folder but no item describes it." % f)
    seen = {}
    for it in items:
        key = it["item"]["name"]
        seen[key] = seen.get(key, 0) + 1
    for key, n in seen.items():
        if n > 2:
            warnings.append("%s has %d versions; keep the current and the previous one." % (key, n))
    items.sort(key=lambda i: i["file"])
    return items, problems, warnings


def make_files(folder, items, pub, now, old_index=None, old_repo=None, endorser=None):
    """The bytes of repo.json and index.json. `updated` of an entry stays as it was while the package is unchanged, so building twice changes nothing."""
    meta = load_toml(os.path.join(folder, "repo.toml")).get("repo", {})
    rid = fingerprint(pub)
    old_up = {}
    for a in (old_index or {}).get("apps", []):
        old_up[(a.get("name"), a.get("version"), a.get("sha256"))] = a.get("updated")
    apps = []
    for it in items:
        item, info, data = it["item"], it["info"], it["data"]
        sha = hashlib.sha256(data).hexdigest()
        name, version, kind = item["name"], item["version"], item.get("type", "app")
        entry = {"name": name, "title": item.get("title") or name, "version": version, "type": kind, "target": item.get("target", "flash"), "size": len(data),
                 "sha256": sha, "chip": item.get("chip") or info.get("chip", "any"), "signed": bool(info.get("signed")), "key_id": info.get("key_id", 0),
                 "desc": item.get("desc", ""), "url": it["file"], "updated": old_up.get((name, version, sha)) or now}
        for k in ("category", "source", "min_os", "changelog", "dest"):
            if item.get(k):
                entry[k] = item[k]
        if item.get("perms"):
            entry["perms"] = list(item["perms"])
        if item.get("needs_sd"):
            entry["needs_sd"] = 1
        apps.append(entry)
    updated = max([a["updated"] for a in apps] or [(old_repo or {}).get("updated") or now])
    repo = {"format": FORMAT, "id": rid, "name": meta.get("name", ""), "description": meta.get("description", ""), "maintainer": meta.get("maintainer", ""),
            "url": meta.get("url", ""), "key": {"alg": "p256", "pub": pub.hex()}, "min_os": meta.get("min_os", "1.0.0"), "layout": "flat", "updated": updated}
    if endorser is not None:
        repo["endorsement"] = endorser
    index = {"format": FORMAT, "repo": {"id": rid, "name": repo["name"], "kind": "store"}, "apps": apps}
    return json.dumps(repo, separators=(",", ":")).encode(), json.dumps(index, separators=(",", ":")).encode(), index


def _read_json(path):
    try:
        with open(path, "rb") as fh:
            return json.loads(fh.read())
    except (OSError, ValueError):
        return None


def _read_bytes(path):
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError:
        return None


def check_signatures(folder):
    """Existing repo.json / index.json against the key in repo.json. Returns (problems, warnings)."""
    problems, warnings = [], []
    rb, ib = _read_bytes(os.path.join(folder, "repo.json")), _read_bytes(os.path.join(folder, "index.json"))
    if rb is None and ib is None:
        return problems, ["not signed yet (no repo.json); `build` makes it."]
    try:
        repo = json.loads(rb)
        pub = bytes.fromhex(repo["key"]["pub"])
        rsig = bytes.fromhex((_read_bytes(os.path.join(folder, "repo.json.sig")) or b"").decode().strip())
        isig = bytes.fromhex((_read_bytes(os.path.join(folder, "index.json.sig")) or b"").decode().strip())
    except Exception as e:
        return ["repo.json or a signature cannot be read (%s)." % e], warnings
    if repo.get("id") != fingerprint(pub):
        problems.append("the id in repo.json is not the fingerprint of its key.")
    if not verify_bytes(pub, rb, rsig):
        problems.append("repo.json is not signed by its own key.")
    if ib is None or not verify_bytes(pub, ib, isig):
        problems.append("index.json is not signed by the repository's key.")
    return problems, warnings


def repo_ids():
    """{folder: id} for every repository that already has a repo.json."""
    out = {}
    for kind, folder in repositories():
        rj = _read_json(os.path.join(folder, "repo.json"))
        if rj and rj.get("id"):
            out[kind] = rj["id"]
    return out


def cmd_check(args):
    bad = 0
    ids = repo_ids()
    for kind, rid in sorted(ids.items()):
        twins = sorted(k for k, v in ids.items() if v == rid and k != kind)
        if twins:
            print("repos/%s: PROBLEM it has the same key (id %s) as repos/%s; a device would see one repository, not two." % (kind, rid, ", repos/".join(twins)))
            bad += 1
    repos = repositories(args.only)
    if not repos:
        print("no repository with a repo.toml under repos/")
    for kind, folder in repos:
        items, problems, warnings = read_items(folder)
        sp, sw = check_signatures(folder)
        problems += sp
        warnings += sw
        # the committed index must say what the folder holds
        idx = _read_json(os.path.join(folder, "index.json"))
        if idx is not None and not sp:
            have = sorted((a.get("name"), a.get("version"), a.get("sha256")) for a in idx.get("apps", []))
            want = sorted((i["item"]["name"], i["item"]["version"], hashlib.sha256(i["data"]).hexdigest()) for i in items)
            if have != want:
                warnings.append("index.json is out of date: it does not list what the folder holds. Run `build`.")
        if args.strict:
            problems, warnings = problems + warnings, []
        print("repos/%s: %d item(s), %d problem(s), %d warning(s)" % (kind, len(items), len(problems), len(warnings)))
        for m in problems:
            print("  PROBLEM  " + m)
        for m in warnings:
            print("  note     " + m)
        bad += len(problems)
    return 1 if bad else 0


def cmd_build(args):
    repos = repositories(args.only)
    if not repos:
        raise HubError("no repository with a repo.toml under repos/")
    if len(repos) > 1:
        raise HubError("one run signs one repository (use --only <name>): a device knows a repository by its key, so each needs its own key.")
    plan = []
    for kind, folder in repos:
        items, problems, warnings = read_items(folder)
        for m in warnings:
            print("repos/%s: note: %s" % (kind, m))
        if problems:
            for m in problems:
                print("repos/%s: PROBLEM %s" % (kind, m))
            raise HubError("repos/%s has problems; nothing was written." % kind)
        plan.append((kind, folder, items))
    priv = load_private(args.key)
    pub = raw_pub(priv.public_key())
    for other, rid in repo_ids().items():
        if rid == fingerprint(pub) and other != plan[0][0]:
            raise HubError("this key already signs repos/%s; a device would see one repository, not two. Give repos/%s its own key (endorsed by the hub key)." % (other, plan[0][0]))
    now = int(args.now if args.now is not None else time.time())
    print("signing with the key %s (fingerprint %s)" % (args.key, fingerprint(pub)))
    for kind, folder, items in plan:
        meta = load_toml(os.path.join(folder, "repo.toml")).get("repo", {})
        old_index, old_repo = _read_json(os.path.join(folder, "index.json")), _read_json(os.path.join(folder, "repo.json"))
        endorser = None
        if meta.get("endorse_key_id"):
            # the device knows this key under that id; it checks the endorsement against its own copy
            endorser = {"key_id": int(meta["endorse_key_id"]), "sig": sign_bytes(priv, ENDORSE_PREFIX + hashlib.sha256(pub).digest()).hex()}
            if old_repo and old_repo.get("endorsement", {}).get("key_id") == endorser["key_id"] and verify_bytes(
                    pub, ENDORSE_PREFIX + hashlib.sha256(pub).digest(), bytes.fromhex(old_repo["endorsement"].get("sig", ""))):
                endorser = old_repo["endorsement"]
        repo_bytes, index_bytes, _idx = make_files(folder, items, pub, now, old_index, old_repo, endorser)
        if len(index_bytes) > MAX_INDEX:
            raise HubError("repos/%s: index.json would be %d bytes; a device refuses an index over 24 KB." % (kind, len(index_bytes)))
        changed = []
        for name, data in (("repo.json", repo_bytes), ("index.json", index_bytes)):
            path = os.path.join(folder, name)
            old, old_sig = _read_bytes(path), _read_bytes(path + ".sig")
            if old == data and old_sig is not None:
                try:
                    if verify_bytes(pub, data, bytes.fromhex(old_sig.decode().strip())):
                        continue
                except ValueError:
                    pass
            with open(path, "wb") as fh:
                fh.write(data)
            with open(path + ".sig", "wb") as fh:
                fh.write(sign_bytes(priv, data).hex().encode())
            changed.append(name)
        print("repos/%s: %d item(s), %s" % (kind, len(items), ("wrote " + ", ".join(changed)) if changed else "nothing changed"))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="check and sign the repositories in repos/")
    sub = ap.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("keygen", help="make this store's key")
    k.add_argument("--key", default=os.path.join(ROOT, "signing_keys", "hub.key"))
    c = sub.add_parser("check", help="look at the repositories (no key needed)")
    c.add_argument("--only", action="append", help="a folder under repos/ (repeat for several)")
    c.add_argument("--strict", action="store_true", help="treat notes as problems (for CI)")
    b = sub.add_parser("build", help="check, then write and sign repo.json and index.json")
    b.add_argument("--key", default=os.path.join(ROOT, "signing_keys", "hub.key"))
    b.add_argument("--only", action="append")
    b.add_argument("--now", type=int, help="the time to record (for tests); default now")
    args = ap.parse_args(argv)
    try:
        if args.cmd == "keygen":
            pub = keygen(args.key)
            print("wrote %s, %s and %s" % (args.key, os.path.splitext(args.key)[0] + ".pub", os.path.splitext(args.key)[0] + ".pub.bin"))
            print("fingerprint %s (publish the .pub.bin in keys/; keep the .key private and back it up offline)" % fingerprint(pub))
            return 0
        return cmd_check(args) if args.cmd == "check" else cmd_build(args)
    except HubError as e:
        print("error: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
