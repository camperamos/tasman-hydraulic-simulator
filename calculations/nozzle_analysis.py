import math
import numpy as np


def nozzle_analysis(
    flow_rate_bpm,
    density_ppg,
    discharge_coefficient,
    nozzle_configs,
    step=0.5
):
    """
    Exact replication of Excel LET-based nozzle analysis:
    - Flow rate table
    - Fluid velocity
    - Nozzle pressure drop
    """

    # ─────────────────────────
    # Total Flow Area (in²)
    # ─────────────────────────
    tfa_in2 = 0.0
    for cfg in nozzle_configs:
        count = cfg["count"]
        diameter = cfg["diameter"]

        if count > 0 and diameter > 0:
            tfa_in2 += count * (math.pi / 4.0) * (diameter ** 2)

    if tfa_in2 <= 0:
        return None

    # ─────────────────────────
    # Flow table (Excel LET logic)
    # ─────────────────────────
    Qin = flow_rate_bpm
    base = np.arange(0, Qin, step)

    if len(base) == 0 or base[-1] != Qin:
        base = np.append(base, Qin)

    # ─────────────────────────
    # Constants & conversions
    # ─────────────────────────
    g_c = 32.174

    # Density: ppg → lb/ft³
    rho_lb_ft3 = density_ppg * 7.48052

    # Area: in² → ft²
    area_ft2 = tfa_in2 / 144.0

    velocities = []
    pressure_drops = []

    # ─────────────────────────
    # Calculations per flow rate
    # ─────────────────────────
    for Q in base:
        # Flow rate: bpm → ft³/s
        Q_ft3_s = Q * 0.093576

        if area_ft2 == 0:
            velocity = 0.0
            dp = 0.0
        else:
            velocity = Q_ft3_s / area_ft2
            dp = (
                (rho_lb_ft3 / (2 * g_c))
                * ((Q_ft3_s / (discharge_coefficient * area_ft2)) ** 2)
                / 144.0
            )

        velocities.append(velocity)
        pressure_drops.append(dp)

    return {
        "TFA_in2": tfa_in2,
        "flow_rates": base,
        "velocities": velocities,
        "pressure_drops": pressure_drops,
    }
