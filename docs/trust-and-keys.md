# Trust and keys

The owner has four system keys (design in the firmware repository's `plan3.md`, "Four system keys and the dev channel"):

| Key | Signs | Where it lives |
|---|---|---|
| boot | OS images (kernel, loader, KittenOS, boot package) and the trust block | offline, owner's computer; **never in CI** |
| developer | apps and drivers | the owner's computer; developer-mode only after the rotation |
| hub | `hub.json`, `moved.txt`, and the app, game, driver, extras and shell indexes | offline |
| nightly | the `dev` channel only | held by CI; accepted by a device only in developer mode on the dev channel, with an expiry |

Only the public halves are ever put in this repository (`keys/`). A private key or a passphrase in a file, a commit message or an issue is a mistake to be fixed at once (revoke the key).

## Status

The keys are being rotated first; nothing signed is published until the new keys exist. `keys/KEYS.md` records the public keys, their fingerprints and the rotation log once they do.

## Shells are different

A shell is native code that runs in the device's kernel and owns the screen. A device loads one only if it is signed by a key that device trusts for shells, and a locked device trusts only the project's keys, so official shells are signed with the hub key and a third-party shell is installed from its author's own repository, never through a pull request here.
