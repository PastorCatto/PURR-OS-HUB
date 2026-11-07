# Hosting

**Decision (owner, 2026-11-07):** the hub is one ordinary GitHub repository that the Store points at directly. `main` holds everything, binaries included, so updating the repository updates the Store. There are no release assets, no deploy branch and no site builder: nothing sits between the repository and the device.

- A device reads a repository through its raw address, for example `https://raw.githubusercontent.com/PastorCatto/PURR-OS-HUB/main/repos/official`.
- A repository folder keeps `repo.json`, `repo.json.sig`, `index.json` and `index.json.sig` at its root (see section 2 of `Repositories/SPEC.md` in the firmware repository), and its packages in subfolders such as `apps/` and `shells/`, for example `shells/w10m-1.0.32.cat`; the index names each by its path relative to the repository. `os/<channel>/` keeps OS images next to their manifests.
- Each item keeps its current and its previous version. Older versions are deleted in the same commit that adds the new one. If the repository ever gets heavy, its history can be squashed.
- The address devices use may later become one the owner controls (a custom domain). Nothing compiled into a device has to change when it does, because the signed `moved.txt` and `hub.json` carry the addresses.
- GitHub is the host **for now, not forever.**

## What CI does and does not do

CI only checks a change with `tools/hubsign.py check --strict` (see [submissions.md](submissions.md)); it is switched on after the first `build`, because an unsigned repository fails the strict check. It publishes nothing. **CI never holds the boot key, the hub key or any passphrase.** Signing happens offline on the owner's computer.
