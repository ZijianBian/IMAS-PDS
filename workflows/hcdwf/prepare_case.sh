#!/usr/bin/env bash
# Shared preparation helpers, sourced by the HCD workflow preprocess scripts.

hcd_link() {
    local name="$1" path
    [[ "$name" =~ ^[A-Za-z0-9_-]+$ ]] || { echo "HCD: invalid asset name: $name" >&2; return 1; }
    path="$(realpath -e -- "$2")" || return 1
    [[ -d "$path" && ( -z "${3:-}" || -f "$path/$3" ) ]] || {
        echo "HCD: missing installation or file: $path/${3:-}" >&2; return 1;
    }
    mkdir -p "$CASE_DIR/assets"
    ln -sfnT -- "$path" "$CASE_DIR/assets/$name"
}

hcd_prepare_runtime() {
    : "${CASE_DIR:?CASE_DIR is required}" "${HCD_SOURCE_DIR:?Set HCD_SOURCE_DIR to the HCD-WF checkout}"
    [[ "$CASE_DIR" == /* ]] || {
        echo "HCD: use the default case directory or an absolute custom case path" >&2; return 1;
    }
    : "${HCDWF_IWRAP_ROOT:?Set HCDWF_IWRAP_ROOT to the iwrap installation}"
    local venv="${HCDWF_PDS_VENV_DIR:-${HCD_ASSET_ROOT:+$HCD_ASSET_ROOT/venv}}"
    local actors="${ACTOR_FOLDER:-${HCD_ASSET_ROOT:+$HCD_ASSET_ROOT/actors}}"
    : "${venv:?Set HCDWF_PDS_VENV_DIR or HCD_ASSET_ROOT}" "${actors:?Set ACTOR_FOLDER or HCD_ASSET_ROOT}"
    hcd_link hcd-source "$HCD_SOURCE_DIR" hcdworkflow/hcd_workflow_m3.py || return 1
    if [[ -n "${HCD_SOURCE_REVISION:-}" ]]; then
        [[ "$(git -C "$HCD_SOURCE_DIR" rev-parse HEAD)" == "$HCD_SOURCE_REVISION" ]] || {
            echo "HCD: selected source does not match HCD_SOURCE_REVISION" >&2; return 1;
        }
    fi
    hcd_link hcd-venv "$venv" bin/python || return 1
    hcd_link iwrap "$HCDWF_IWRAP_ROOT" bin/iwrap || return 1
    hcd_link actors "$actors" || return 1
    [[ -x "$CASE_DIR/assets/hcd-venv/bin/python" && -x "$CASE_DIR/assets/iwrap/bin/iwrap" &&
       -d "$CASE_DIR/assets/iwrap/python" ]] || {
        echo "HCD: Python/iwrap must be executable and iwrap/python must exist" >&2; return 1;
    }
}

hcd_input() {
    local name="$1" path
    [[ "$name" =~ ^[A-Za-z0-9_-]+$ ]] || { echo "HCD: invalid input name: $name" >&2; return 1; }
    path="$(python3 - "$2" <<'PY'
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

raw = sys.argv[1]
if raw.startswith("imas:"):
    uri = urlsplit(raw)
    paths = parse_qs(uri.query).get("path", [])
    if uri.scheme != "imas" or uri.path != "hdf5" or len(paths) != 1:
        raise SystemExit("HCD: expected an imas:hdf5?path=/absolute/path URI")
    raw = paths[0]
path = Path(raw).expanduser()
if not path.is_absolute() or not (path / "master.h5").is_file():
    raise SystemExit(f"HCD: expected an absolute HDF5 directory with master.h5: {raw}")
print(path.resolve())
PY
)" || return 1
    mkdir -p "$CASE_DIR/preprocess/input"
    ln -sfnT -- "$path" "$CASE_DIR/preprocess/input/$name"
}

hcd_copy_parameters() {
    local source="$1"
    shift
    python3 - "$source" "$CASE_DIR" "$@" <<'PY'
import sys
from pathlib import Path
from xml.sax.saxutils import escape

source, case = map(Path, sys.argv[1:3])
for filename in sys.argv[3:]:
    relative = Path(filename)
    if relative.is_absolute() or ".." in relative.parts:
        raise SystemExit(f"HCD: parameter filename must be relative: {filename}")
    path = source / relative
    if path.suffix not in (".xml", ".nml", ".yaml") or not path.is_file():
        raise SystemExit(f"HCD: missing XML/NML/YAML parameter: {path}")
    value = str(case)
    if path.suffix == ".xml":
        value = escape(value)
    elif path.suffix == ".nml":
        value = value.replace("'", "''")
    target = case / "preprocess/hcd_config" / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(path.read_bytes().replace(b"${CASE_DIR}", value.encode()))
PY
}

hcd_prepare_actor_paths() {
    local root="${HCDWF_PDS_ACTOR_ROOT:-${ACTOR_FOLDER:-${HCD_ASSET_ROOT:+$HCD_ASSET_ROOT/actors}}}"
    local value="${HCDWF_PDS_ACTOR_PYTHONPATH:-$root}" path index=0 aliases=()
    [[ -n "$value" && "$value" != :* && "$value" != *: && "$value" != *::* ]] || {
        echo "HCD: actor Python paths must be nonempty directories separated by colons" >&2; return 1;
    }
    local paths=()
    IFS=: read -r -a paths <<< "$value"
    for path in "${paths[@]}"; do
        hcd_link "actor-python-$index" "$path" || return 1
        aliases+=("$CASE_DIR/assets/actor-python-$index")
        index=$((index + 1))
    done
    (IFS=:; printf '%s\n' "${aliases[*]}") > "$CASE_DIR/assets/actor_pythonpath.txt"
}
