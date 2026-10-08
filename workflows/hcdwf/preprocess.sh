#!/usr/bin/env bash
set -euo pipefail
source "$PDS_REPO/workflows/hcdwf/prepare_case.sh"
hcd_prepare_runtime
hcd_link hcd-actors "${HCDWF_PDS_ACTOR_ROOT:-${ACTOR_FOLDER:-$HCD_ASSET_ROOT/actors}}"
hcd_prepare_actor_paths
hcd_link rabbit-tables "${HCDWF_RABBIT_TABLES_DIR:?Set HCDWF_RABBIT_TABLES_DIR to the installed Rabbit tables}"
hcd_input source "${PDS_HCDWF_INPUT_URI:-$SCENARIOS_REPO/$SHOT/data/in}"
hcd_input nbi "${PDS_HCDWF_NBI_URI:-$SCENARIOS_REPO/$SHOT/data/nbi}"
hcd_copy_parameters "${HCDWF_PDS_CONFIG_DIR:-$PDS_REPO/cases/overrides/hcdwf_$SHOT}" \
    input_workflow.xml ECRH/ec_wave_solver/input_torbeam.xml \
    ICRH/ic_wave_solver/input_cyrano.xml ICRH/ic_wave_fp/input_fopla.xml \
    NBI/nbi_fp/input_rabbit.xml \
    source/fill_core_sources/input_hcd2core_sources.xml
mkdir -p "$CASE_DIR/output"
