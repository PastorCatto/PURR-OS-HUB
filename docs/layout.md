# Layout

```
README.md  LICENSE  HUB.md
hub.json  hub.json.sig         signed list of channels (added after the key rotation)
keys/                          PUBLIC keys only; KEYS.md says what each is for
os/stable/  beta/  dev/        recovery.manifest, modules.manifest, drivers.manifest,
                               withdrawn.list, moved.txt + moved.txt.sig
repos/official/                the one official repository: apps and shells (later themes and
                               other items) together. It holds repo.toml, repo.json, repo.json.sig,
                               index.json, index.json.sig, the packages beside them (for example
                               w10m-1.0.32.cat) and items/<name>.toml, the small unsigned
                               description of each item that the signing step reads
submissions/                   the entry schema and an example for pull requests
.github/                       the pull request template (and later the checks)
docs/                          these documents
```

`tools/hubsign.py` is the one tool that checks and signs the repositories; `tools/test_hubsign.py` tests it. To run your own store from a copy of this repository, see [fork.md](fork.md).

## What is committed and what is not

Everything is committed to `main`, binaries included: OS images and the app, game, driver, extras and shell packages sit next to the manifest or index that names them with their size and sha256 ([hosting.md](hosting.md)). Each item keeps its current and previous version only.

## Item types in a repository

An index entry has a `type`: `app` (default), `asset`, `extra`, `theme` (one `pack.bin`, up to 4 MB) or `shell` (one signed `shell.cat`, up to 1 MB, which carries its own pictures). The full format is `Repositories/SPEC.md` in the firmware repository (https://github.com/PastorCatto/PURR-OS-ESP32). All official items are in `repos/official`; the Store tells apps, shells and themes apart by each item's `type` and `category`, not by folder.

## One key is one repository

A device knows a repository by its **key** fingerprint, so one key is one repository. Two folders signed with the same key would be the same repository on a device, and the second would overwrite the first. That is why the hub has a single official repository. An additional repository needs its **own key**, endorsed by the hub key, and its own folder under `repos/`.

**Known limit:** a device holds at most 32 items per repository today.
