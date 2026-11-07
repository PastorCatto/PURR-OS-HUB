# PURR OS Hub

The hub is where a PURR OS device gets everything that is not already in it: OS updates (OTA), apps, games, drivers, extras (themes, fonts, sounds) and shells (user interfaces). It is a set of static files. There is no server to run and nothing here executes on a device.

This repository holds everything: lists, indexes, signatures, documentation and the files themselves (OS images, app and shell packages). A device reads it directly from `main` through its raw GitHub address, so updating the repository updates the Store. See [docs/hosting.md](docs/hosting.md).

**Status:** the layout and the rules are written; nothing is signed or published yet. The new signing keys exist and their public halves are in [keys/](keys/KEYS.md), but nothing is signed with them yet ([docs/trust-and-keys.md](docs/trust-and-keys.md)), so `hub.json` and every signature are added after that.

## How a device uses it

1. It asks for `hub.json`: a signed list of **channels** (`stable`, `beta`, `dev`), each with a base address, a trust rule and a version floor rule.
2. For the OS it reads that channel's manifests under `os/<channel>/` and verifies every image against the keys built into the device. The install of OS images stays in the recovery loader and KittenOS, which keep their own copy of the address, so a broken OS can still repair itself.
3. For apps, games, drivers, extras and shells it reads the repository's `repo.json` and `index.json` (and their signatures) under `repos/official/`, the same format the Store already understands.

A host can never make a device run something it should not: images and packages are verified against keys on the device whatever address they came from. A wrong or hostile host can only withhold updates, and the signed `moved.txt` in `os/<channel>/` is the way to point devices somewhere else.

## What is where

See [docs/layout.md](docs/layout.md). In short: `hub.json`, `keys/`, `os/`, `repos/official/` (the one official repository: apps and shells), `submissions/`, `docs/`.

## Contributing

Third-party apps and games are added by pull request ([docs/submissions.md](docs/submissions.md)). Shells and themes from other authors live in the author's own repository, which a user adds in the Store; they are not added here.

## Licence

MIT, see [LICENSE](LICENSE). This licence covers this repository's own files (documents and tools). The apps, games and shells listed here are not all under one licence: each item names its own licence in its `items/<name>.toml`, and there is no repository-wide default.
