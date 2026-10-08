# External assets for PDS + HCD-WF

The [runbook](PDS+HCDWF.md) uses an HCD source checkout, existing Python and
native actor installations, and external IMAS data. The standard
`bin/pds-create-case` command prepares the case without downloading or
building those resources.

## Common runtime

| Variable | Requirement / default |
| --- | --- |
| `HCD_SOURCE_DIR` | Required: HCD-WF-M3 checkout containing the NICE GGD preparation and CYRANO single-mode coordinate fixes |
| `HCD_SOURCE_REVISION` | Optional expected SHA; recommended reference `266d6ee89700790209bca6c2cb000968fbb37f3a` |
| `HCD_ASSET_ROOT` | Optional installation root supplying defaults below |
| `HCDWF_IWRAP_ROOT` | Required: existing `bin/iwrap` and `python/` installation |
| `HCDWF_PDS_VENV_DIR` | Required HCD Python 3.11/MUSCLE3 0.10.0 environment; default `$HCD_ASSET_ROOT/venv` when the asset root is set |
| `ACTOR_FOLDER` | Required common actor Python root; default `$HCD_ASSET_ROOT/actors` when the asset root is set |
| `PDS_MODULEPATH` / `PDS_MODULE` | Override the shared SDCC module location and PDS module selection |

The HCD programs use IMAS-Python 2.3.0, IMAS-Fortran 5.5.0/DD 4.1.0, lxml,
XMLlib, INTERPOS, Waveform-Cooker 1.6.0, matplotlib and PyYAML site modules.
The EC case also needs the NICE and TORAX-MUSCLE3 modules specified in its
workflow. Native libraries and actor wrappers must use a compatible DD,
compiler and library stack.

## Input data

Input variables accept an absolute HDF5 entry directory or
`imas:hdf5?path=/absolute/path/to/entry`. Keep `master.h5` and its linked IDS
files together. Obtain the reference data from its maintainer and retain its
DD version and provenance. The workflows do not convert or generate inputs.

If URI overrides are omitted, inputs are selected from
`$SCENARIOS_REPO/$SHOT/data/` using the directories listed below. Set
`SCENARIOS_REPO` to a site-provided scenario repository or a local scenario
root. When that repository exists, both HCD workflows require the selected
`$SHOT` directory, including when explicit input variables point to data
elsewhere. For EC–TORAX, select an existing `105099` scenario directory or
create `$SCENARIOS_REPO/105099` under a local scenario root and supply all
three input URI overrides.

## HCD-only inputs

| Variable | Requirement / default |
| --- | --- |
| `PDS_HCDWF_INPUT_URI` | Equilibrium, core profiles, EC launchers, IC antennas and wall; default scenario `data/in` |
| `PDS_HCDWF_NBI_URI` | Complete DD 4.1 NBI IDS with geometry, time-dependent power and energy; default scenario `data/nbi` |
| `HCDWF_PDS_ACTOR_ROOT` | Native actor root containing TORBEAM, CYRANO, Rabbit, FoPla and HCD2; default `ACTOR_FOLDER` or `$HCD_ASSET_ROOT/actors` |
| `HCDWF_PDS_ACTOR_PYTHONPATH` | Optional colon-separated additional actor Python roots |
| `HCDWF_RABBIT_TABLES_DIR` | Required existing Rabbit atomic tables |

The PDS source follows the time frames in the input IDS. The standard
`nbi_source` samples the complete NBI entry using the closest slice at each
time; machine-description geometry alone is insufficient. There is no
bundled NBI waveform or fixed 105102 time window. Rabbit requires its DD4
native build, Python wrapper and atomic tables.

Tracked HCD parameters are the six actor XML files. Case preparation copies
them into `preprocess/hcd_config` and sets Rabbit table and output namelist
paths for the case. Rabbit generates `options.nml` from `input_rabbit.xml`
when it first runs. CYRANO takes its single toroidal mode, `n_phi=-38`,
directly from `input_cyrano.xml`; no mode YAML is needed.

## EC–TORAX reference, 105099

| Variable | Requirement / default |
| --- | --- |
| `PDS_HCDWF_105099_INPUT_URI` | Initialization IDS; default scenario `data/in` |
| `PDS_HCDWF_105099_EC_URI` | EC launcher replay; default scenario `data/ec_reference` |
| `PDS_HCDWF_105099_GEOMETRY_URI` | Prepared HCD geometry; default scenario `data/hcd_geometry` |
| `HCDWF_TORBEAM_DIR` | Required TORBEAM installation; default `$HCD_ASSET_ROOT/torbeam` when the asset root is set |
| `HCDWF_CORE_SOURCES_DIR` | Required HCD2 installation; default `$HCD_ASSET_ROOT/hcd2core_sources` when the asset root is set |
| `HCDWF_TORAX_ACTOR_ROOT` | Required: external TORAX-MUSCLE3 checkout root containing `torax_muscle3/torax_actor.py` |
| `HCDWF_TORAX_ACTOR_REVISION` | Optional expected Git SHA; recommended reference `b62a4dc549a3bf320dec30bb27e587fc288274c6` |

The initialization contains equilibrium, core_profiles, wall, pf_active,
pf_passive and iron_core. NICE recomputes its equilibrium using the retained
`config_nice.xml`. The prepared HCD geometry is a separate reference input,
not the new NICE output. Supply all three entries in the matching DD 4.1
representation. The case retains NICE development version 258, TORAX 1.4.0
and the reference actor parameters.

Case preparation loads the frozen TORAX Python configuration's
`CONFIG.numerics` and writes its selected interval to
`preprocess_settings.ymmsl`. The reference configuration derives this
interval from the second equilibrium time frame through the last frame in
the initialization IDS. The generated `source.t_min` skips the incomplete
first plasma-composition frame, while explicit `torax.t_initial` and
`torax.t_final` apply the same interval to the actor and override its
default NICE trace bounds. HCD's `tbegin=-1` and `tend=-1` accept TORAX's
requested time frames without an additional interval filter. The selected
times come from the input and configuration, with no fixed scenario
time-window override.

Use [ZijianBian/TORAX-MUSCLE3](https://github.com/ZijianBian/TORAX-MUSCLE3),
branch `feature/pds-hcdwf-torax`, based on upstream `develop` at `b4311d3`.
The fork's fixes for padded and duplicate ion labels, geometry-based initial
psi, and inherited `n_rho` settings are required for this reference case.
Set `HCDWF_TORAX_ACTOR_ROOT=/path/to/TORAX-MUSCLE3` to the checkout root.
The case links that checkout into `assets/torax-actor` and uses its
`torax_muscle3` package through `PYTHONPATH`. The existing
`TORAX-MUSCLE3/0.1.3-intel-2025b-pds` module supplies TORAX 1.4.0 and its
dependencies. Case creation checks an optional revision pin; it does not
install or update the shared module. The actor source and license remain
in the external fork.

TORBEAM and HCD2 directories must contain their Python actor packages and
matching native libraries. The case creates links to these installations;
they are not copied into Git. The JAX cache defaults to `CASE_DIR/cache/jax`.

## Generated case resources

Prepared cases contain configuration and links to input data and
installations. The HCD-only case saves `core_sources` and `waves` under
`CASE_DIR/output/hcd`. EC–TORAX saves the transport equilibrium and core
profiles under `CASE_DIR/output/transport_ec` at completion; NICE and HCD
intermediate outputs are passed between components without separate sinks.
Both workflows use the standard runner without a workflow `env.sh`.
Physical actor installations, Python environments, Rabbit tables, input
IDS, replay data, caches and simulation results remain external assets.
Moving a case requires preserving its resources or recreating it with the
new paths.
