"""Provisional BKT parameters; values have not been estimated from user data."""

_PROVISIONAL_DEFAULTS = {
    "p_init": 0.30,
    "p_guess": 0.20,
    "p_slip": 0.05,
    "p_transition": 0.10,
}

BKT_PARAMETERS_BY_SKILL = {
    skill_code: _PROVISIONAL_DEFAULTS.copy()
    for skill_code in ("SOURCE", "EVIDENCE", "CONTEXT", "VISUAL")
}


def get_bkt_parameters(skill_code: str) -> dict[str, float]:
    """Return an isolated copy of one skill's parameter set."""
    try:
        return BKT_PARAMETERS_BY_SKILL[skill_code].copy()
    except KeyError as error:
        raise ValueError(f"No BKT parameters configured for {skill_code}") from error