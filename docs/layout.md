# Layout

```
README.md  LICENSE  HUB.md
hub.json  hub.json.sig         signed list of channels (added after the key rotation)
keys/                          PUBLIC keys only; KEYS.md says what each is for
os/stable/  beta/  dev/        recovery.manifest, modules.manifest, drivers.manifest,
                               withdrawn.list, moved.txt + moved.txt.sig
repos/apps/                    apps
repos/games/                   games (an app of kind "game")
repos/drivers/                 drivers
repos/extras/                  themes, fonts, sounds, other data
repos/ui/                      official shells (user interfaces)
                               each repository folder holds repo.json, repo.json.sig, index.json,
                               index.json.sig, the packages beside them (for example w10m-1.0.32.cat)
                               and items/<name>.toml, the small unsigned description of each item
                               that the signing step reads
submissions/                   the entry schema and an example for pull requests
.github/                       the pull request template (and later the checks)
docs/                          these documents
```

One signing tool will be added when signing starts.

## What is committed and what is not

Everything is committed to `main`, binaries included: OS images and the app, game, driver, extras and shell packages sit next to the manifest or index that names them with their size and sha256 ([hosting.md](hosting.md)). Each item keeps its current and previous version only.

## Item types in a repository

An index entry has a `type`: `app` (default), `asset`, `extra`, `theme` (one `pack.bin`, up to 4 MB) or `shell` (one signed `shell.cat`, up to 1 MB, which carries its own pictures). The full format is `Repositories/SPEC.md` in the firmware repository (https://github.com/PastorCatto/PURR-OS-ESP32). Official shells are in `repos/ui`; official themes are in `repos/extras`.
