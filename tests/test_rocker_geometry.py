from math import degrees, radians

from model.rocker_geometry import RockerGeometry


def test_step_contact_boundaries() -> None:
    geom = RockerGeometry()
    assert abs(degrees(geom.theta_inner_rad) - 1.910213) < 1e-6
    assert abs(degrees(geom.theta_outer_rad) - 17.457603) < 1e-6


def test_contact_mode_regions() -> None:
    geom = RockerGeometry()
    assert geom.contact_mode(0.0) == "double_inner_edge"
    assert geom.contact_mode(radians(1.0)) == "single_inner_edge_pivot"
    assert geom.contact_mode(radians(5.0)) == "circular_arc"
    assert geom.contact_mode(radians(18.0)) == "outer_edge_or_outside_cad_arc"


def test_piecewise_height_is_continuous_at_inner_transition() -> None:
    geom = RockerGeometry()
    eps = 1e-9
    left = geom.delta_height_m(geom.theta_inner_rad - eps)
    right = geom.delta_height_m(geom.theta_inner_rad + eps)
    assert abs(left - right) < 1e-9


def test_real_geometry_energy_is_materially_higher_near_fixed_q_gate() -> None:
    geom = RockerGeometry()
    theta = radians(6.5)
    mass_kg = 0.1997
    u_a = geom.complete_circle_potential_delta_j(theta, mass_kg)
    u_b = geom.potential_delta_j(theta, mass_kg)
    ratio = u_b / u_a
    assert 1.40 < ratio < 1.45
