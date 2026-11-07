# Submissions: third-party apps and games

Anyone can run their own repository under their own key and rules; a user adds it in the Store. To be listed in **this** hub instead, open a pull request that adds the **package** (the binary) to `repos/official/apps/`, together with its `items/<name>.toml` description. Third-party apps are unprivileged. Third-party shells and anything privileged (drivers, modules, kernel images) are not accepted here: they stay in the author's own repository, and a pull request that adds one is closed.

## What a submission says

The `items/<name>.toml` carries `name`, `title`, `version`, `desc`, `type` (`app`; a game is an app with `category = "game"`), `source` (a link to the source code), the **commit** the package was built from (in the toml or in the pull request), the `perms` the app asks for, `min_os`, and the item's own licence (every item names its own; there is no default). The field names follow section 3.2 of `Repositories/SPEC.md` in the firmware repository.

The package is built by the author from that commit. The author may sign it with their own key or leave it unsigned; either way a device accepts it because the hub's signed index vouches for those exact bytes (the size and sha256 in the signed entry), and only as an unprivileged app. Devices do not trust an author's key, and the project's developer key is not used for third-party apps.

`submissions/item.example.toml` is an example. For it, a contributor adds the package `repos/official/apps/clock-1.2.0.cat` and its description `repos/official/items/clock.toml`; the package file is named `<name>-<version>.<ext>`.

Keep the texts short: `title` is at most 31 characters, `desc` at most 79 and `category` at most 15. A device drops a whole index entry if one of its texts is longer than the device keeps, so `check` refuses a longer one rather than let an entry that no device would show be signed.

The contributor does **not** write `size`, `sha256` or `url`: `python3 tools/hubsign.py build` fills them in from the package when the owner signs. `commit` and `licence` are for the reviewer and are not copied into the index (the tool ignores fields it does not know). Whether a licence ever reaches the Store is still the owner's open decision.

## What CI checks

CI runs `python3 tools/hubsign.py check --strict`, which needs no key. It publishes nothing and never holds the hub key or a passphrase. It is switched on only after the first `build`, because an unsigned repository fails the strict check. It checks:

- names, versions and types in the toml, and the text lengths a device keeps (title, desc, category, min_os, dest, chip, a permission, a version of at most 15 characters, a package file name a device accepts), and that exactly one package file matches each item;
- sizes (within the caps) and that the package's payload hash matches its header;
- the shell rules (a shell must be a signed loadable shell module of at most 1 MB with `dest = "shell.cat"`), and that an app is a PURR app package and a module is not an item;
- that the existing signatures verify and that `index.json` is not out of date.

## What the owner checks by hand

The owner checks the rest before merging; the tool does not, and may automate some of it later:

- that the source link and the commit exist and match the package;
- that the permissions in the toml match what the package asks for;
- that the package is unprivileged;
- that nothing private is in the change.

## What the owner does

Reads the change and merges it, then runs one local command, `python3 tools/hubsign.py build`, which rebuilds `index.json` and signs it with the hub key (id 5), and then pushes the result. A merged item is **not offered to any device** until that signed index is pushed: that is the review gate.
