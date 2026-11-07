# OS channels

One folder per channel: `stable`, `beta`, `dev`. Each will hold `recovery.manifest`, `modules.manifest`, `drivers.manifest`, `withdrawn.list` and, when the address changes, `moved.txt` with `moved.txt.sig`. The manifests name every image with its size and sha256; the images are on the site, not in git. Empty until the first signed release.
