import math
import numpy as np


SOLIDS_TABLE = {
    "Steel debris": {"size_in": 0.1, "density_gcc": 7.85},
    "Iron debris": {"size_in": 0.1, "density_gcc": 5.00},
    "Sand 20/40": {"size_in": 0.0331, "density_gcc": 2.65},
    "Sand 40/70": {"size_in": 0.0138, "density_gcc": 2.65},
    "Sand 70/140": {"size_in": 0.0070, "density_gcc": 2.65},
    "Sand 100 mesh": {"size_in": 0.0058, "density_gcc": 2.65},
}


def ratio_from_deviation(dev):
    if dev < 20:
        return 1.5
    elif dev < 40:
        return 2.0
    elif dev < 60:
        return 2.5
    else:
        return 3.0


def settling_velocity_analysis(
    ann_area_in2,
    density_ppg,
    viscosity_cp,
    max_flow_bpm,
    solid_type,
    deviation_deg,
    step=0.5
):
    g = 32.174

    rho_f = density_ppg * 7.48052
    mu = viscosity_cp * 0.00067197

    solid = SOLIDS_TABLE[solid_type]
    d_ft = solid["size_in"] / 12.0
    rho_p = solid["density_gcc"] * 62.42796

    Vs0 = g * (rho_p - rho_f) * d_ft**2 / (18 * mu)
    Re = (rho_f * Vs0 * d_ft) / mu if mu > 0 else 0

    if Re < 1000 and Re > 0:
        Cd = (24 / Re) * (1 + 0.15 * Re**0.687)
    else:
        Cd = 0.44

    Vset = 60 * math.sqrt((4 * g * d_ft * (rho_p - rho_f)) / (3 * Cd * rho_f))

    ratio = ratio_from_deviation(deviation_deg)
    Vreq = ratio * Vset

    flow_rates = np.arange(0, max_flow_bpm, step)
    if len(flow_rates) == 0 or abs(flow_rates[-1] - max_flow_bpm) > 1e-6:
        flow_rates = np.append(flow_rates, max_flow_bpm)

    ann_velocity = [
        (Q * 5.6146) / (ann_area_in2 / 144.0) if Q > 0 else 0.0
        for Q in flow_rates
    ]

    required_velocity = [Vreq] * len(flow_rates)

    # Exact intersection, not next table value
    min_rate_exact = Vreq * (ann_area_in2 / 144.0) / 5.6146

    if min_rate_exact > max_flow_bpm:
        min_rate_exact = None

    return {
        "flow_rates": flow_rates,
        "ann_velocity": ann_velocity,
        "required_velocity": required_velocity,
        "settling_velocity": Vset,
        "ratio": ratio,
        "req_velocity": Vreq,
        "min_rate": min_rate_exact,
        "solid_properties": {
            "Solid Type": solid_type,
            "Particle Size (in)": solid["size_in"],
            "Particle Density (g/cc)": solid["density_gcc"],
        },
    }