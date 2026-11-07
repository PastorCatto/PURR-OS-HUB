# Repositories

`official/` is the one official repository: the apps and shells (and later themes and other items) from the PURR OS project, in the format of `Repositories/SPEC.md` of the firmware repository: `repo.toml`, `repo.json`, `repo.json.sig`, `index.json`, `index.json.sig` and `items/<name>.toml` for each item at its root, and the packages in subfolders (`apps/`, `shells/`, later `themes/`). A device knows a repository by its key, so one key is one repository; another repository needs its own key and its own folder.
