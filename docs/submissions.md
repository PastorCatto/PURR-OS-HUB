# Submissions: third-party apps and games

Anyone can run their own repository under their own key and rules; a user adds it in the Store. To be listed in **this** hub instead, open a pull request that adds one index entry (see `submissions/entry.example.json`). Pull requests that add shells are closed: shells are native code and are installed from their author's own repository.

## What an entry says

`name`, `title`, `version`, `desc`, `type` (`app`; a game is an app with `category: "game"`), `url` (the package address), `sha256`, `size`, `source` (a link to the source code), the **commit** the package was built from, the `perms` the app asks for, `min_os`, and the licence. The package is built by the author from that commit. The author may sign it with their own key or leave it unsigned; either way a device accepts it because the hub's signed index vouches for those exact bytes (the size and sha256 in the signed entry), and only as an unprivileged app. Devices do not trust an author's key, and the project's developer key is not used for third-party apps.

The all-zero sha256 in `submissions/entry.example.json` is a placeholder; a real entry carries the package's real sha256 and size.

## What CI checks

- the package downloads and its size and sha256 match the entry;
- the package is a valid app image and its name and version match;
- the permissions in the package are the permissions in the entry (and none of them is one the hub does not allow third parties);
- the source link and commit exist.

## What the owner does

Reads the change, merges it, then signs the updated index offline. A merged pull request is not published until the index is signed.
