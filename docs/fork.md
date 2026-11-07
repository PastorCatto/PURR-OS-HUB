# Run your own store

The tools are in this repository, so anyone can copy the whole hub and run a store of their own under their own key. Only the key is private: `signing_keys/`, `*.key` and `*.pem` are git-ignored.

You need Python 3.9 or newer and the `cryptography` package (`pip install cryptography`).

1. **Clone** this repository (or fork it on GitHub).
2. **Make your key:** `python3 tools/hubsign.py keygen`. It asks for a passphrase and writes `signing_keys/hub.key` (private, keep it and back it up offline) and its public halves next to it. Put the public `.pub.bin` in `keys/` if you want it published.
3. **Describe your repository:** `repos/official/` (rename it if you like) needs a `repo.toml` with your `name`, `description`, `maintainer` and `url` (the raw address devices will read it from). **Remove the `endorse_key_id` line.** That line makes a device treat the repository as an official PURR one, which only the project's own key can do. A device knows a repository by its key, so each repository you run needs its own key and its own folder under `repos/`.
4. **Add packages:** put each package in the repository folder or a subfolder of it (the official one uses `apps/` and `shells/`) and write `items/<name>.toml` next to it. The package file is named `<name>-<version>.<ext>` and its path inside the repository is at most 95 characters, and the toml gives its name, version, type and so on (fields: section 3.2 of `Repositories/SPEC.md` in the firmware repository). Keep the current and the previous version of each item.
5. **Sign:** `python3 tools/hubsign.py build`. It checks every repository, then writes and signs `repo.json` and `index.json`. Building twice changes nothing, so the git diff stays clean. The passphrase is asked for, or taken from `PURRHUB_KEY_PASSWORD` for that one command; it is never read from a file.
6. **Push.** Devices read the repository through its raw address.

A device treats a repository without the project's endorsement as a **community** repository: it is used in developer mode, or when the user adds its address in the Store. Third-party apps from it are unprivileged; drivers, modules and kernel images never come from a community repository.

For CI, run `python3 tools/hubsign.py check --strict`. It needs no key, treats every note as a problem, and also fails on a repository that is not signed yet or whose `index.json` is out of date. Keep the key and its passphrase out of CI.

`python3 tools/test_hubsign.py` runs the tool's self-tests with a throwaway key.
