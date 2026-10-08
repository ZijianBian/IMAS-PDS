# PDS + HCD-WF

These workflows run the HCD-WF MUSCLE3 micro through the standard PDS case
commands. Runtime installations and input IDS are supplied by the user;
the repository contains the workflow and physics configuration.

| Workflow | Actors and clock | Time selection |
| --- | --- | --- |
| `hcdwf` | PDS clock; TORBEAM, CYRANO, RABBIT, FoPla, HCD2 | All time frames in the input IDS |
| `hcdwf_torax` / 105099 | NICE initialization; TORAX clock; TORBEAM, HCD2 | Initialization IDS and TORAX configuration |

## Runtime

Use an [HCD-WF-M3](https://github.com/ZijianBian/HCD-WF-M3) checkout with the
NICE GGD preparation and CYRANO single-mode coordinate fixes, for example
`integration/imas-pds` at `266d6ee89700790209bca6c2cb000968fbb37f3a`. Select compatible existing
installations before creating a case:

```bash
export HCD_SOURCE_DIR=/path/to/HCD-WF-M3
export HCD_SOURCE_REVISION=266d6ee89700790209bca6c2cb000968fbb37f3a  # optional pin
export HCDWF_PDS_VENV_DIR=/path/to/hcd-python-environment
export HCDWF_IWRAP_ROOT=/path/to/iwrap
export ACTOR_FOLDER=/path/to/actor-python-root
source config_pds_hcd_iter_sdcc.sh
```

The entry script loads the shared SDCC PDS module. Override `PDS_MODULEPATH`
and `PDS_MODULE` for another compatible module installation. The HCD Python
3.11 environment uses MUSCLE3 0.10.0 and the actors use DD 4.1.0. Native
actors must match the site's compiler and library stack. Case creation
checks the selected resources; it does not install packages, build actors,
or fetch IDS. See [external assets](hcdwf-assets.md) for required variables.

## HCD-only case

Provide equilibrium, core profiles, EC launchers, IC antennas and wall, plus
a complete DD 4.1 NBI IDS, native actors and Rabbit tables. The NBI entry
must contain geometry, time-dependent power and energy; machine-description
geometry alone is insufficient. An input variable accepts either an absolute
directory containing `master.h5` or `imas:hdf5?path=/absolute/path/to/entry`.

```bash
export SCENARIOS_REPO=/path/to/scenarios
export SHOT=105102  # select an existing scenario directory
export PDS_HCDWF_INPUT_URI=/path/to/input-ids
export PDS_HCDWF_NBI_URI=/path/to/complete-nbi-dd410
export HCDWF_PDS_ACTOR_ROOT=/path/to/hcd-actor-root
export HCDWF_RABBIT_TABLES_DIR=/path/to/rabbit-tables
# Set HCDWF_PDS_ACTOR_PYTHONPATH if wrappers need additional Python roots.
bin/pds-create-case hcdwf "$SHOT"
export CASE_DIR="$PWD/cases/hcdwf_$SHOT"
bin/pds-run-case "$CASE_DIR"
```

The PDS source determines the simulation times from the input IDS. The
standard `nbi_source` component samples the supplied NBI data at each time
using the closest available slice; there is no prescribed NBI waveform or
fixed time window. CYRANO uses the single mode `n_phi=-38` from its XML; the
FoPla pilot parameter remains 5 MW. Rabbit generates `options.nml` in the
case from `input_rabbit.xml` when it first runs.

## EC + TORAX case

Provide the 105099 initialization, EC launcher replay and prepared HCD
geometry. NICE recomputes the TORAX initialization equilibrium. HCD receives
evolving TORAX profiles and reference geometry/launchers sampled on the
TORAX clock.

```bash
export SCENARIOS_REPO=/path/to/local-scenarios
mkdir -p "$SCENARIOS_REPO/105099"
export PDS_HCDWF_105099_INPUT_URI=/path/to/105099-input
export PDS_HCDWF_105099_EC_URI=/path/to/105099-ec-reference
export PDS_HCDWF_105099_GEOMETRY_URI=/path/to/105099-hcd-geometry
export HCDWF_TORBEAM_DIR=/path/to/torbeam-install
export HCDWF_CORE_SOURCES_DIR=/path/to/hcd2core-sources-install
export HCDWF_TORAX_ACTOR_ROOT=/path/to/TORAX-MUSCLE3
export HCDWF_TORAX_ACTOR_REVISION=b62a4dc549a3bf320dec30bb27e587fc288274c6  # optional pin
bin/pds-create-case hcdwf_torax 105099
export CASE_DIR="$PWD/cases/hcdwf_torax_105099"
bin/pds-run-case "$CASE_DIR"
```

The standard case creator requires the selected scenario directory when
`SCENARIOS_REPO` exists. Use an existing `105099` scenario directory, or
create it in a local scenario root as shown above when providing all three
input URI overrides. The input IDS remain in the supplied external entries.

Case preparation loads `CONFIG.numerics` from the frozen TORAX Python
configuration and writes its selected interval to
`preprocess_settings.ymmsl`. The reference configuration reads the second
equilibrium time frame through the last frame in the initialization IDS.
The generated `source.t_min` skips the incomplete first plasma-composition
frame; explicit `torax.t_initial` and `torax.t_final` keep the actor on the
same interval and take precedence over its default NICE trace bounds.
HCD accepts the time frames requested by TORAX; its XML uses `tbegin=-1`
and `tend=-1` to leave the interval unrestricted. These settings are derived
from the input and configuration rather than a fixed scenario time window.

Use the [TORAX-MUSCLE3 fork](https://github.com/ZijianBian/TORAX-MUSCLE3),
branch `feature/pds-hcdwf-torax` at `b62a4dc549a3bf320dec30bb27e587fc288274c6`, based on upstream
`develop` commit `b4311d3`. Its three compatibility fixes handle padded and
duplicate ion labels, initial psi from geometry, and inherited `n_rho`
settings. These fixes are required to reproduce the 105099 case. The
checkout root must contain `torax_muscle3/torax_actor.py`; case preparation
links it under `assets/torax-actor` and checks the optional revision pin.

The actor's Python source comes from this external checkout through
`PYTHONPATH`. The existing `TORAX-MUSCLE3/0.1.3-intel-2025b-pds` module
supplies TORAX 1.4.0 and its dependencies. NICE remains at development
version 258. No shared module is installed or updated; source and license
remain in the TORAX-MUSCLE3 fork.

## Case layout and execution

For a custom case directory, pass an absolute path as the third argument to
`bin/pds-create-case`.

`pds-create-case` freezes the selected environment and configuration into
the case, copies the HCD parameters into `preprocess/hcd_config`, and links
input IDS and native installations under `preprocess/input` and `assets`.
Those links require the supplied external resources to remain available.
The HCD-only case writes `core_sources` and `waves` under
`CASE_DIR/output/hcd`. The EC + TORAX case writes the transport equilibrium
and core profiles under `CASE_DIR/output/transport_ec` at completion. NICE
equilibrium and HCD sources are exchanged directly between components;
they have no intermediate output sinks in this case. The JAX cache is under
`CASE_DIR/cache/jax`.

`bin/pds-run-case` submits the standard PDS runner when `sbatch` is available
and otherwise runs it locally. To override Slurm resources, submit directly
with, for example, `sbatch --time=01:00:00 bin/pds-run-case.sbatch "$CASE_DIR"`.
Alternatively, start MUSCLE3 directly:

```bash
configs=("$CASE_DIR/workflow.ymmsl" "$CASE_DIR/workflow_settings.ymmsl")
for extra in scenario_settings preprocess_settings; do
  if [[ -f "$CASE_DIR/$extra.ymmsl" ]]; then
    configs+=("$CASE_DIR/$extra.ymmsl")
  fi
done
muscle_manager --start-all "${configs[@]}"
```

Optional user-provided scenario and preprocessing settings are applied
last, as in the PDS runner. Both HCD workflows use the standard runner
without an additional `env.sh`. Input IDS, generated cases, actor
installations, caches and run logs remain outside Git.

## Current scope

The direct HCD micro preserves native `core_sources` fields. Unpopulated
heating profiles and global powers remain missing and must not be treated
as zeros. Full physics and energy-balance acceptance has not been established.

The EC case uses reference HCD geometry and launcher replay. EC+IC coupling
into TORAX still requires IC source pre-registration and electron/ion
heating checks. FoPla distributions are not an accepted TORAX fast-ion
feedback interface.
