import os
import math

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from calculations.annular_velocity import annular_velocity_analysis
from calculations.settling_velocity import settling_velocity_analysis, SOLIDS_TABLE
from calculations.friction_analysis import friction_analysis
from calculations.nozzle_analysis import nozzle_analysis
from calculations.tubular_lookup import (
    CT_DF,
    TUBING_DF,
    DRILLPIPE_DF,
    CASING_DF,
    get_id,
)
from reports.pdf_report import generate_pdf_report


TUBULAR_TABLES = {
    "CT": CT_DF,
    "Tubing": TUBING_DF,
    "Drill Pipe": DRILLPIPE_DF,
    "Casing": CASING_DF,
}

M_PER_FT = 0.3048
MIN_ANNULAR_VELOCITY_FT_MIN = 120.0
CUSTOM_SOLID_OPTION = "Manual / Custom"


MODULE_DESCRIPTIONS = {
    "Annular Velocity": "Evaluates annular fluid velocity versus flow rate to support solids transport screening.",
    "Settling Velocity (Hole Cleaning)": "Estimates particle settling velocity and required annular velocity for effective hole cleaning.",
    "Friction Pressure Drop": "Estimates friction pressure losses through the selected tubular across a flow-rate range.",
    "Nozzle Pressure Drop": "Calculates nozzle pressure drop and exit velocity based on the selected nozzle configuration.",
}


def parse_od(od_value):
    """
    Convierte OD en string a float (in).
    Soporta:
    - 1.050
    - 1.050 Reg
    - 2-3/8
    - 3-1/2
    """

    if od_value is None:
        return None

    text = str(od_value).strip()

    # quitar etiquetas tipo "Reg"
    text = text.replace("Reg", "EUE").strip()

    # intento directo (caso decimal)
    try:
        return float(text)
    except:
        pass

    # caso fracción tipo 2-3/8
    if "-" in text:
        try:
            whole, frac = text.split("-")
            num, den = frac.split("/")
            return float(whole) + float(num) / float(den)
        except:
            return None

    return None


def fmt_int(val):
    try:
        return f"{int(round(float(val))):,}"
    except (ValueError, TypeError):
        return "-"


def fmt_flow(val):
    try:
        return f"{float(val):.1f}"
    except (ValueError, TypeError):
        return "-"


def fmt_value(value):
    if value is None or value == "":
        return "-"
    return value


def parse_positive_float(value):
    if value is None or str(value).strip() == "":
        return None

    try:
        parsed = float(str(value).strip().replace(",", "."))
    except ValueError:
        return None

    return parsed if parsed > 0 else None


def length_to_m(value, unit):
    if value is None:
        return None
    return float(value) * M_PER_FT if unit == "ft" else float(value)


def display_velocity_ft_min(value, unit):
    return float(value) * M_PER_FT if unit == "m" else float(value)


def display_velocity_ft_s(value, unit):
    return float(value) * M_PER_FT if unit == "m" else float(value)


def velocity_per_min_label(unit):
    return "m/min" if unit == "m" else "ft/min"


def velocity_per_s_label(unit):
    return "m/s" if unit == "m" else "ft/s"


def validate_required(values):
    missing = []
    for label, value in values.items():
        if value is None or value == "":
            missing.append(label)
    return missing


def ct_length_is_short(ct_length, target_depth):
    return (
        ct_length is not None
        and target_depth is not None
        and float(ct_length) < float(target_depth)
    )


def show_ct_length_warning(ct_length, target_depth, unit):
    if ct_length_is_short(ct_length, target_depth):
        st.error(
            f"Total CT Length ({ct_length:,.2f} {unit}) cannot be less than "
            f"Target Depth ({target_depth:,.2f} {unit})."
        )
        return True
    return False


def make_inputs_table(inputs_dict):
    return pd.DataFrame(
        {
            "Input": list(inputs_dict.keys()),
            "Value": [fmt_value(v) for v in inputs_dict.values()],
        }
    )


def pipe_selector(prefix):
    pipe_type = st.selectbox(
        f"{prefix} Type",
        ["CT", "Tubing", "Drill Pipe", "Casing"],
        index=None,
        key=f"{prefix}_type",
    )

    if not pipe_type:
        return None, None, None, None, None

    df = TUBULAR_TABLES[pipe_type]

    od = st.selectbox(
        f"{prefix} OD",
        df["OD"].unique(),
        index=None,
        key=f"{prefix}_od",
    )

    if od is None:
        return pipe_type, None, None, None, None

    wt_options = df[df["OD"] == od]["WT"].unique()

    wt = st.selectbox(
        f"{prefix} WT / Weight",
        wt_options,
        index=None,
        key=f"{prefix}_wt",
    )

    if wt is None:
        return pipe_type, od, None, None, None

    inner_id = get_id(df, od, wt)
    od_numeric = parse_od(od)
    
    if od_numeric is None:
        st.error(f"Invalid OD format: {od}")
        return pipe_type, od, wt, None, None

    return pipe_type, od, wt, od_numeric, inner_id


def save_chart(fig, filename):
    os.makedirs("reports", exist_ok=True)
    path = os.path.join("reports", filename)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return path


def store_payload(payload, well_name, target_depth, length_unit, calculation):
    st.session_state["last_payload"] = payload
    st.session_state["last_job_info"] = {
        "well_name": well_name,
        "target_depth": target_depth,
        "length_unit": length_unit,
        "calculation": calculation,
    }
    st.session_state["pdf_bytes"] = None


def make_pdf_download_button(calculation):
    payload = st.session_state.get("last_payload")
    job_info = st.session_state.get("last_job_info")

    if payload is None or job_info is None:
        return

    if job_info.get("calculation") != calculation:
        return

    if st.button("Prepare Technical Report"):
        pdf_path = "reports/Final_Report.pdf"

        generate_pdf_report(
            filename=pdf_path,
            job_info=job_info,
            table=payload["table"],
            chart=payload["chart"],
            warning=payload.get("warning"),
            solid_table=payload.get("solid_table"),
            inputs_table=payload.get("inputs_table"),
        )

        with open(pdf_path, "rb") as f:
            st.session_state["pdf_bytes"] = f.read()

        st.success("Technical report ready for download.")

    if st.session_state.get("pdf_bytes") is not None:
        st.download_button(
            label="Download Technical Report",
            data=st.session_state["pdf_bytes"],
            file_name="Tasman_Hydraulic_Report.pdf",
            mime="application/pdf",
        )


def render_ui():
    st.set_page_config(page_title="Tasman Hydraulic Simulator", layout="wide")
    os.makedirs("reports", exist_ok=True)

    if "last_payload" not in st.session_state:
        st.session_state["last_payload"] = None

    if "last_job_info" not in st.session_state:
        st.session_state["last_job_info"] = None

    if "pdf_bytes" not in st.session_state:
        st.session_state["pdf_bytes"] = None

    logo_path = os.path.join("assets", "tasman_logo.png")

    if os.path.exists(logo_path):
        st.image(logo_path, width=300)

    st.markdown(
        "<h2 style='color:#008FE3; margin-bottom:0;'>Hydraulic & Well Intervention Simulator</h2>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<p style='color:gray; margin-top:0;'>Tasman Oil Tools | Rentals - Services - Solutions</p>",
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns([2, 1, 1])
    well_name = c1.text_input("Well Name")
    length_unit = c2.selectbox("Length Unit", ["m", "ft"], index=0)
    target_depth = c3.number_input(
        f"Target Depth ({length_unit})",
        value=None,
        min_value=0.0,
    )
    target_depth_m = length_to_m(target_depth, length_unit)
    velocity_min_unit = velocity_per_min_label(length_unit)
    velocity_s_unit = velocity_per_s_label(length_unit)
    min_annular_velocity_display = display_velocity_ft_min(
        MIN_ANNULAR_VELOCITY_FT_MIN,
        length_unit,
    )

    st.markdown("---")

    st.markdown(
        "<h3 style='color:#F28C00; margin-bottom:0;'>Select Calculation</h3>",
        unsafe_allow_html=True,
    )
    st.caption("Select the hydraulic calculation module you want to run.")

    calculation = st.radio(
        label="Calculation module",
        options=[
            "Annular Velocity",
            "Settling Velocity (Hole Cleaning)",
            "Friction Pressure Drop",
            "Nozzle Pressure Drop",
        ],
        label_visibility="collapsed",
    )

    st.info(MODULE_DESCRIPTIONS[calculation])

    st.markdown("---")

    # =====================================================
    # 1. ANNULAR VELOCITY
    # =====================================================
    if calculation == "Annular Velocity":
        st.markdown("### Annular Velocity")

        p1, p2 = st.columns(2)

        with p1:
            pipe1_type, pipe1_od_label, pipe1_wt, pipe1_od, pipe1_id = pipe_selector("Pipe 1")

        with p2:
            pipe2_type, pipe2_od_label, pipe2_wt, pipe2_od, pipe2_id = pipe_selector("Pipe 2")

        max_flow = st.number_input("Max Flow Rate (bpm)", value=None, min_value=0.0)

        if st.button("Run Simulation"):
            missing = validate_required(
                {
                    "Pipe 1 OD": pipe1_od,
                    "Pipe 2 ID": pipe2_id,
                    "Max Flow Rate": max_flow,
                }
            )

            if missing:
                st.error("Missing inputs: " + ", ".join(missing))
            else:
                try:
                    ann = annular_velocity_analysis(pipe1_od, pipe2_id, max_flow)

                    results_df = pd.DataFrame(
                        {
                            "Flow Rate (bpm)": [fmt_flow(v) for v in ann["flow_rates"]],
                            f"Annular Velocity ({velocity_min_unit})": [
                                fmt_int(display_velocity_ft_min(v, length_unit))
                                for v in ann["ann_velocities"]
                            ],
                        }
                    )

                    st.dataframe(results_df, use_container_width=True)

                    fig, ax = plt.subplots(figsize=(8, 4.5))
                    ax.plot(
                        ann["flow_rates"],
                        [
                            display_velocity_ft_min(v, length_unit)
                            for v in ann["ann_velocities"]
                        ],
                        color="#008FE3",
                        linewidth=2.5,
                        label="Annular Velocity",
                    )
                    ax.axhline(
                        min_annular_velocity_display,
                        linestyle="--",
                        color="#F28C00",
                        linewidth=2.5,
                        label="Minimum Recommended Velocity",
                    )
                    ax.set_xlabel("Flow Rate (bpm)")
                    ax.set_ylabel(f"Annular Velocity ({velocity_min_unit})")
                    ax.grid(True)
                    ax.legend()

                    chart_path = save_chart(fig, "annular.png")
                    st.pyplot(fig)

                    warning = None
                    if max(ann["ann_velocities"]) < MIN_ANNULAR_VELOCITY_FT_MIN:
                        warning = (
                            f"Minimum annular velocity of {min_annular_velocity_display:.1f} "
                            f"{velocity_min_unit} was not reached. "
                            "Higher pump capacity may be required."
                        )
                        st.warning(warning)

                    inputs_table = make_inputs_table(
                        {
                            "Well Name": well_name,
                            f"Target Depth ({length_unit})": target_depth,
                            "Length Unit": length_unit,
                            "Calculation": calculation,
                            "Pipe 1 Type": pipe1_type,
                            "Pipe 1 OD": pipe1_od_label,
                            "Pipe 1 WT / Weight": pipe1_wt,
                            "Pipe 1 OD Numeric (in)": pipe1_od,
                            "Pipe 2 Type": pipe2_type,
                            "Pipe 2 OD": pipe2_od_label,
                            "Pipe 2 WT / Weight": pipe2_wt,
                            "Pipe 2 ID (in)": pipe2_id,
                            "Max Flow Rate (bpm)": max_flow,
                        }
                    )

                    payload = {
                        "table": results_df,
                        "chart": chart_path,
                        "warning": warning,
                        "solid_table": None,
                        "inputs_table": inputs_table,
                    }

                    store_payload(payload, well_name, target_depth, length_unit, calculation)

                except Exception as e:
                    st.error(f"Calculation error: {e}")

    # =====================================================
    # 2. SETTLING VELOCITY / HOLE CLEANING
    # =====================================================
        # =====================================================
    # 2. SETTLING VELOCITY / HOLE CLEANING
    # =====================================================
    elif calculation == "Settling Velocity (Hole Cleaning)":
        st.markdown("### Settling Velocity / Hole Cleaning")

        p1, p2 = st.columns(2)

        with p1:
            pipe1_type, pipe1_od_label, pipe1_wt, pipe1_od, pipe1_id = pipe_selector("Pipe 1")

        with p2:
            pipe2_type, pipe2_od_label, pipe2_wt, pipe2_od, pipe2_id = pipe_selector("Pipe 2")

        pipe1_total_length = None
        if pipe1_type == "CT":
            pipe1_total_length = st.number_input(
                f"Total CT Length ({length_unit})",
                value=None,
                min_value=0.0,
                help="Total CT length available on reel/string. Used to estimate friction pressure drop through the smaller pipe."
            )
        else:
            pipe1_total_length = target_depth
        pipe1_total_length_m = length_to_m(pipe1_total_length, length_unit)
        pipe1_ct_length_short = pipe1_type == "CT" and show_ct_length_warning(
            pipe1_total_length,
            target_depth,
            length_unit,
        )

        density = st.number_input("Fluid Density (ppg)", value=None, min_value=0.0)
        viscosity = st.number_input("Fluid Viscosity (cP)", value=None, min_value=0.0)
        deviation = st.number_input("Max Well Deviation (deg)", value=None, min_value=0.0)
        solid = st.selectbox(
            "Solid Type",
            list(SOLIDS_TABLE.keys()) + [CUSTOM_SOLID_OPTION],
            index=None,
        )

        custom_solid_name = None
        custom_particle_size_in = None
        custom_particle_density_gcc = None
        custom_solid_invalid = False

        if solid == CUSTOM_SOLID_OPTION:
            st.markdown("### Manual Solid Properties")
            s1, s2, s3 = st.columns(3)
            custom_solid_name = s1.text_input(
                "Solid Name",
                value="Custom Solid",
            )
            custom_particle_size_text = s2.text_input(
                "Particle Size (in)",
                value="",
                placeholder="Example: 0.1250",
            )
            custom_particle_density_text = s3.text_input(
                "Particle Density (g/cc)",
                value="",
                placeholder="Example: 7.000",
            )
            custom_particle_size_in = parse_positive_float(custom_particle_size_text)
            custom_particle_density_gcc = parse_positive_float(custom_particle_density_text)

            if custom_particle_size_text.strip() and custom_particle_size_in is None:
                custom_solid_invalid = True
                s2.error("Enter a positive particle size.")

            if custom_particle_density_text.strip() and custom_particle_density_gcc is None:
                custom_solid_invalid = True
                s3.error("Enter a positive particle density.")

        max_flow = st.number_input("Max Flow Rate (bpm)", value=None, min_value=0.0)

        pressure_limit = st.number_input(
            "Max Allowable Friction Pressure Drop (psi) - Optional",
            value=None,
            min_value=0.0,
            help="Optional limit to flag if friction pressure drop through the smaller pipe becomes excessive."
        )

        if st.button(
            "Run Simulation",
            disabled=pipe1_ct_length_short or custom_solid_invalid,
        ):
            missing = validate_required(
                {
                    "Target Depth": target_depth,
                    "Pipe 1 OD": pipe1_od,
                    "Pipe 1 ID": pipe1_id,
                    "Pipe 2 ID": pipe2_id,
                    "Pipe 1 Total Length": pipe1_total_length,
                    "Fluid Density": density,
                    "Fluid Viscosity": viscosity,
                    "Max Well Deviation": deviation,
                    "Solid Type": solid,
                    "Particle Size": custom_particle_size_in
                    if solid == CUSTOM_SOLID_OPTION
                    else 1,
                    "Particle Density": custom_particle_density_gcc
                    if solid == CUSTOM_SOLID_OPTION
                    else 1,
                    "Max Flow Rate": max_flow,
                }
            )

            if missing:
                st.error("Missing inputs: " + ", ".join(missing))
            else:
                try:
                    ann_area = math.pi * (pipe2_id**2 - pipe1_od**2) / 4.0

                    if ann_area <= 0:
                        raise ValueError(
                            "Invalid annular geometry. Pipe 2 ID must be greater than Pipe 1 OD."
                        )

                    selected_solid = (
                        custom_solid_name.strip() or "Custom Solid"
                        if solid == CUSTOM_SOLID_OPTION
                        else solid
                    )

                    settle = settling_velocity_analysis(
                        ann_area_in2=ann_area,
                        density_ppg=density,
                        viscosity_cp=viscosity,
                        max_flow_bpm=max_flow,
                        solid_type=selected_solid,
                        deviation_deg=deviation,
                        particle_size_in=custom_particle_size_in,
                        particle_density_gcc=custom_particle_density_gcc,
                    )

                    friction = friction_analysis(
                        tubing_type=pipe1_type,
                        inner_diameter_in=pipe1_id,
                        target_depth_m=target_depth_m,
                        total_ct_length_m=pipe1_total_length_m,
                        density_ppg=density,
                        viscosity_cp=viscosity,
                        max_flow_bpm=max_flow,
                    )

                    results_df = pd.DataFrame(
                        {
                            "Flow Rate (bpm)": [
                                fmt_flow(v) for v in settle["flow_rates"]
                            ],
                            f"Annular Velocity ({velocity_min_unit})": [
                                fmt_int(display_velocity_ft_min(v, length_unit))
                                for v in settle["ann_velocity"]
                            ],
                            f"Required Velocity ({velocity_min_unit})": [
                                fmt_int(display_velocity_ft_min(v, length_unit))
                                for v in settle["required_velocity"]
                            ],
                            "Friction ΔP - Pipe 1 (psi)": [
                                fmt_int(v) for v in friction["dp_total"]
                            ],
                        }
                    )

                    st.dataframe(results_df, use_container_width=True)

                    solid_props = settle["solid_properties"]
                    solid_table = pd.DataFrame(
                        {
                            "Property": [
                                "Solid Type",
                                "Particle Size (in)",
                                "Particle Density (g/cc)",
                            ],
                            "Value": [
                                solid_props["Solid Type"],
                                solid_props["Particle Size (in)"],
                                solid_props["Particle Density (g/cc)"],
                            ],
                        }
                    )

                    st.markdown("### Solid Properties")
                    st.dataframe(solid_table, use_container_width=True)

                    c1, c2, c3, c4 = st.columns(4)

                    c1.metric(
                        "Settling Velocity",
                        f"{display_velocity_ft_min(settle['settling_velocity'], length_unit):.0f} {velocity_min_unit}",
                    )
                    c2.metric("Target Ratio", f"{settle['ratio']:.1f}")
                    c3.metric(
                        "Required Velocity",
                        f"{display_velocity_ft_min(settle['req_velocity'], length_unit):.0f} {velocity_min_unit}",
                    )

                    if settle["min_rate"] is not None:
                        c4.metric(
                            "Minimum Required Rate",
                            f"{settle['min_rate']:.2f} bpm",
                        )
                    else:
                        c4.metric("Minimum Required Rate", "Not reached")

                    max_friction_dp = max(friction["dp_total"]) if friction["dp_total"] else 0

                    st.metric(
                        "Max Friction ΔP Through Pipe 1",
                        f"{max_friction_dp:,.0f} psi",
                    )

                    fig, ax = plt.subplots(figsize=(8, 4.5))

                    ax.plot(
                        settle["flow_rates"],
                        [
                            display_velocity_ft_min(v, length_unit)
                            for v in settle["ann_velocity"]
                        ],
                        color="#008FE3",
                        linewidth=2.5,
                        label="Annular Velocity",
                    )

                    ax.plot(
                        settle["flow_rates"],
                        [
                            display_velocity_ft_min(v, length_unit)
                            for v in settle["required_velocity"]
                        ],
                        linestyle="--",
                        color="#F28C00",
                        linewidth=2.5,
                        label="Required Velocity",
                    )

                    if settle["min_rate"] is not None:
                        ax.scatter(
                            settle["min_rate"],
                            display_velocity_ft_min(settle["req_velocity"], length_unit),
                            s=130,
                            color="#D62728",
                            edgecolor="black",
                            zorder=5,
                            label=f"Minimum Rate: {settle['min_rate']:.2f} bpm",
                        )

                    ax.set_xlabel("Flow Rate (bpm)")
                    ax.set_ylabel(f"Velocity ({velocity_min_unit})")
                    ax.grid(True)
                    ax.legend()

                    chart_path = save_chart(fig, "settling.png")
                    st.pyplot(fig)

                    st.markdown("### Friction Pressure Drop Through Pipe 1")

                    fig2, ax2 = plt.subplots(figsize=(8, 4.5))

                    ax2.plot(
                        friction["flow_rates"],
                        friction["dp_total"],
                        color="#6A3D9A",
                        linewidth=2.5,
                        label="Friction ΔP - Pipe 1",
                    )

                    if pressure_limit is not None:
                        ax2.axhline(
                            pressure_limit,
                            color="#D62728",
                            linestyle="--",
                            linewidth=2.5,
                            label=f"Pressure Limit: {pressure_limit:,.0f} psi",
                        )

                    ax2.set_xlabel("Flow Rate (bpm)")
                    ax2.set_ylabel("Pressure Drop (psi)")
                    ax2.grid(True)
                    ax2.legend()

                    friction_chart_path = save_chart(fig2, "settling_friction.png")
                    st.pyplot(fig2)

                    warnings = []

                    if settle["min_rate"] is None or max_flow < settle["min_rate"]:
                        warnings.append(
                            "Required annular velocity was not reached. Higher pump capacity may be required."
                        )

                    if pressure_limit is not None and max_friction_dp > pressure_limit:
                        warnings.append(
                            "Friction pressure drop through Pipe 1 exceeds the defined allowable limit. "
                            "The required flow rate may not be operationally feasible."
                        )

                    warning = " ".join(warnings) if warnings else None

                    if warning:
                        st.warning(warning)

                    inputs_table = make_inputs_table(
                        {
                            "Well Name": well_name,
                            f"Target Depth ({length_unit})": target_depth,
                            "Length Unit": length_unit,
                            "Calculation": calculation,
                            "Pipe 1 Type": pipe1_type,
                            "Pipe 1 OD": pipe1_od_label,
                            "Pipe 1 WT / Weight": pipe1_wt,
                            "Pipe 1 OD Numeric (in)": pipe1_od,
                            "Pipe 1 ID (in)": pipe1_id,
                            f"Pipe 1 Total Length ({length_unit})": pipe1_total_length,
                            "Pipe 2 Type": pipe2_type,
                            "Pipe 2 OD": pipe2_od_label,
                            "Pipe 2 WT / Weight": pipe2_wt,
                            "Pipe 2 ID (in)": pipe2_id,
                            "Annular Area (in²)": round(ann_area, 4),
                            "Fluid Density (ppg)": density,
                            "Fluid Viscosity (cP)": viscosity,
                            "Max Well Deviation (deg)": deviation,
                            "Solid Type": selected_solid,
                            "Particle Size (in)": solid_props["Particle Size (in)"],
                            "Particle Density (g/cc)": solid_props["Particle Density (g/cc)"],
                            "Max Flow Rate (bpm)": max_flow,
                            "Max Allowable Friction ΔP (psi)": pressure_limit,
                            "Max Calculated Friction ΔP (psi)": round(max_friction_dp, 0),
                        }
                    )

                    payload = {
                        "table": results_df,
                        "chart": chart_path,
                        "warning": warning,
                        "solid_table": solid_table,
                        "inputs_table": inputs_table,
                    }

                    store_payload(payload, well_name, target_depth, length_unit, calculation)

                except Exception as e:
                    st.error(f"Calculation error: {e}")

    # =====================================================
    # 3. FRICTION PRESSURE DROP
    # =====================================================
    elif calculation == "Friction Pressure Drop":
        st.markdown("### Friction Pressure Drop")

        pipe_type, pipe_od_label, pipe_wt, pipe_od, pipe_id = pipe_selector("Tubing")

        total_ct_length = None
        if pipe_type == "CT":
            total_ct_length = st.number_input(
                f"Total CT Length ({length_unit})",
                value=None,
                min_value=0.0,
            )
        else:
            total_ct_length = target_depth
        total_ct_length_m = length_to_m(total_ct_length, length_unit)
        ct_length_short = pipe_type == "CT" and show_ct_length_warning(
            total_ct_length,
            target_depth,
            length_unit,
        )

        density = st.number_input("Fluid Density (ppg)", value=None, min_value=0.0)
        viscosity = st.number_input("Fluid Viscosity (cP)", value=None, min_value=0.0)
        max_flow = st.number_input("Max Flow Rate (bpm)", value=None, min_value=0.0)

        if st.button("Run Simulation", disabled=ct_length_short):
            missing = validate_required(
                {
                    "Tubing Type": pipe_type,
                    "Tubing ID": pipe_id,
                    "Target Depth": target_depth,
                    "Total CT Length": total_ct_length,
                    "Fluid Density": density,
                    "Fluid Viscosity": viscosity,
                    "Max Flow Rate": max_flow,
                }
            )

            if missing:
                st.error("Missing inputs: " + ", ".join(missing))
            else:
                try:
                    fric = friction_analysis(
                        tubing_type=pipe_type,
                        inner_diameter_in=pipe_id,
                        target_depth_m=target_depth_m,
                        total_ct_length_m=total_ct_length_m,
                        density_ppg=density,
                        viscosity_cp=viscosity,
                        max_flow_bpm=max_flow,
                    )

                    results_df = pd.DataFrame(
                        {
                            "Flow Rate (bpm)": [
                                fmt_flow(v) for v in fric["flow_rates"]
                            ],
                            "Pressure Drop (psi)": [
                                fmt_int(v) for v in fric["dp_total"]
                            ],
                        }
                    )

                    st.dataframe(results_df, use_container_width=True)

                    fig, ax = plt.subplots(figsize=(8, 4.5))
                    ax.plot(
                        fric["flow_rates"],
                        fric["dp_total"],
                        color="#6A3D9A",
                        linewidth=2.5,
                        label="Total Friction Pressure Drop",
                    )
                    ax.set_xlabel("Flow Rate (bpm)")
                    ax.set_ylabel("Pressure Drop (psi)")
                    ax.grid(True)
                    ax.legend()

                    chart_path = save_chart(fig, "friction.png")
                    st.pyplot(fig)

                    inputs_table = make_inputs_table(
                        {
                            "Well Name": well_name,
                            f"Target Depth ({length_unit})": target_depth,
                            "Length Unit": length_unit,
                            "Calculation": calculation,
                            "Tubing Type": pipe_type,
                            "Tubing OD": pipe_od_label,
                            "Tubing WT / Weight": pipe_wt,
                            "Tubing ID (in)": pipe_id,
                            f"Total CT Length ({length_unit})": total_ct_length,
                            "Fluid Density (ppg)": density,
                            "Fluid Viscosity (cP)": viscosity,
                            "Max Flow Rate (bpm)": max_flow,
                        }
                    )

                    payload = {
                        "table": results_df,
                        "chart": chart_path,
                        "warning": None,
                        "solid_table": None,
                        "inputs_table": inputs_table,
                    }

                    store_payload(payload, well_name, target_depth, length_unit, calculation)

                except Exception as e:
                    st.error(f"Calculation error: {e}")

    # =====================================================
    # 4. NOZZLE PRESSURE DROP
    # =====================================================
    elif calculation == "Nozzle Pressure Drop":
        st.markdown("### Nozzle Pressure Drop")

        flow_rate = st.number_input("Max Flow Rate (bpm)", value=None, min_value=0.0)
        density = st.number_input("Fluid Density (ppg)", value=None, min_value=0.0)
        cd = st.number_input(
            "Discharge Coefficient (Cd)",
            value=None,
            min_value=0.0,
            max_value=1.5,
        )

        st.markdown("### Nozzle Configuration")

        n1, n2, n3 = st.columns(3)

        with n1:
            count_1 = st.number_input("Count 1", value=None, min_value=0)
            dia_1 = st.number_input(
                "Diameter 1 (in)",
                value=None,
                min_value=0.0,
                format="%.3f",
            )

        with n2:
            count_2 = st.number_input("Count 2", value=None, min_value=0)
            dia_2 = st.number_input(
                "Diameter 2 (in)",
                value=None,
                min_value=0.0,
                format="%.3f",
            )

        with n3:
            count_3 = st.number_input("Count 3", value=None, min_value=0)
            dia_3 = st.number_input(
                "Diameter 3 (in)",
                value=None,
                min_value=0.0,
                format="%.3f",
            )

        if st.button("Run Simulation"):
            missing = validate_required(
                {
                    "Max Flow Rate": flow_rate,
                    "Fluid Density": density,
                    "Discharge Coefficient": cd,
                }
            )

            if missing:
                st.error("Missing inputs: " + ", ".join(missing))
            else:
                nozzle_configs = [
                    {"count": count_1 or 0, "diameter": dia_1 or 0},
                    {"count": count_2 or 0, "diameter": dia_2 or 0},
                    {"count": count_3 or 0, "diameter": dia_3 or 0},
                ]

                try:
                    noz = nozzle_analysis(
                        flow_rate_bpm=flow_rate,
                        density_ppg=density,
                        discharge_coefficient=cd,
                        nozzle_configs=nozzle_configs,
                    )

                    if noz is None:
                        st.error("Invalid nozzle configuration. Total flow area is zero.")
                    else:
                        results_df = pd.DataFrame(
                            {
                                "Flow Rate (bpm)": [
                                    fmt_flow(v) for v in noz["flow_rates"]
                                ],
                                "Nozzle ΔP (psi)": [
                                    fmt_int(v) for v in noz["pressure_drops"]
                                ],
                                f"Exit Velocity ({velocity_s_unit})": [
                                    fmt_int(display_velocity_ft_s(v, length_unit))
                                    for v in noz["velocities"]
                                ],
                            }
                        )

                        st.metric("Total Flow Area", f"{noz['TFA_in2']:.4f} in²")
                        st.dataframe(results_df, use_container_width=True)

                        fig, ax = plt.subplots(figsize=(8, 4.5))
                        ax.plot(
                            noz["flow_rates"],
                            noz["pressure_drops"],
                            color="#D62728",
                            linewidth=2.5,
                            label="Nozzle Pressure Drop",
                        )
                        ax.set_xlabel("Flow Rate (bpm)")
                        ax.set_ylabel("Pressure Drop (psi)")
                        ax.grid(True)
                        ax.legend()

                        chart_path = save_chart(fig, "nozzle.png")
                        st.pyplot(fig)

                        inputs_table = make_inputs_table(
                            {
                                "Well Name": well_name,
                                f"Target Depth ({length_unit})": target_depth,
                                "Length Unit": length_unit,
                                "Calculation": calculation,
                                "Max Flow Rate (bpm)": flow_rate,
                                "Fluid Density (ppg)": density,
                                "Discharge Coefficient (Cd)": cd,
                                "Nozzle Count 1": count_1 or 0,
                                "Nozzle Diameter 1 (in)": dia_1 or 0,
                                "Nozzle Count 2": count_2 or 0,
                                "Nozzle Diameter 2 (in)": dia_2 or 0,
                                "Nozzle Count 3": count_3 or 0,
                                "Nozzle Diameter 3 (in)": dia_3 or 0,
                                "Total Flow Area (in²)": round(noz["TFA_in2"], 4),
                            }
                        )

                        payload = {
                            "table": results_df,
                            "chart": chart_path,
                            "warning": None,
                            "solid_table": None,
                            "inputs_table": inputs_table,
                        }

                        store_payload(payload, well_name, target_depth, length_unit, calculation)

                except Exception as e:
                    st.error(f"Calculation error: {e}")

    make_pdf_download_button(calculation)
