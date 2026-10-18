**[ไทย](README.md) | English**

# Storage Check

A disk-space checker for macOS with both a CLI and a web UI that runs on your own machine.

- Uses only the Python standard library, nothing to install
- Read-only modes are safe. Modes that delete always show what they will do first and ask for confirmation
- Every deletion moves items to the Trash, so they can be restored

## Getting started

```bash
cd "/Users/chanyut/Documents/storage check"
python3 gui.py
```

The browser opens `http://127.0.0.1:8765` automatically. If it doesn't, type that URL yourself.

> **Always open the UI through `gui.py`.** Do not open `static/index.html` with Live Server or by double-clicking it. The page calls the API served by `gui.py`. Opening it any other way shows a "response is not JSON" error.

The server only accepts requests from `127.0.0.1`. Press `Ctrl+C` in Terminal to stop it. If you see `Address already in use`, a `gui.py` is still running. Run `pkill -f gui.py` and start it again.

Scanning the whole home folder can take several minutes. The latest result is saved, so reopening the page shows the previous result with its scan time. Press **Scan again** to rescan.

## Web UI

### Main cards

| Card | What it does |
|---|---|
| **App cache** | Review and select cache that can be deleted, then move it to the Trash |
| **Large files** | Review files to check before deleting. Filter by type, or by files not opened for a while. Move the selected files to the Trash |
| **Duplicate files** | Files with identical contents, byte for byte. The most recently edited copy is always kept |
| **Duplicate folders** | Folders whose files are all identical. The most recently edited folder is always kept |
| **Developer tools** | Dry-run output for Docker, Homebrew, conda, and pnpm, then clean what is shown. Docker volumes are never touched |

Items marked ⛔ cannot be selected. Any selected items are moved to the Trash only after a confirmation dialog.

### More options

- **Largest folders** Click a row to browse its subfolders one level at a time. Click **⬆ Up one level** to go to the parent folder. Click **Exclude** to keep a folder out of future scans.
- **Save & compare** Save a report, then pick a snapshot to see which folders grew or shrank and which large files are new.
- **Settings** Thresholds for large files and duplicates, the number of months after which a file counts as unused, and the excluded folders. Changes apply on the next scan.

### Common buttons

- **Reveal in Finder** Every row has this button. It opens the file or folder's location so you can check details before deciding. It only works for items inside your home folder and never deletes anything.
- **Select all** Selects only items that can be moved. Items marked **Kept** cannot be selected.
- **Filter by type** For example video, archives, data, documents, AI models.

> The "not opened for" date uses the time macOS recorded the file was last read. It is an approximation and may not always match your actual use.

## CLI

```bash
python3 scan.py <mode> [--yes]
```

| Mode | What it does | Deletes? |
|---|---|---|
| `scan` | Shows the largest files and folders | No |
| `report` | Saves `reports/report_*.md` and `.csv` plus a snapshot for comparison | No |
| `diff` | Compares with the latest snapshot and shows what grew and what is new | No |
| `tools` | Shows or cleans caches for Docker, Homebrew, conda, and pnpm | Only with `--yes` |
| `clean-cache` | Moves caches larger than the threshold in `~/Library/Caches` and `~/.cache` to the Trash | Only with `--yes` |
| `interactive` | Pick files by number, then confirm before moving them | Always asks first |
| `duplicates` | Finds duplicate files of 10 MB or more, shows the groups and the space you can reclaim | Only with `--yes`. Keeps the most recently edited copy |

Examples

```bash
python3 scan.py report              # save a comparison point
python3 scan.py diff                # see what grew since last time
python3 scan.py tools               # see what would be cleaned (dry-run)
python3 scan.py tools --yes         # clean for real
python3 scan.py duplicates          # list duplicates (dry-run)
python3 scan.py duplicates --yes    # move duplicates other than the newest copy to the Trash
```

## Labels

| Label | Meaning |
|---|---|
| 🟢 cache | Cache or log folder that can be recreated |
| 🟡 review first | Ordinary file. Check its last-used date and contents before deleting |
| ⛔ do not delete | Data you should not touch, such as Docker, iCloud, Photos, or Keychains |

🟡 does not mean safe to delete. Always review it first.

## Safety

- Every deletion goes to the Trash through Finder, so it can be restored
- Items marked ⛔ and paths outside your home folder are refused inside the move function itself, whether the request comes from the web UI or the CLI
- `tools` never touches Docker volumes. It only prunes untagged images and build cache
- `clean-cache --yes` moves caches that can be recreated. Apps that are open may take time to rebuild them
- The server does not accept requests from other machines

## Settings

These can be changed in the web UI under **Settings** and are stored in `settings.json`.

| Key | Meaning | Default |
|---|---|---|
| `min_mb` | Minimum size of files to show | 100 MB |
| `dup_min_mb` | Minimum size of files and folders checked for duplicates | 10 MB |
| `old_months` | Months without use before a file counts as unused | 12 |
| `exclude` | Folders not to scan, written as `~/...` | empty |

Other values, such as `TOP_N`, `SKIP_DIRS`, `NEVER`, and `CACHE`, are in `storagecheck/config.py`.

## Code layout

```
scan.py                 CLI entry point
gui.py                  web server and API
storagecheck/
  config.py             settings, paths, and constants
  safety.py             labels, protected paths, and moving to the Trash
  walk.py               walking the home folder, file index, large-file scan
  hashing.py            file hashing with caching and parallel hashing
  duplicates.py         duplicate files and duplicate folders
  history.py            last scan, snapshots, reports, and comparison
  tools.py              developer tools (Docker, Homebrew, conda, pnpm)
  cleanup.py            cache cleanup and interactive mode
  cli.py                dispatches CLI modes
static/                 web UI (HTML, CSS, ES modules)
```

To add a new CLI mode, write the function in the relevant module, then add the call in `storagecheck/cli.py`.

## Generated files

| File | Purpose |
|---|---|
| `snapshots/` | Comparison points used by `diff` and the comparison panel |
| `reports/` | `.md` and `.csv` reports |
| `cache/last_scan.json` | Last scan result, loaded when the page opens |
| `cache/hash_cache.json` | Computed hashes, reused for files that have not changed |
| `settings.json` | Settings and the excluded-folder list |

These files contain your file names and usage data, so don't put them under version control.

## Notes

- If `~/Library` or `~/.Trash` cannot be read, give **Full Disk Access** to your Terminal in System Settings → Privacy & Security
- The first time something is moved to the Trash, macOS may ask whether Terminal may control Finder. Click Allow
- Reading a file's hash updates its access time (atime). So after a duplicate search, the "not opened for" value of those files may be wrong until the next time they are really opened
