# Trust and keys

The owner has four system keys (design in the firmware repository's `plan3.md`, "Four system keys and the dev channel"):

| Key | Signs | Where it lives |
|---|---|---|
| boot | OS images (kernel, loader, KittenOS, boot package) and the trust block | offline, owner's computer; **never in CI** |
| developer | apps and drivers of the project itself | the owner's computer; developer-mode only after the rotation |
| hub | `hub.json`, `moved.txt`, and the app, game, driver, extras and shell indexes | offline |
| nightly | the `dev` channel only | held by CI; accepted by a device only in developer mode on the dev channel, with an expiry |

Only the public halves are ever put in this repository (`keys/`). A private key or a passphrase in a file, a commit message or an issue is a mistake to be fixed at once (revoke the key).

## How a device decides whether to run an app

A device runs an app if one of two things holds: the app is signed by a key that device trusts for apps (the project's keys, the device owner's own key, or a vendor's), or a repository the device trusts has a signed index that vouches for those exact bytes. The second way only ever applies to an ordinary, unprivileged app: never to a driver, a module, a kernel image or a shell, which must be signed by a key the device trusts for that kind of thing. A third-party author's own key is not one of the keys a device trusts, so a third-party app reaches a device only through a repository's signed index. In a locked device the repositories it trusts are the project's, so this hub; its own settings cannot add more.

'Unprivileged' means the app's class. Such an app may still ask for permissions, which the person (for the most sensitive ones an administrator) grants or refuses when the app runs; neither a signature nor a repository's index grants a permission, and the privileged class, which has every permission and is never asked, is never given by an index.

## Status

The new keys are in keys/. The hub key (id 5) signs the official repository and the Windows 10 Mobile style shell; the developer key (id 4) signs the project's own apps. The boot key (id 3) does not sign anything yet: the OS images are still signed by the old boot key until the rotation is finished (keys/KEYS.md has the log).

## Shells are different

A shell is native code that runs in the device's kernel and owns the screen. A device loads one only if it is signed by a key that device trusts for shells, and a locked device trusts only the project's keys, so official shells are signed with the hub key and a third-party shell is installed from its author's own repository, never through a pull request here.
