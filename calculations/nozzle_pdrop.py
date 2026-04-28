import math


def calculate_nozzle_pdrop(
    flow_rate_bpm,
    density_ppg,
    discharge_coefficient,
    nozzle_configs
):
    """
    Exact replication of Excel nozzle pressure drop formula

    Excel formula:
    ΔP = ((ρ*7.48052)/(2*g_c)) *
         ((Q*0.093576)/(Cd*(TFA/144)))^2 / 144
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
        return 0.0

    # ─────────────────────────
    # Constants
    # ─────────────────────────
    g_c = 32.174

    # Density: ppg → lb/ft³
    density_lb_ft3 = density_ppg * 7.48052

    # Flow rate: bpm → ft³/s
    flow_ft3_s = flow_rate_bpm * 0.093576

    # Area: in² → ft²
    area_ft2 = tfa_in2 / 144.0

    # ─────────────────────────
    # Excel equation
    # ─────────────────────────
    delta_p = (
        (density_lb_ft3 / (2 * g_c))
        * ((flow_ft3_s / (discharge_coefficient * area_ft2)) ** 2)
        / 144.0
    )

    return delta_p