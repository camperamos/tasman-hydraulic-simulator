import numpy as np
import math


def annular_velocity_analysis(
    small_pipe_od_in,
    big_pipe_id_in,
    max_flow_bpm,
    step=0.5,
    min_ann_vel=120.0
):
    """
    Replicates Excel Annular Velocity sheet.
    Returns annular velocity vs flow rate.
    """

    # Annular area (in²)
    ann_area_in2 = math.pi * (big_pipe_id_in**2 - small_pipe_od_in**2) / 4.0

    if ann_area_in2 <= 0:
        raise ValueError("Invalid annular geometry: Big ID must be greater than small OD.")

    # Flow table (LET logic)
    flow_rates = np.arange(0, max_flow_bpm, step)
    if len(flow_rates) == 0 or flow_rates[-1] != max_flow_bpm:
        flow_rates = np.append(flow_rates, max_flow_bpm)

    ann_velocities = []

    for Q in flow_rates:
        if Q == 0:
            ann_velocities.append(0.0)
        else:
            ann_vel = (Q * 5.6146) / (ann_area_in2 / 144.0)
            ann_velocities.append(ann_vel)

    min_vel_line = [min_ann_vel] * len(flow_rates)

    return {
        "flow_rates": flow_rates,
        "ann_velocities": ann_velocities,
        "min_velocity": min_vel_line,
        "ann_area_in2": ann_area_in2,
    }
