"""Screen how important the 1.5-mm printed foot compliance could be."""
from __future__ import annotations
from math import degrees
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model.foot_compliance import FootArcSection
from model.rocker_geometry import RockerGeometry

MASS_KG = 0.1997
G = 9.80665


def main() -> None:
    sec = FootArcSection()
    geom = RockerGeometry()
    total_n = MASS_KG * G
    k_crit = sec.symmetric_upright_stability_stiffness_n_per_m(
        MASS_KG, geom.cg_height_upright_m, G
    )
    k_sag = (total_n / 2.0) / geom.center_missing_sagitta_m

    print("STEP geometry used only as geometry")
    print(f"radial thickness = {sec.radial_thickness_m*1e3:.3f} mm")
    print(f"arc width Y      = {sec.arc_width_y_m*1e3:.3f} mm")
    print(f"free span arc    = {sec.free_span_arc_m*1e3:.3f} mm")
    print(f"rigid gap sagitta= {geom.center_missing_sagitta_m*1e3:.5f} mm")
    print(f"screening k_crit = {k_crit:.0f} N/m")
    print(f"k for half-load deflection = sagitta: {k_sag:.0f} N/m")
    print()
    print(
        "E[GPa]  k[N/m]  half-load defl[mm]  full-load defl[mm]  "
        "dual-support screen[deg]"
    )
    for e_gpa in (1.0, 1.5, 2.0, 2.5, 3.0):
        k = sec.cantilever_tip_stiffness_n_per_m(e_gpa * 1e9)
        d_half = sec.tip_deflection_m(total_n / 2.0, k)
        d_full = sec.tip_deflection_m(total_n, k)
        th = sec.symmetric_double_support_limit_rad(total_n, k)
        print(
            f"{e_gpa:5.1f} {k:8.0f} {d_half*1e3:19.3f} "
            f"{d_full*1e3:19.3f} {degrees(th):24.2f}"
        )

    print("\nFrequency screen (density is sensitivity only, not CAD mass):")
    for e_gpa in (1.0, 2.0, 3.0):
        f = sec.first_cantilever_frequency_hz(e_gpa * 1e9, 1200.0)
        print(f"E={e_gpa:.1f} GPa, rho=1200 kg/m^3 -> f1~{f:.0f} Hz")


if __name__ == "__main__":
    main()
