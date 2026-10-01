"""Generate every shot-specific PDS input from one pulse file.

A pulse file ``cases/pulses/<shot>.yaml`` is the single place where everything that is
specific to one shot is set: the DINA and machine-description inputs used to prepare the
scenario data, the simulated time window, the time steps, an optional TORAX transport
calibration and the post-processing plot times. ``bin/pds-configure`` reads it and writes
the tool-specific files derived from it; everything else stays generic in
``workflows/<wf>/``. ``cases/pulses/TEMPLATE.yaml`` is a commented starting point.

Pulse file keys
---------------

``shot`` (int, required)
    Shot / scenario number: the directory ``$SCENARIOS_REPO/<shot>`` and the ``<shot>``
    in every generated file name.
``description`` (str, optional)
    Free text, copied as a comment into the generated files.
``workflows`` (list, required)
    Workflows this pulse is run with. Supported: ``inverse_convergence``,
    ``prescribed_transport``, ``evolutive_controller``, ``metis_from_dina``,
    ``metis_nice_inverse_from_dina``. One override file is generated per workflow.
    ``[]`` (empty) means preparation only: only ``source.env`` is written and
    ``--create`` does nothing.
``prepare`` (mapping, required) -> ``$SCENARIOS_REPO/<shot>/source.env``, the input of
``preprocessing/prepare``:

    ``source`` (str, required)             -> ``SOURCE_URI``, the DINA entry.
    ``summary`` (str, default ``source``)  -> ``SUMMARY_URI``.
    ``machine_description`` (required)     -> ``MD_PF_ACTIVE``, ``MD_PF_PASSIVE``,
        ``MD_WALL``, ``MD_IRON_CORE``. Either the name of a set or a mapping with the
        four keys ``pf_active``, ``pf_passive``, ``wall``, ``iron_core`` (URIs;
        ``iron_core`` may be ``empty``). Sets:

        ``basic``: the active ITER_MD catalogue versions (md_summary.yaml, checked
        2026-09-30): pf_active 111001/204, pf_passive 115005/3, wall 116000/5.
        ``legacy``: pf_active 111001/203, pf_passive 115005/2, wall 116000/4 -- the
        datasets the five pds-scenarios scenarios 105073/78/84/92/99 were prepared
        with; use only to reproduce them.

        ITER has no iron core, so in both sets iron_core is ``empty``: the converter
        creates an empty static iron_core IDS (a real URI is only needed for machines
        with an iron core, e.g. WEST).
    ``n_timeslices`` (int >= 2, required)  -> ``N_TIMESLICES``, the number of prepared
        slices. This slice grid is the outer time grid of inverse_convergence and
        prescribed_transport.
    ``md_layout`` (``separate`` | ``combined``, default ``separate``) -> ``MD_LAYOUT``.
        inverse_convergence and prescribed_transport read ``data/in_md`` and therefore
        need ``separate``; ``combined`` with those workflows is rejected (such a shot
        needs hand-written overrides, see ``cases/overrides/inverse_convergence_105073*``).
        The two METIS workflows do not read ``data/``: their preprocess.sh builds their
        inputs from ``source.env`` at ``--create``, so they accept either layout.
    ``metis`` (mapping, optional) with ``mode`` (``interpretative`` | ``predictive``)
        -> ``METIS_MODE`` and ``nbt`` (int) -> ``METIS_NBT``; written only if present,
        and ``--prepare`` then passes ``--metis`` to preprocessing/prepare.
    ``dd_version`` (str, default ``"4.0.0"``) -> ``IMAS_VERSION`` of the
        preprocessing/prepare run, i.e. the data-dictionary version the prepared data
        are written at (recorded as a comment in source.env). 4.0.0 is the version of
        the stored data of the existing scenarios.

``time`` (mapping, required):

    ``t_start``, ``t_end`` (float, required, ``t_end > t_start``) -- simulated window:
        inverse_convergence ``loop.t_min`` / ``loop.t_max`` (selects slices of the
        prepared grid); prescribed_transport ``source.t_min`` / ``source.t_max``;
        evolutive_controller default of ``forward_t_start`` / ``forward_t_end``;
        metis_from_dina and metis_nice_inverse_from_dina ``source_metis.t_min`` /
        ``source_metis.t_max``. source_metis (imas_muscle3 ``source_component``,
        ``iterative`` default true) streams one slice per message for every native
        slice of its input in ``[t_min, t_max]``; METIS takes its time from the message
        timestamps (``metis_clock_internal`` off), so no METIS time setting is written.
        In metis_nice_inverse_from_dina, ``source_nice`` is a ``sink_source_component``
        that has no ``t_min``/``t_max``: it re-slices its input at the timestamp of each
        METIS equilibrium it receives, so the window reaches it through METIS.
    ``transport_dt`` (float > 0, optional) -> inverse_convergence
        ``transport.torax.fixed_dt``, the TORAX step inside each outer slice interval.
    ``forward_dt`` (float > 0, optional) -> evolutive_controller ``torax.fixed_dt``,
        ``nice_evo_rd.dt`` and ``nice_evo_rd.t_interval``.
    ``forward_source_dt`` (float > 0, optional) -> evolutive_controller ``source.dt``,
        the resampling step of the input data.
    ``forward_t_start``, ``forward_t_end`` (float, default ``t_start`` / ``t_end``,
        ``forward_t_end > forward_t_start``) -- evolutive_controller forward window:
        ``source.t_min`` / ``source.t_max``; ``forward_t_end`` also sets
        ``torax.t_final`` and ``nice_evo_rd.t_end``.
    ``forward_source`` (str, optional) -> evolutive_controller ``source.source_uri``,
        the inverse result the forward run starts from. Default (not written): the
        workflow's ``imas:hdf5?path=${PDS_REPO}/cases/runs/inverse_convergence_${SHOT}/
        out_nice``, i.e. the latest inverse_convergence run of the same shot.

    Forward-window check: whenever evolutive_controller is selected (every mode,
    ``--dry-run`` included, before anything is written) the effective source is
    resolved (``$PDS_REPO``/``$SHOT`` expanded). For an existing local
    ``imas:hdf5?path=`` entry its ``equilibrium.time`` is read (read-only, lazy): a
    window outside it (tolerance 1e-6 s) is an error; otherwise the first native slice
    of the window is logged, with a warning if ``forward_t_start`` is not a native slice
    (a non-native start diverged on 105073). A non-HDF5 or not-yet-existing source only
    gets a warning: rerun after the inverse_convergence run for a hard check.

``inverse_convergence`` (mapping, optional) -> ``loop.<key>`` of inverse_convergence:
    ``max_iterations`` (int >= 1), ``tolerance`` (float > 0), ``rel_tolerance``
    (float >= 0), ``max_slices`` (int >= 0, 0 = all), ``cold_start`` (bool). Unset keys
    keep the workflow defaults of ``workflows/inverse_convergence/settings.ymmsl``.

``transport_calibration`` (mapping, optional). Omit it to keep the workflow's generic
qlknn transport. When present, a calibrated ``<wf>_<shot>_config_torax.py`` is generated
for each selected workflow with TORAX (inverse_convergence, evolutive_controller; not
prescribed_transport and the METIS workflows, which have no TORAX): the
workflow's generic ``config_torax.py`` verbatim, followed by assignments that switch
``CONFIG["transport"]`` to the calibrated model; the override points
``<torax instance>.python_config_module`` at it. Keys:

    ``model`` (required): ``bohm-gyrobohm`` (the only supported model).
    ``chi_multiplier``: applied to all four multipliers below.
    ``chi_e_bohm_multiplier``, ``chi_i_bohm_multiplier``, ``chi_e_gyrobohm_multiplier``,
    ``chi_i_gyrobohm_multiplier``: per-channel values, overriding ``chi_multiplier``.

    Each value is a number or a table ``{time_s: value}`` (times strictly increasing,
    values > 0), piecewise-linear in time and constant outside the given range. A
    multiplier left unset keeps the TORAX default 1.0.

``postprocess`` (mapping, optional):
    ``t_list`` (list of numbers) -- plot times of the validation plots
    (``workflows/inverse_convergence/postprocess.sh``). Default: 25/50/75 % of
    ``[t_start, t_end]``, rounded to 0.1 s.

Unknown keys and wrong types are errors.

Failures
--------

Pulse-file errors (unknown keys, wrong types, a ``--workflow`` not listed) and failures
common to all workflows (``source.env``, ``--prepare``) are fatal at once. A failure of
one workflow -- generating its override, its check (e.g. the evolutive_controller
forward-window check), the overwrite guard of its files, or its ``pds-create-case`` --
is reported, that workflow is skipped and the others continue; the command then exits
with code 1 and a final ``failed workflows:`` summary line.

Generated files
---------------

* ``$SCENARIOS_REPO/<shot>/source.env``
* ``$PDS_REPO/cases/overrides/generated/<wf>_<shot>.ymmsl`` for each workflow, stacked
  after the generic ``workflows/<wf>/settings.ymmsl`` by ``bin/pds-create-case``
* ``$PDS_REPO/cases/overrides/generated/<wf>_<shot>_config_torax.py`` if
  ``transport_calibration``
* with ``--create``: ``export SCENARIOS_REPO=<data root>`` appended to each new
  ``<case>/case.env``, which bin/pds-run-case.sbatch sources before post-processing

``cases/overrides/generated/`` is git-ignored: generated files are never committed.
Each file starts with a ``# GENERATED by bin/pds-configure`` marker line. An existing
target without that marker is never overwritten unless ``--force``.

Override precedence
-------------------

``bin/pds-create-case <wf> <shot>`` uses the first of:

1. the hand-written ``cases/overrides/<wf>_<shot>.ymmsl``;
2. the generated ``cases/overrides/generated/<wf>_<shot>.ymmsl``;
3. none (the workflow's generic settings only).

Precedence is per whole file: the two are never merged. A hand-written override
therefore silently shadows the generated one, and this command warns when it finds one
(the legacy shots 105073/78/84/92/99 have hand-written overrides, which always win).

To customise a generated override: copy ``cases/overrides/generated/<wf>_<shot>.ymmsl``
to ``cases/overrides/``, delete its first (marker) line and edit it; if it references a
generated ``<wf>_<shot>_config_torax.py``, copy that file to ``cases/overrides/`` too and
change the ``python_config_module`` path to the copy. From then on the pulse file no
longer affects that workflow/shot: changes to it must be carried over by hand.

Command line
------------

::

    bin/pds-configure <pulse.yaml> [--workflow WF ...] [--prepare] [--create]
                      [--force] [--dry-run] [--print-t-list]

Without options, writes the files above. ``--workflow`` restricts to a subset of
``workflows``. ``--dry-run`` prints paths and contents (and the commands ``--prepare`` /
``--create`` would run) without doing anything. ``--prepare`` then runs
``$PDS_REPO/preprocessing/prepare <shot>`` (plus ``--metis`` if ``prepare.metis`` is
set) with this interpreter as ``PREPARE_PYTHON`` (the IMAS-MUSCLE3 environment has
everything preprocessing/prepare needs) and ``IMAS_VERSION`` = ``prepare.dd_version``.
``--create`` then runs ``bin/pds-create-case -f <wf> <shot>`` for each selected
workflow, appends ``export SCENARIOS_REPO=...`` to the new case's ``case.env``, and runs
``preprocessing/check_scenario.py`` on the new case (figure ``<case>/check_<shot>.png``),
printing its OK/WARN lines (a failing check is reported, not fatal).
``--print-t-list`` prints the post-processing plot times, space separated, and exits.

Environment: ``PDS_REPO`` (default: the checkout containing this package),
``SCENARIOS_REPO`` (the scenario data root; default ``$PDS_REPO/scenarios``, which is
not committed). Both are exported to the child processes.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger("pds-configure")

MARKER_PREFIX = "# GENERATED by bin/pds-configure from "
# Default evolutive_controller source (workflows/evolutive_controller/settings.ymmsl):
# the NICE inverse output of the latest inverse_convergence run of the same shot.
FORWARD_SOURCE_DEFAULT = (
    "imas:hdf5?path=${PDS_REPO}/cases/runs/inverse_convergence_${SHOT}/out_nice"
)
TIME_TOL = 1e-6  # s, tolerance of the forward-window check
DEFAULT_DD_VERSION = "4.0.0"
LINE_LENGTH = 88

SUPPORTED_WORKFLOWS = (
    "inverse_convergence",
    "prescribed_transport",
    "evolutive_controller",
    "metis_from_dina",
    "metis_nice_inverse_from_dina",
)
# Workflow -> ymmsl instance of its TORAX actor (None: no TORAX).
TORAX_INSTANCE: dict[str, str | None] = {
    "inverse_convergence": "transport.torax",
    "prescribed_transport": None,
    "evolutive_controller": "torax",
    "metis_from_dina": None,
    "metis_nice_inverse_from_dina": None,
}
# METIS workflows: their source_component that feeds METIS (the only time-bounded
# source; source_nice of metis_nice_inverse_from_dina is a sink_source_component without
# t_min/t_max that follows METIS's timestamps).
METIS_SOURCE = {
    "metis_from_dina": "source_metis",
    "metis_nice_inverse_from_dina": "source_metis",
}
# Workflows whose settings.ymmsl reads data/in + data/in_md (the separate layout).
SEPARATE_MD_WORKFLOWS = ("inverse_convergence", "prescribed_transport")

_ITER_MD = "imas:hdf5?path=/work/imas/shared/imasdb/ITER_MD/3"
# ITER has no iron core: the converter creates an empty static iron_core IDS.
_IRON_CORE_EMPTY = "empty"
MACHINE_DESCRIPTIONS: dict[str, dict[str, str]] = {
    # Active ITER_MD catalogue versions (md_summary.yaml, checked 2026-09-30).
    "basic": {
        "pf_active": f"{_ITER_MD}/111001/204",
        "pf_passive": f"{_ITER_MD}/115005/3",
        "wall": f"{_ITER_MD}/116000/5",
        "iron_core": _IRON_CORE_EMPTY,
    },
    # The datasets the five pds-scenarios scenarios 105073/78/84/92/99 were prepared
    # with; use only to reproduce them.
    "legacy": {
        "pf_active": f"{_ITER_MD}/111001/203",
        "pf_passive": f"{_ITER_MD}/115005/2",
        "wall": f"{_ITER_MD}/116000/4",
        "iron_core": _IRON_CORE_EMPTY,
    },
}
MD_KEYS = ("pf_active", "pf_passive", "wall", "iron_core")
MD_ENV = {
    "pf_active": "MD_PF_ACTIVE",
    "pf_passive": "MD_PF_PASSIVE",
    "wall": "MD_WALL",
    "iron_core": "MD_IRON_CORE",
}
MULTIPLIERS = (
    "chi_e_bohm_multiplier",
    "chi_i_bohm_multiplier",
    "chi_e_gyrobohm_multiplier",
    "chi_i_gyrobohm_multiplier",
)
CALIBRATION_MODELS = ("bohm-gyrobohm",)
METIS_MODES = ("interpretative", "predictive")

Table = float | dict[float, float]


class ConfigError(Exception):
    """Invalid pulse file or refused action."""


@dataclass
class Pulse:
    """Validated content of a pulse file."""

    path: Path
    shot: int
    description: str | None
    workflows: list[str]
    source: str
    summary: str | None
    machine_description: dict[str, str]
    md_name: str | None
    n_timeslices: int
    md_layout: str
    metis: dict[str, Any] | None
    dd_version: str
    t_start: float
    t_end: float
    transport_dt: float | None
    forward_dt: float | None
    forward_source_dt: float | None
    forward_t_start: float
    forward_t_end: float
    forward_source: str | None
    loop: dict[str, Any] = field(default_factory=dict)
    calibration_model: str | None = None
    multipliers: dict[str, Table] = field(default_factory=dict)
    t_list: list[float] = field(default_factory=list)


# --------------------------------------------------------------------------- validation


class _Checker:
    """Type checks that name the offending key and the pulse file."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def fail(self, key: str, msg: str) -> ConfigError:
        return ConfigError(f"{self.path}: {key}: {msg}")

    def mapping(
        self,
        value: object,
        key: str,
        allowed: tuple[str, ...],
        required: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise self.fail(key, f"expected a mapping, got {type(value).__name__}")
        for k in value:
            if not isinstance(k, str) or k not in allowed:
                where = f"{key}.{k}" if key else str(k)
                raise ConfigError(
                    f"{self.path}: unknown key '{where}' (allowed: {', '.join(allowed)})"
                )
        for k in required:
            if k not in value:
                where = f"{key}.{k}" if key else k
                raise ConfigError(f"{self.path}: missing required key '{where}'")
        return value

    def string(self, value: object, key: str) -> str:
        if not isinstance(value, str) or not value:
            raise self.fail(key, f"expected a non-empty string, got {value!r}")
        return value

    def integer(self, value: object, key: str, minimum: int | None = None) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise self.fail(key, f"expected an integer, got {value!r}")
        if minimum is not None and value < minimum:
            raise self.fail(key, f"must be >= {minimum}, got {value}")
        return value

    def number(
        self,
        value: object,
        key: str,
        positive: bool = False,
        nonnegative: bool = False,
    ) -> float:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise self.fail(key, f"expected a number, got {value!r}")
        result = float(value)
        if positive and result <= 0:
            raise self.fail(key, f"must be > 0, got {value}")
        if nonnegative and result < 0:
            raise self.fail(key, f"must be >= 0, got {value}")
        return result

    def boolean(self, value: object, key: str) -> bool:
        if not isinstance(value, bool):
            raise self.fail(key, f"expected true or false, got {value!r}")
        return value

    def choice(self, value: object, key: str, choices: tuple[str, ...]) -> str:
        if value not in choices:
            raise self.fail(key, f"must be one of {', '.join(choices)}, got {value!r}")
        return str(value)

    def table(self, value: object, key: str) -> Table:
        if not isinstance(value, dict):
            return self.number(value, key, positive=True)
        if not value:
            raise self.fail(key, "empty time table")
        result: dict[float, float] = {}
        previous: float | None = None
        for t, v in value.items():
            time = self.number(t, f"{key} (time {t!r})")
            if previous is not None and time <= previous:
                raise self.fail(key, f"times must be strictly increasing ({t!r})")
            result[time] = self.number(v, f"{key}[{t!r}]", positive=True)
            previous = time
        return result


def load_pulse(path: Path) -> Pulse:
    """Read and strictly validate a pulse file."""
    try:
        raw = yaml.safe_load(path.read_text())
    except OSError as exc:
        raise ConfigError(f"cannot read pulse file {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path}: invalid YAML: {exc}") from exc
    c = _Checker(path)
    top = c.mapping(
        raw,
        "",
        (
            "shot",
            "description",
            "workflows",
            "prepare",
            "time",
            "inverse_convergence",
            "transport_calibration",
            "postprocess",
        ),
        ("shot", "workflows", "prepare", "time"),
    )
    shot = c.integer(top["shot"], "shot", minimum=0)
    if path.stem.isdigit() and int(path.stem) != shot:
        logger.warning("%s: shot %d does not match the file name", path, shot)
    description = None
    if top.get("description") is not None:
        description = c.string(top["description"], "description")

    wfs = top["workflows"]
    if not isinstance(wfs, list):
        raise c.fail("workflows", "expected a list ([] for preparation only)")
    workflows: list[str] = []
    for i, wf in enumerate(wfs):
        name = c.choice(wf, f"workflows[{i}]", SUPPORTED_WORKFLOWS)
        if name in workflows:
            raise c.fail("workflows", f"'{name}' listed twice")
        workflows.append(name)

    prep = c.mapping(
        top["prepare"],
        "prepare",
        (
            "source",
            "summary",
            "machine_description",
            "n_timeslices",
            "md_layout",
            "metis",
            "dd_version",
        ),
        ("source", "machine_description", "n_timeslices"),
    )
    source = c.string(prep["source"], "prepare.source")
    summary = None
    if prep.get("summary") is not None:
        summary = c.string(prep["summary"], "prepare.summary")
    md_raw = prep["machine_description"]
    md_name: str | None = None
    if isinstance(md_raw, str):
        md_name = c.choice(
            md_raw, "prepare.machine_description", tuple(MACHINE_DESCRIPTIONS)
        )
        machine_description = dict(MACHINE_DESCRIPTIONS[md_name])
    else:
        md_map = c.mapping(md_raw, "prepare.machine_description", MD_KEYS, MD_KEYS)
        machine_description = {
            k: c.string(md_map[k], f"prepare.machine_description.{k}") for k in MD_KEYS
        }
    n_timeslices = c.integer(prep["n_timeslices"], "prepare.n_timeslices", minimum=2)
    md_layout = c.choice(
        prep.get("md_layout", "separate"), "prepare.md_layout", ("separate", "combined")
    )
    metis: dict[str, Any] | None = None
    if prep.get("metis") is not None:
        m = c.mapping(prep["metis"], "prepare.metis", ("mode", "nbt"))
        metis = {}
        if "mode" in m:
            metis["mode"] = c.choice(m["mode"], "prepare.metis.mode", METIS_MODES)
        if "nbt" in m:
            metis["nbt"] = c.integer(m["nbt"], "prepare.metis.nbt", minimum=2)
    dd_version = DEFAULT_DD_VERSION
    if prep.get("dd_version") is not None:
        dd_version = c.string(prep["dd_version"], "prepare.dd_version")
        if not re.fullmatch(r"\d+\.\d+\.\d+", dd_version):
            raise c.fail(
                "prepare.dd_version",
                f"expected a version like '4.0.0', got {dd_version!r}",
            )

    tm = c.mapping(
        top["time"],
        "time",
        (
            "t_start",
            "t_end",
            "transport_dt",
            "forward_dt",
            "forward_source_dt",
            "forward_t_start",
            "forward_t_end",
            "forward_source",
        ),
        ("t_start", "t_end"),
    )
    t_start = c.number(tm["t_start"], "time.t_start")
    t_end = c.number(tm["t_end"], "time.t_end")
    if t_end <= t_start:
        raise c.fail("time.t_end", f"must be > time.t_start ({t_end} <= {t_start})")
    steps: dict[str, float | None] = {}
    for k in ("transport_dt", "forward_dt", "forward_source_dt"):
        steps[k] = None
        if tm.get(k) is not None:
            steps[k] = c.number(tm[k], f"time.{k}", positive=True)
    forward_t_start = t_start
    if tm.get("forward_t_start") is not None:
        forward_t_start = c.number(tm["forward_t_start"], "time.forward_t_start")
    forward_t_end = t_end
    if tm.get("forward_t_end") is not None:
        forward_t_end = c.number(tm["forward_t_end"], "time.forward_t_end")
    if forward_t_end <= forward_t_start:
        raise c.fail(
            "time.forward_t_end",
            f"must be > time.forward_t_start ({forward_t_end} <= {forward_t_start})",
        )
    forward_source: str | None = None
    if tm.get("forward_source") is not None:
        forward_source = c.string(tm["forward_source"], "time.forward_source")

    loop: dict[str, Any] = {}
    if top.get("inverse_convergence") is not None:
        ic = c.mapping(
            top["inverse_convergence"],
            "inverse_convergence",
            (
                "max_iterations",
                "tolerance",
                "rel_tolerance",
                "max_slices",
                "cold_start",
            ),
        )
        checks = {
            "max_iterations": lambda v, k: c.integer(v, k, minimum=1),
            "tolerance": lambda v, k: c.number(v, k, positive=True),
            "rel_tolerance": lambda v, k: c.number(v, k, nonnegative=True),
            "max_slices": lambda v, k: c.integer(v, k, minimum=0),
            "cold_start": c.boolean,
        }
        for k, v in ic.items():
            loop[k] = checks[k](v, f"inverse_convergence.{k}")

    calibration_model: str | None = None
    multipliers: dict[str, Table] = {}
    if top.get("transport_calibration") is not None:
        tc = c.mapping(
            top["transport_calibration"],
            "transport_calibration",
            ("model", "chi_multiplier", *MULTIPLIERS),
            ("model",),
        )
        calibration_model = c.choice(
            tc["model"], "transport_calibration.model", CALIBRATION_MODELS
        )
        common = None
        if tc.get("chi_multiplier") is not None:
            common = c.table(
                tc["chi_multiplier"], "transport_calibration.chi_multiplier"
            )
        for k in MULTIPLIERS:
            if tc.get(k) is not None:
                multipliers[k] = c.table(tc[k], f"transport_calibration.{k}")
            elif common is not None:
                multipliers[k] = common

    if top.get("postprocess") is not None:
        pp = c.mapping(top["postprocess"], "postprocess", ("t_list",))
    else:
        pp = {}
    if pp.get("t_list") is not None:
        tl = pp["t_list"]
        if not isinstance(tl, list) or not tl:
            raise c.fail("postprocess.t_list", "expected a non-empty list of numbers")
        t_list = [c.number(t, f"postprocess.t_list[{i}]") for i, t in enumerate(tl)]
        for t in t_list:
            if not t_start <= t <= t_end:
                logger.warning(
                    "%s: postprocess.t_list time %g is outside [t_start, t_end]",
                    path,
                    t,
                )
    else:
        span = t_end - t_start
        t_list = [round(t_start + f * span, 1) for f in (0.25, 0.5, 0.75)]

    return Pulse(
        path=path,
        shot=shot,
        description=description,
        workflows=workflows,
        source=source,
        summary=summary,
        machine_description=machine_description,
        md_name=md_name,
        n_timeslices=n_timeslices,
        md_layout=md_layout,
        metis=metis,
        dd_version=dd_version,
        t_start=t_start,
        t_end=t_end,
        transport_dt=steps["transport_dt"],
        forward_dt=steps["forward_dt"],
        forward_source_dt=steps["forward_source_dt"],
        forward_t_start=forward_t_start,
        forward_t_end=forward_t_end,
        forward_source=forward_source,
        loop=loop,
        calibration_model=calibration_model,
        multipliers=multipliers,
        t_list=t_list,
    )


# --------------------------------------------------------------------------- rendering


def marker(pulse: Pulse, pds_repo: Path) -> str:
    """The first line of every generated file."""
    try:
        shown = pulse.path.resolve().relative_to(pds_repo.resolve())
    except ValueError:
        shown = pulse.path.resolve()
    return f"{MARKER_PREFIX}{shown} -- edit that file and rerun; do not edit this one"


def _fmt_time(t: float) -> str:
    return f"{t:g}"


def render_source_env(pulse: Pulse, mark: str) -> str:
    """source.env for preprocessing/prepare."""
    md = pulse.machine_description
    lines = [
        mark,
        "# Inputs that preprocessing/prepare turns into data/. Read-only sources on the"
        " ITER SDCC cluster.",
        f"# data-dictionary version: IMAS_VERSION={pulse.dd_version} (prepare.dd_version,"
        " exported by pds-configure --prepare)",
    ]
    if pulse.description:
        lines.append(f"# {pulse.description}")
    lines.append(f'SOURCE_URI="{pulse.source}"')
    summary = pulse.summary if pulse.summary is not None else "$SOURCE_URI"
    lines.append(f'SUMMARY_URI="{summary}"')
    if pulse.md_name:
        lines.append(f"# machine description: set '{pulse.md_name}'")
    for k in MD_KEYS:
        line = f'{MD_ENV[k]}="{md[k]}"'
        if k == "iron_core" and md[k] == _IRON_CORE_EMPTY:
            line += "   # empty for ITER"
        lines.append(line)
    lines.append(f"N_TIMESLICES={pulse.n_timeslices}")
    if pulse.md_layout != "separate":
        lines.append(f"MD_LAYOUT={pulse.md_layout}")
    if pulse.metis is not None:
        if "mode" in pulse.metis:
            lines.append(f"METIS_MODE={pulse.metis['mode']}")
        if "nbt" in pulse.metis:
            lines.append(f"METIS_NBT={pulse.metis['nbt']}")
    return "\n".join(lines) + "\n"


def _yaml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return repr(value)
    return str(value)


def torax_config_name(wf: str, shot: int) -> str:
    return f"{wf}_{shot}_config_torax.py"


def render_override(pulse: Pulse, wf: str, mark: str) -> str:
    """cases/overrides/generated/<wf>_<shot>.ymmsl."""
    if pulse.md_layout == "combined" and wf in SEPARATE_MD_WORKFLOWS:
        raise ConfigError(
            f"{pulse.path}: prepare.md_layout is 'combined' but workflow {wf} reads "
            "data/in + data/in_md (the separate layout); a combined-layout shot needs "
            "hand-written overrides for it (see cases/overrides/inverse_convergence_"
            "105073*), so it cannot be generated"
        )
    groups: list[tuple[str, list[tuple[str, object]]]] = []
    window = [("t_min", pulse.t_start), ("t_max", pulse.t_end)]
    if wf == "inverse_convergence":
        groups.append(
            (
                "time.t_start / time.t_end: slices of the prepared grid the loop visits",
                [(f"loop.{k}", v) for k, v in window],
            )
        )
        if pulse.transport_dt is not None:
            groups.append(
                (
                    "time.transport_dt: TORAX step inside each slice interval",
                    [("transport.torax.fixed_dt", pulse.transport_dt)],
                )
            )
        if pulse.loop:
            groups.append(
                (
                    "inverse_convergence: outer loop tuning",
                    [(f"loop.{k}", v) for k, v in pulse.loop.items()],
                )
            )
    elif wf == "prescribed_transport":
        groups.append(
            (
                "time.t_start / time.t_end: time range loaded by the source",
                [(f"source.{k}", v) for k, v in window],
            )
        )
        if pulse.transport_dt is not None or pulse.calibration_model is not None:
            logger.info(
                "prescribed_transport has no TORAX: time.transport_dt and "
                "transport_calibration do not apply to it"
            )
    elif wf == "evolutive_controller":
        if pulse.forward_source is not None:
            groups.append(
                (
                    "time.forward_source: inverse result the forward run starts from",
                    [("source.source_uri", json.dumps(pulse.forward_source))],
                )
            )
        groups.append(
            (
                "time.forward_t_start / time.forward_t_end: time range loaded by the "
                "source",
                [
                    ("source.t_min", pulse.forward_t_start),
                    ("source.t_max", pulse.forward_t_end),
                ],
            )
        )
        if pulse.forward_source_dt is not None:
            groups.append(
                (
                    "time.forward_source_dt: resampling step of the source",
                    [("source.dt", pulse.forward_source_dt)],
                )
            )
        if pulse.forward_dt is not None:
            groups.append(
                (
                    "time.forward_dt: TORAX and NICE evolutive step",
                    [
                        ("torax.fixed_dt", pulse.forward_dt),
                        ("nice_evo_rd.dt", pulse.forward_dt),
                        ("nice_evo_rd.t_interval", pulse.forward_dt),
                    ],
                )
            )
        groups.append(
            (
                "time.forward_t_end: end of the forward simulation",
                [
                    ("torax.t_final", pulse.forward_t_end),
                    ("nice_evo_rd.t_end", pulse.forward_t_end),
                ],
            )
        )
    elif wf in METIS_SOURCE:
        src = METIS_SOURCE[wf]
        groups.append(
            (
                "time.t_start / time.t_end: time range streamed to METIS, one native "
                "slice per message",
                [(f"{src}.{k}", v) for k, v in window],
            )
        )
        if pulse.transport_dt is not None or pulse.calibration_model is not None:
            logger.info(
                "%s has no TORAX: time.transport_dt and transport_calibration do not "
                "apply to it",
                wf,
            )
    else:  # pragma: no cover - rejected by load_pulse
        raise ConfigError(f"unsupported workflow {wf}")

    instance = TORAX_INSTANCE[wf]
    if pulse.calibration_model is not None and instance is not None:
        name = torax_config_name(wf, pulse.shot)
        groups.append(
            (
                "transport_calibration: calibrated TORAX config generated alongside",
                [
                    (
                        f"{instance}.python_config_module",
                        f"${{PDS_REPO}}/cases/overrides/generated/{name}",
                    )
                ],
            )
        )

    lines = [mark, "ymmsl_version: v0.2"]
    lines.append(f"# Per-shot settings for {wf} on {pulse.shot}, stacked after the")
    lines.append(f"# generic workflows/{wf}/settings.ymmsl by bin/pds-create-case.")
    if pulse.description:
        lines.append(f"# {pulse.description}")
    lines.append("settings:")
    for comment, items in groups:
        lines.append(f"  # {comment}")
        lines.extend(f"  {k}: {_yaml_value(v)}" for k, v in items)
    return "\n".join(lines) + "\n"


def _py_literal(value: Table) -> list[str]:
    """Items of a multiplier rendered as Python literal pieces."""
    if isinstance(value, dict):
        return [f"{float(t)!r}: {float(v)!r}" for t, v in value.items()]
    return [repr(float(value))]


def _py_assignment(key: str, value: Table) -> str:
    """One ``CONFIG["transport"][key] = ...`` statement, in ruff format style."""
    lhs = f'CONFIG["transport"]["{key}"] = '
    items = _py_literal(value)
    if not isinstance(value, dict):
        return lhs + items[0]
    one_line = lhs + "{" + ", ".join(items) + "}"
    if len(one_line) <= LINE_LENGTH:
        return one_line
    body = "".join(f"    {item},\n" for item in items)
    return lhs + "{\n" + body + "}"


def render_torax_config(pulse: Pulse, wf: str, generic: str, mark: str) -> str:
    """Generic config_torax.py plus the calibration assignments."""
    text = generic if generic.endswith("\n") else generic + "\n"
    lines = [
        "",
        mark,
        f"# transport_calibration of shot {pulse.shot}: switch the generic transport "
        "block",
        "# to the calibrated model; unset multipliers keep the TORAX default 1.0.",
        f'CONFIG["transport"]["model_name"] = "{pulse.calibration_model}"',
    ]
    lines.extend(_py_assignment(k, v) for k, v in pulse.multipliers.items())
    return f"{mark}\n{text}" + "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- actions


@dataclass
class Output:
    path: Path
    content: str


def source_env_output(pulse: Pulse, pds_repo: Path, scenarios_repo: Path) -> Output:
    """The source.env that would be written, without touching the disk."""
    return Output(
        scenarios_repo / str(pulse.shot) / "source.env",
        render_source_env(pulse, marker(pulse, pds_repo)),
    )


def workflow_outputs(pulse: Pulse, wf: str, pds_repo: Path) -> list[Output]:
    """The files that would be written for one workflow, without touching the disk."""
    mark = marker(pulse, pds_repo)
    overrides = pds_repo / "cases" / "overrides" / "generated"
    outputs = [
        Output(overrides / f"{wf}_{pulse.shot}.ymmsl", render_override(pulse, wf, mark))
    ]
    if pulse.calibration_model is not None and TORAX_INSTANCE[wf] is not None:
        generic_path = pds_repo / "workflows" / wf / "config_torax.py"
        try:
            generic = generic_path.read_text()
        except OSError as exc:
            raise ConfigError(f"cannot read {generic_path}: {exc}") from exc
        outputs.append(
            Output(
                overrides / torax_config_name(wf, pulse.shot),
                render_torax_config(pulse, wf, generic, mark),
            )
        )
    return outputs


def check_overwrite(outputs: list[Output], force: bool) -> None:
    """Refuse to replace a file that bin/pds-configure did not write."""
    for out in outputs:
        if not out.path.exists() or force:
            continue
        with out.path.open() as f:
            first = f.readline()
        if not first.startswith(MARKER_PREFIX):
            raise ConfigError(
                f"{out.path} exists and was not generated by bin/pds-configure "
                "(no marker line); move it away or rerun with --force"
            )


def warn_hand_written(pulse: Pulse, workflows: list[str], pds_repo: Path) -> None:
    """Warn about a cases/overrides/<wf>_<shot>.ymmsl that shadows the generated one."""
    for wf in workflows:
        name = f"{wf}_{pulse.shot}.ymmsl"
        path = pds_repo / "cases" / "overrides" / name
        if not path.is_file():
            continue
        with path.open() as f:
            first = f.readline()
        if first.startswith(MARKER_PREFIX):
            logger.warning(
                "warning: cases/overrides/%s is a stale generated file from the old "
                "location; it takes precedence over cases/overrides/generated/%s in "
                "pds-create-case and should be deleted",
                name,
                name,
            )
        else:
            logger.warning(
                "warning: hand-written override cases/overrides/%s exists and takes "
                "precedence; the generated cases/overrides/generated/%s is ignored by "
                "pds-create-case",
                name,
                name,
            )


def forward_source_uri(pulse: Pulse, pds_repo: Path) -> str:
    """Effective evolutive_controller source URI, with PDS_REPO / SHOT expanded."""
    uri = pulse.forward_source or FORWARD_SOURCE_DEFAULT
    return uri.replace("${PDS_REPO}", str(pds_repo)).replace("${SHOT}", str(pulse.shot))


def _local_hdf5_path(uri: str) -> Path | None:
    """The directory of an ``imas:hdf5?path=<dir>`` URI, else None."""
    m = re.fullmatch(r"imas:hdf5\?path=([^;&]+)", uri.strip())
    if m is None:
        return None
    return Path(os.path.expandvars(m.group(1)))


def _equilibrium_times(uri: str) -> list[float]:
    """equilibrium.time of a local HDF5 entry, read lazily and read-only."""
    os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")
    try:
        import imas  # only needed for this check

        with imas.DBEntry(uri, "r") as entry:
            eq = entry.get("equilibrium", lazy=True, autoconvert=False)
            times = [float(t) for t in eq.time]
    except Exception as exc:  # any failure to read is a config error
        raise ConfigError(
            f"forward source {uri}: cannot read equilibrium.time: {exc}"
        ) from exc
    if not times:
        raise ConfigError(f"forward source {uri}: equilibrium.time is empty")
    return times


def check_forward_window(pulse: Pulse, pds_repo: Path) -> None:
    """Check [forward_t_start, forward_t_end] against the inverse result it reads."""
    a, b = pulse.forward_t_start, pulse.forward_t_end
    uri = forward_source_uri(pulse, pds_repo)
    path = _local_hdf5_path(uri)
    if path is None or not (path / "master.h5").is_file():
        reason = "not a local HDF5 entry" if path is None else "does not exist yet"
        logger.warning(
            "warning: cannot check the forward window against %s (%s); make sure it "
            "covers [%g, %g]; rerun bin/pds-configure after the inverse_convergence "
            "run for a hard check",
            uri,
            reason,
            a,
            b,
        )
        return
    times = _equilibrium_times(uri)
    first, last = times[0], times[-1]
    if a < first - TIME_TOL or b > last + TIME_TOL:
        raise ConfigError(
            f"{pulse.path}: forward window [{a:g}, {b:g}] "
            "(time.forward_t_start / time.forward_t_end) is not covered by the forward "
            f"source {uri}, whose equilibrium spans [{first:g}, {last:g}] s "
            f"({len(times)} slices)"
        )
    start = next(t for t in times if t >= a - TIME_TOL)
    logger.info(
        "evolutive_controller: first native slice of the forward window is "
        "t = %r s of %s (%d slices in [%g, %g] s)",
        start,
        uri,
        len(times),
        first,
        last,
    )
    if abs(start - a) > TIME_TOL:
        before = max((t for t in times if t < a), default=None)
        nearest = ", ".join(f"{t!r}" for t in (before, start) if t is not None)
        logger.warning(
            "warning: time.forward_t_start = %g is not a native slice of %s (nearest "
            "native slices: %s s); the source then starts from the next native slice "
            "or, with time.forward_source_dt set, from a state interpolated at "
            "forward_t_start -- seeding the forward run from a non-native/other slice "
            "diverged on 105073 (see cases/overrides/evolutive_controller_105073.ymmsl); "
            "prefer one of the native values",
            a,
            uri,
            nearest,
        )


def write_outputs(outputs: list[Output]) -> None:
    for out in outputs:
        out.path.parent.mkdir(parents=True, exist_ok=True)
        out.path.write_text(out.content)
        logger.info("wrote %s", out.path)


def prepare_command(pulse: Pulse, pds_repo: Path) -> list[str]:
    cmd = [str(pds_repo / "preprocessing" / "prepare"), str(pulse.shot)]
    if pulse.metis is not None:
        cmd.append("--metis")
    return cmd


def create_command(wf: str, pulse: Pulse, pds_repo: Path) -> list[str]:
    return [str(pds_repo / "bin" / "pds-create-case"), "-f", wf, str(pulse.shot)]


def _run(cmd: list[str], env: dict[str, str], capture: bool = False) -> str:
    logger.info("running %s", " ".join(cmd))
    result = subprocess.run(
        cmd, env=env, check=False, text=True, capture_output=capture
    )
    if result.returncode != 0:
        detail = ""
        if capture and result.stderr:
            # The last lines carry the error; a MATLAB preprocess can print thousands.
            tail = result.stderr.strip().splitlines()[-20:]
            detail = ":\n  " + "\n  ".join(tail)
        raise ConfigError(f"{cmd[0]} failed with exit code {result.returncode}{detail}")
    return result.stdout if capture else ""


def run_create(
    pulse: Pulse,
    workflows: list[str],
    pds_repo: Path,
    scenarios_repo: Path,
    env: dict[str, str],
    failed: dict[str, str],
) -> None:
    """Create one case per workflow; a failing workflow is recorded in ``failed``."""
    check = pds_repo / "preprocessing" / "check_scenario.py"
    for wf in workflows:
        try:
            out = _run(create_command(wf, pulse, pds_repo), env, capture=True)
            lines = [line for line in out.splitlines() if line.strip()]
            if not lines:
                raise ConfigError(f"pds-create-case printed no case dir for {wf}")
        except ConfigError as exc:
            _fail_workflow(failed, wf, exc)
            continue
        case_dir = Path(lines[-1].strip())
        print(f"{wf}: case {case_dir}")
        # bin/pds-run-case.sbatch sources case.env right before postprocess.sh, so the
        # post-processing reads this data root without SCENARIOS_REPO exported at submit.
        with (case_dir / "case.env").open("a") as f:
            f.write(
                f"export SCENARIOS_REPO={shlex.quote(str(scenarios_repo.resolve()))}\n"
            )
        if not check.exists():
            logger.warning("%s not found; skipping the configuration check plot", check)
            continue
        result = subprocess.run(
            [
                sys.executable,
                str(check),
                str(pulse.shot),
                "--case",
                str(case_dir),
                "--out",
                str(case_dir / f"check_{pulse.shot}.png"),
            ],
            env=env,
            check=False,
            text=True,
            capture_output=True,
        )
        if result.returncode != 0:
            logger.warning(
                "check_scenario.py exited with code %d for %s; continuing "
                "(the case itself was created)",
                result.returncode,
                wf,
            )
        for line in result.stdout.splitlines():
            if line.startswith(("OK", "WARN")):
                print(f"  {line}")


def _fail_workflow(failed: dict[str, str], wf: str, exc: ConfigError) -> None:
    """Report a per-workflow failure; the caller skips that workflow."""
    failed[wf] = str(exc)
    sys.stdout.flush()
    print(f"pds-configure: error: {wf}: {exc}", file=sys.stderr)
    print(f"pds-configure: {wf}: skipped, continuing with the others", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pds-configure",
        description="Generate the shot-specific PDS files from a pulse file "
        "(cases/pulses/<shot>.yaml).",
    )
    parser.add_argument(
        "pulse", type=Path, help="pulse file, e.g. cases/pulses/105033.yaml"
    )
    parser.add_argument(
        "--workflow",
        action="append",
        metavar="WF",
        help="only this workflow (repeatable; must be listed in the pulse file)",
    )
    parser.add_argument(
        "--prepare",
        action="store_true",
        help="run preprocessing/prepare afterwards",
    )
    parser.add_argument(
        "--create",
        action="store_true",
        help="run bin/pds-create-case and preprocessing/check_scenario.py afterwards",
    )
    parser.add_argument(
        "--force", action="store_true", help="overwrite files without the marker line"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print what would be done, change nothing",
    )
    parser.add_argument(
        "--print-t-list",
        action="store_true",
        help="print the post-processing plot times and exit",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="pds-configure: %(message)s")
    pds_repo = Path(
        os.environ.get("PDS_REPO") or Path(__file__).resolve().parent.parent
    )
    scenarios_repo = Path(os.environ.get("SCENARIOS_REPO") or pds_repo / "scenarios")
    try:
        pulse = load_pulse(args.pulse)
        if args.print_t_list:
            print(" ".join(_fmt_time(t) for t in pulse.t_list))
            return 0
        selected = pulse.workflows
        if args.workflow:
            for wf in args.workflow:
                if wf not in pulse.workflows:
                    raise ConfigError(
                        f"--workflow {wf}: not in the workflows of {pulse.path} "
                        f"({', '.join(pulse.workflows)})"
                    )
            selected = [wf for wf in pulse.workflows if wf in args.workflow]
        source_env = source_env_output(pulse, pds_repo, scenarios_repo)
        check_overwrite([source_env], args.force)
        # Per-workflow generation and checks: a failure skips that workflow only.
        failed: dict[str, str] = {}
        workflows: list[str] = []
        outputs = [source_env]
        for wf in selected:
            try:
                wf_outputs = workflow_outputs(pulse, wf, pds_repo)
                if wf == "evolutive_controller":
                    check_forward_window(pulse, pds_repo)
                check_overwrite(wf_outputs, args.force)
            except ConfigError as exc:
                _fail_workflow(failed, wf, exc)
                continue
            workflows.append(wf)
            outputs.extend(wf_outputs)
        warn_hand_written(pulse, workflows, pds_repo)
        env = dict(os.environ)
        env.update(
            PDS_REPO=str(pds_repo),
            SCENARIOS_REPO=str(scenarios_repo),
            PREPARE_PYTHON=env.get("PREPARE_PYTHON", sys.executable),
        )
        prepare_env = dict(env, IMAS_VERSION=pulse.dd_version)
        if args.dry_run:
            for out in outputs:
                print(f"==> {out.path}")
                print(out.content, end="")
            if args.prepare:
                cmd = prepare_command(pulse, pds_repo)
                print(
                    f"would run: IMAS_VERSION={pulse.dd_version} "
                    f"SCENARIOS_REPO={scenarios_repo} " + " ".join(cmd)
                )
            if args.create:
                if not selected:
                    print("would create nothing: workflows is empty (preparation only)")
                for wf in workflows:
                    cmd = create_command(wf, pulse, pds_repo)
                    print(
                        "would run: " + " ".join(cmd) + " + case.env SCENARIOS_REPO"
                        " + preprocessing/check_scenario.py"
                    )
        else:
            write_outputs(outputs)
            if args.prepare:
                _run(prepare_command(pulse, pds_repo), prepare_env)
            if args.create:
                if not selected:
                    print(
                        f"{pulse.path}: workflows is empty (preparation only); "
                        "--create has nothing to create"
                    )
                run_create(pulse, workflows, pds_repo, scenarios_repo, env, failed)
    except ConfigError as exc:
        print(f"pds-configure: error: {exc}", file=sys.stderr)
        return 1
    if failed:
        sys.stdout.flush()
        print(
            f"pds-configure: failed workflows: {', '.join(failed)} "
            f"(succeeded: {', '.join(wf for wf in selected if wf not in failed) or 'none'})",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
