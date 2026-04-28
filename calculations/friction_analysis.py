import math
import numpy as np


def friction_analysis(
    tubing_type,                # "CT", "Tubing", "Drill Pipe", "Casing"
    inner_diameter_in,          # inches (calculated from tables)
    target_depth_m,             # meters
    total_ct_length_m,          # meters (only relevant if CT)
    density_ppg,
    viscosity_cp,               # USER INPUT in cP
    max_flow_bpm,
    step=0.5
):
    """
    Replicates Excel Friction Pdrop sheet.
    Returns ONLY total friction pressure drop (psi).
    """

    # -------------------------
    # Constants (Excel-equivalent)
    # -------------------------
    roughness_in = 0.00015
    g_c = 32.174
    viscosity_lbm_ft_s = viscosity_cp * 0.000672  # Excel conversion

    ID_ft = inner_diameter_in / 12.0
    area = math.pi * (ID_ft ** 2) / 4.0
    rho = density_ppg * 7.48052  # lbm/ft3

    # Lengths
    target_depth_ft = target_depth_m * 3.28084

    if tubing_type == "CT":
        if total_ct_length_m < target_depth_m:
            raise ValueError(
                "Target depth exceeds total CT length. Please check CT length."
            )
        surface_length_ft = (total_ct_length_m - target_depth_m) * 3.28084
    else:
        surface_length_ft = 0.0

    # -------------------------
    # Flow table (LET logic)
    # -------------------------
    flow_rates = np.arange(0, max_flow_bpm, step)
    if len(flow_rates) == 0 or flow_rates[-1] != max_flow_bpm:
        flow_rates = np.append(flow_rates, max_flow_bpm)

    dp_total = []

    for Q in flow_rates:
        if Q == 0:
            dp_total.append(0.0)
            continue

        Q_ft3_s = (Q * 5.614583) / 60.0
        velocity = Q_ft3_s / area

        Re = rho * velocity * ID_ft / viscosity_lbm_ft_s

        # Friction factor
        if Re < 2100:
            f = 64 / Re
        else:
            f = 0.25 / (
                math.log10(
                    (roughness_in / (3.7 * inner_diameter_in)) +
                    (5.74 / (Re ** 0.9))
                ) ** 2
            )

        # Downhole pressure loss
        dp_down = (
            (1 / 144) *
            f *
            (target_depth_ft / ID_ft) *
            rho *
            (velocity ** 2) /
            (2 * g_c)
        )

        # Surface pressure loss (CT only)
        if tubing_type == "CT" and surface_length_ft > 0:
            De_raw = Re * math.sqrt(ID_ft / (2 * 5.74))
            De_cap = min(De_raw, (0.15 / 0.033) ** 2)
            F_coil = 1 + 0.033 * math.sqrt(De_cap)

            dp_surface = (
                (1 / 144) *
                f *
                (surface_length_ft / ID_ft) *
                rho *
                (velocity ** 2) /
                (2 * g_c) *
                F_coil
            )
        else:
            dp_surface = 0.0

        dp_total.append(dp_down + dp_surface)

    return {
        "flow_rates": flow_rates,
        "dp_total": dp_total
    }
