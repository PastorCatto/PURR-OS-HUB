# Hosting

**Decision (owner, 2026-11-06):** the hub is served from a static site that CI builds onto a **deploy branch**, whose history is squashed on every deploy. `main` therefore stays small, and the repository does not grow with every OS image or package.

- The site uses the same tree layout as the firmware repository's `purrstrap dev serve` (for example `purr/v1/...` for a repository, `os/stable/recovery.manifest` for a channel), so a device reads it the same way it reads the development server.
- The address devices use is meant to become one the owner controls (a custom domain pointed at the same site). Nothing compiled into a device has to change when it does, because the signed `moved.txt` and `hub.json` carry the addresses.
- GitHub is the host **for now, not forever.**

## What CI does and does not do

CI builds the site from the committed metadata and the release assets, and runs the checks (hashes, signatures against the public keys in `keys/`, the permissions an entry asks for). **CI never holds the boot key, the hub key or any passphrase.** Signing happens offline on the owner's computer; CI only verifies.
