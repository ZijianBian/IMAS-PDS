#!/usr/bin/env bash
set -euo pipefail
source "$PDS_REPO/workflows/hcdwf/prepare_case.sh"
hcd_prepare_runtime
hcd_link torbeam "${HCDWF_TORBEAM_DIR:-${HCD_ASSET_ROOT:?Set HCDWF_TORBEAM_DIR or HCD_ASSET_ROOT}/torbeam}" torbeam/actor.py
hcd_link core-sources "${HCDWF_CORE_SOURCES_DIR:-${HCD_ASSET_ROOT:?Set HCDWF_CORE_SOURCES_DIR or HCD_ASSET_ROOT}/hcd2core_sources}" hcd2core_sources/actor.py
hcd_link torax-actor "${HCDWF_TORAX_ACTOR_ROOT:?Set HCDWF_TORAX_ACTOR_ROOT to the patched TORAX-MUSCLE3 checkout}" torax_muscle3/torax_actor.py
if [[ -n "${HCDWF_TORAX_ACTOR_REVISION:-}" ]]; then
    [[ "$(git -C "$HCDWF_TORAX_ACTOR_ROOT" rev-parse HEAD)" == "$HCDWF_TORAX_ACTOR_REVISION" ]] || {
        echo "HCD: selected TORAX actor does not match HCDWF_TORAX_ACTOR_REVISION" >&2; exit 1;
    }
fi
hcd_input source "${PDS_HCDWF_105099_INPUT_URI:-$SCENARIOS_REPO/$SHOT/data/in}"
hcd_input ec "${PDS_HCDWF_105099_EC_URI:-$SCENARIOS_REPO/$SHOT/data/ec_reference}"
hcd_input geometry "${PDS_HCDWF_105099_GEOMETRY_URI:-$SCENARIOS_REPO/$SHOT/data/hcd_geometry}"
hcd_copy_parameters "${HCDWF_TORAX_HCD_CONFIG_DIR:-$PDS_REPO/cases/overrides/hcdwf_$SHOT}" \
    input_workflow.xml ECRH/ec_wave_solver/input_torbeam.xml \
    source/fill_core_sources/input_hcd2core_sources.xml
# Keep the initialization trace and actor on the interval selected by the config.
PDS_HCDWF_105099_INPUT_URI="imas:hdf5?path=$CASE_DIR/preprocess/input/source" \
    python - "$CASE_DIR/config/config_torax.py" "$CASE_DIR/preprocess_settings.ymmsl" <<'PY'
import math
from pathlib import Path
import runpy
import sys

numerics = runpy.run_path(sys.argv[1])["CONFIG"]["numerics"]
t_initial, t_final = (float(numerics[key]) for key in ("t_initial", "t_final"))
if not all(math.isfinite(t) for t in (t_initial, t_final)) or t_final <= t_initial:
    raise ValueError("TORAX config must select a finite, increasing time interval")
Path(sys.argv[2]).write_text(
    "ymmsl_version: v0.2\n\nsettings:\n"
    f"  source.t_min: {t_initial!r}\n"
    f"  torax.t_initial: {t_initial!r}\n"
    f"  torax.t_final: {t_final!r}\n"
)
PY
mkdir -p "$CASE_DIR/output" "$CASE_DIR/cache/jax"
