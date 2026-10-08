"""TORAX config file with default inner sources activated and ECRH set to zero to be coupled with ECRH model such as TORBEAM."""

import os

imas_uri = os.environ.get("PDS_HCDWF_105099_INPUT_URI")
if not imas_uri:
    raise RuntimeError(
        "PDS_HCDWF_105099_INPUT_URI is required; create the case with "
        "bin/pds-create-case hcdwf_torax before running."
    )


def get_t_values(imas_uri):
    import imas

    with imas.DBEntry(imas_uri, "r") as db:
        eq = db.get("equilibrium", lazy=True)
        # The first input frame has incomplete plasma composition.
        t_initial = eq.time[1]
        t_final = eq.time[-1]
    return t_initial, t_final


t_initial, t_final = get_t_values(imas_uri)
if os.environ.get("TORAX_T_FINAL_OFFSET"):
    t_final_offset = float(os.environ["TORAX_T_FINAL_OFFSET"])
    if t_final_offset <= 0.0:
        raise ValueError("TORAX_T_FINAL_OFFSET must be positive")
    t_final = min(t_final, t_initial + t_final_offset)

CONFIG = {
    "profile_conditions": {},
    "plasma_composition": {
        "main_ion": {"H": 1},
        "impurity": {  # Dummy impurities and z_eff replaced by M3 actor
            "species": {
                "Ne": None,
                "W": 4e-5,
            },
            "impurity_mode": "n_e_ratios_Z_eff",
        },
        "Z_eff": 1.6,
    },
    "numerics": {
        "t_initial": t_initial,
        "t_final": t_final,
        "exact_t_final": True,
        "fixed_dt": 1.0,
        "adaptive_dt": True,
        "resistivity_multiplier": 1,
        "evolve_current": True,
        "evolve_ion_heat": True,
        "evolve_electron_heat": True,
        "evolve_density": True,
    },
    # The MUSCLE3 actor replaces this initial geometry with received IMAS geometry.
    "geometry": {
        "geometry_type": "circular",
        "n_rho": 50,
    },
    "pedestal": {},
    "sources": {
        # Physics-based sources
        "ohmic": {},
        "fusion": {},
        "ei_exchange": {},
        "bremsstrahlung": {},
        "impurity_radiation": {
            "model_name": "mavrin_fit",
            "radiation_multiplier": 3.0,
        },
        # Actuators
        "ecrh": {"mode": "ZERO"},
    },
    "transport": {
        "model_name": "combined",
        "transport_models": [
            {
                "model_name": "qlknn",
                "DV_effective": False,  # True gives large increase in core T. Can create sharper density transport when False
            },
            {
                # Constant ad-hoc transport in the edge (L-mode patch).
                "model_name": "constant",
                "chi_e": 2.0,
                "chi_i": 2.0,
                "D_e": 0.2,
                "V_e": -0.2,
                "merge_mode": "overwrite",
                "rho_min": 0.9,
            },
            {
                # Constant ad-hoc transport in the core (MHD/EM patch).
                "model_name": "constant",
                "chi_e": 1.5,
                "chi_i": 1.5,
                "D_e": 0.1,
                "V_e": 0.0,
                "merge_mode": "add",
                "rho_max": 0.3,
            },
        ],
        #  Smoothing
        "smoothing_width": 0.1,
        "smooth_everywhere": False,
        # Clipping
        "chi_min": 0.05,
        "chi_max": 100,
        "D_e_min": 0.05,
    },
    "solver": {
        "solver_type": "newton_raphson",
        "use_predictor_corrector": True,
        "n_corrector_steps": 10,
        "use_pereverzev": True,
    },
    "time_step_calculator": {
        "calculator_type": "fixed",
    },
    "neoclassical": {
        "bootstrap_current": {"model_name": "sauter"},
    },
}
