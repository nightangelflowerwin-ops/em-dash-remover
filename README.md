# Em Dash Remover

Check and remove em dashes from tracked repository text. Python standard library only. MIT licensed.

```sh
python emdash.py --root /path/to/your/repo
python emdash.py --root /path/to/your/repo --mode fix
```

The default checks documentation and changes nothing. Add `--encoded` for escaped Unicode, HTML, URL and supported misencoded forms. Add `--all-text` to include source and data files; review those diffs because punctuation can be meaningful to code. GitHub Action and pull-request automation are the next release milestone.

Binary assets, untracked files, symlinks and files over 2 MiB are skipped. No credentials or network calls are used by the local scanner. It does not rewrite commit history or rename files. Reports disclose skipped files and errors.
