## What this adds

A package (the binary) for an app or a game, and its `items/<name>.toml` (not a shell, and nothing privileged). See `submissions/item.example.toml`.

- Name, version and type:
- Title, description and category:
- Source link and the commit the package was built from:
- Permissions the app asks for, and why:
- Minimum OS version:
- Licence of this item:

## Checklist

- [ ] I built the package from the commit above.
- [ ] The package `repos/<apps or games>/<name>-<version>.<ext>` and `repos/<apps or games>/items/<name>.toml` are both in this change, following `docs/submissions.md`.
- [ ] `title` is at most 31 characters, `desc` at most 79 and `category` at most 15 (`check` refuses longer ones; a device would drop the entry).
- [ ] I did not write `size`, `sha256` or `url`; the owner's `build` fills them in.
- [ ] The permissions in the toml are the permissions in the package.
- [ ] This is not a shell or anything privileged (those stay in the author's own repository).
- [ ] Only the current and previous version of this item are in the change.
- [ ] No private key, password or personal data is in this change.

A merged item is not offered to any device until the owner pushes the signed index.
