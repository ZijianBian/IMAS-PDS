# plasmaless_controller

## What it does

`evolutive_controller` with the plant replaced: the PCSSP `magnetic_controller`
(`controllers/KCURR_RZIp/`) is closed on the plasmaless coil+vessel circuit model (no
plasma) instead of NICE direct evolutive (`nice_evo_rd`), and there is no transport (no
TORAX, `temporal_coupler`, transport sink or recorders). It tests the controller and the
coil/vessel circuits alone.

`magnetic_controller` and `sink_control` are the same as in `evolutive_controller`;
`source` also sends the inverse `pf_active`, and `waveform_editor` uses this directory's
`waveforms.yaml`, so all plasma and coil data come from the inverse run (see below). The `plasmaless` actor (MATLAB, from the plasmaless repository,
`muscle3/muscle_plasmaless_actor.m`; ports, timing and assumptions in that folder's
README) takes nice_evo_rd's place on the controller ports: it receives the F_INIT
equilibrium + pf_active, sends `equilibrium_o_i` + `pf_active_o_i` every `dt` (first at
t0 + dt) and receives the controller's `pf_active` voltages. Its `equilibrium_o_i` is a
reference pass-through (ip and boundary geometric axis of the F_INIT equilibrium,
interpolated in time), so the controller's Ip/R/Z errors are zero and only the coil
current loop acts. It also sends the vessel currents (`pf_passive_o_i`), written with
the other outputs by `sink_equilibrium` to `<run_dir>/out_plasmaless`.

## Data flow (shot 105084 case)

Plasma and coil data come only from the NICE inverse run (`nice_out` of
`cases/runs/metis_nice_inverse_from_dina_<shot>`); only machine descriptions come from
elsewhere. Nothing is read from pds-scenarios `<shot>/data/in` (DINA).

- `source` (non-iterative): one message per port with the native `nice_out` slices in
  [`source.t_min`, `source.t_max`] (19 slices for 105084, 136.2276 .. 251.0776 s); its
  first time is t0. Ports `equilibrium_out` and `pf_active_out`.
- `waveform_editor` (`workflows/plasmaless_controller/waveforms.yaml`, export time base =
  the received equilibrium times): equilibrium passed through whole; `pf_active` = machine
  description of `<shot>/data/in_md` with the coil currents and voltages of the inverse
  `pf_active` (port `pf_active_in`, resampled onto the equilibrium times, closest sample).

| Quantity | Consumer | Origin |
|---|---|---|
| equilibrium (ip, boundary incl. outline and geometric axis, profiles, b0) | controller (Ip/R/Z references), plasmaless (pass-through) | `nice_out` equilibrium |
| `vacuum_toroidal_field/r0` | nobody in this workflow | empty in `nice_out` (not overlaid any more) |
| pf_active coil current | controller (coil-current reference, R*I feed-forward), plasmaless (initial currents) | `nice_out` pf_active |
| pf_active coil voltage | plasmaless (first-step voltages at t0) | `nice_out` pf_active; for 105084 these equal the DINA `data/in` voltages of the closest DINA sample exactly (carried through the inverse run, not computed by it) |
| pf_active geometry, turns, resistance, limits; wall, pf_passive, iron_core | controller (resistances) | pds-scenarios `<shot>/data/in_md` |
| model em_coupling, pf_active, pf_passive | plasmaless | plasmaless repository `data/md_dd4` (default `md_uri`) |

- `plasmaless`: coil names must match the F_INIT pf_active names exactly (CS3U ... PF6,
  VS3U, VS3L; `nice_out` and `data/in_md` use the same 14 names in the same order).

## Running it

Prerequisites: pds-scenarios data for the shot, a completed `metis_nice_inverse_from_dina`
run for the shot in `cases/runs/metis_nice_inverse_from_dina_<shot>` (a symlink to another
clone's run directory works), and a checkout of the plasmaless repository. Set
`PLASMALESS_REPO` to your (or a colleague's) clone before running; the default in the
`plasmaless` program (`workflows/lib/easybuild_programs.ymmsl`) is one user's clone,
`/home/ITER/schneim/public/git/plasmaless-tokamak-circuits`. The model machine description
ships with that repository (`data/md_dd4`), so no `plasmaless.md_uri` is needed.

```bash
export PLASMALESS_REPO=<your clone of plasmaless-tokamak-circuits>
bin/pds-create-case plasmaless_controller 105084
sbatch bin/pds-run-case.sbatch cases/plasmaless_controller_105084
```

Per-shot settings (source window, `plasmaless.t_end`) are in
`cases/overrides/plasmaless_controller_<shot>.ymmsl`. Two MATLAB sessions run (controller
and plasmaless).
