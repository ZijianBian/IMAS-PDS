#!/usr/bin/env bash
# Source this optional SDCC entry point before creating/running HCD cases.
# Native HCD installations and input data are selected by the caller.
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    echo "Use: source config_pds_hcd_iter_sdcc.sh" >&2
    exit 1
fi
if ! type module >/dev/null 2>&1; then
    source /usr/share/lmod/lmod/init/bash || return 1
fi
if declare -F deactivate >/dev/null; then
    deactivate
fi
module purge || return 1
unset PYTHONHOME PYTHONPATH VIRTUAL_ENV VIRTUAL_ENV_PROMPT
export PYTHONNOUSERSITE=1
export PDS_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
module use "${PDS_MODULEPATH:-/work/projects/pds/modules/all}" || return 1
module load "${PDS_MODULE:-PDS/1.0}" || return 1
export YMMSL_PATH="${PDS_REPO}/workflows${YMMSL_PATH:+:${YMMSL_PATH}}"
