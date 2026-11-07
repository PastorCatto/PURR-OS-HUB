# Submissions: third-party apps and games

Anyone can run their own repository under their own key and rules; a user adds it in the Store. To be listed in **this** hub instead, open a pull request that adds one index entry (see `submissions/entry.example.json`). Pull requests that add shells are closed: shells are native code and are installed from their author's own repository.

## What an entry says

`name`, `title`, `version`, `desc`, `type` (`app`; a game is an app with `category: "game"`), `url` (the package address), `sha256`, `size`, `source` (a link to the source code), the **commit** the package was built from, the `perms` the app asks for, `min_os`, and the licence. The package itself is built by the author from that commit and signed with the author's developer key, or vouched for by the hub's signed index after review.

## What CI checks

- the package downloads and its size and sha256 match the entry;
- the package is a valid app image and its name and version match;
- the permissions in the package are the permissions in the entry (and none of them is one the hub does not allow third parties);
- the source link and commit exist.

## What the owner does

Reads the change, merges it, then signs the updated index offline. A merged pull request is not published until the index is signed.
