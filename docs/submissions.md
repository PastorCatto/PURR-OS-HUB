# Submissions: third-party apps and games

Anyone can run their own repository under their own key and rules; a user adds it in the Store. To be listed in **this** hub instead, open a pull request that adds the **package** (the binary) to `repos/apps/` or `repos/games/`, together with its `items/<name>.toml` description. Third-party apps are unprivileged. Third-party shells and anything privileged (drivers, modules, kernel images) are not accepted here: they stay in the author's own repository, and a pull request that adds one is closed.

## What a submission says

The `items/<name>.toml` carries `name`, `title`, `version`, `desc`, `type` (`app`; a game is an app with `category = "game"`), `source` (a link to the source code), the **commit** the package was built from (in the toml or in the pull request), the `perms` the app asks for, `min_os`, and the licence. The field names follow section 3.2 of `Repositories/SPEC.md` in the firmware repository.

The package is built by the author from that commit. The author may sign it with their own key or leave it unsigned; either way a device accepts it because the hub's signed index vouches for those exact bytes (the size and sha256 in the signed entry), and only as an unprivileged app. Devices do not trust an author's key, and the project's developer key is not used for third-party apps.

The `url`, `size` and `sha256` of an index entry are not written by hand: `tools/hubsign.py` computes them from the package. `submissions/entry.example.json` shows the finished entry in the index; its all-zero sha256 is a placeholder, and a real entry carries the package's real sha256 and size.

## What CI checks

CI only checks (`python3 tools/hubsign.py check --strict`, which needs no key); it publishes nothing and never holds the hub key or a passphrase.

- the package is within the size caps and is a valid app image whose name and version match the toml;
- the sha256 and size are the package's own;
- the permissions in the package are the permissions in the toml (and none of them is one the hub does not allow third parties);
- the type rules hold (an app, not a shell or anything privileged);
- the source link and commit exist;
- no secrets are in the change.

## What the owner does

Reads the change and merges it, then runs one local command, `python3 tools/hubsign.py build`, which rebuilds `index.json` and signs it with the hub key (id 5), and then pushes the result. A merged item is **not offered to any device** until that signed index is pushed: that is the review gate.
