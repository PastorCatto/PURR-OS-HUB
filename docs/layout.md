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
                               each repository folder: repo.json, repo.json.sig, index.json, index.json.sig
submissions/                   the entry schema and an example for pull requests
.github/                       the pull request template (and later the workflows)
docs/                          these documents
```

Later, when the keys exist: `ci/` (the checks), `tools/` (`make_site.py`, `verify_hub.py`).

## What is committed and what is not

Committed to `main`: everything above, all small text files that a person can review. The large files (kernel, loader, KittenOS and app, game and shell packages) are not committed: CI builds the static site from them and publishes it ([hosting.md](hosting.md)). A manifest or an index names each large file with its size and sha256, so the site can be rebuilt and checked at any time.

## Item types in a repository

An index entry has a `type`: `app` (default), `asset`, `extra`, `theme` (one `pack.bin`, up to 4 MB) or `shell` (one signed `shell.cat`, up to 1 MB, which carries its own pictures). The full format is `Repositories/SPEC.md` in the firmware repository (https://github.com/PastorCatto/PURR-OS-ESP32). Official shells are in `repos/ui`; official themes are in `repos/extras`.
