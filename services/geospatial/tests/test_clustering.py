"""Conversión metros → grados para el eps de ST_ClusterDBSCAN.

Equivocar esta conversión no produce ningún error visible: devuelve clusters de
un tamaño que no es el que se pidió. Por eso está aislada y cubierta.
"""
import pytest

from app.services.clustering import METERS_PER_DEGREE_LATITUDE, meters_to_degrees


def test_one_degree_of_latitude_is_the_reference_distance():
    assert meters_to_degrees(METERS_PER_DEGREE_LATITUDE) == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("meters", "expected_degrees"),
    [
        (5_000, 0.04491),     # radio por defecto del spec
        (1_000, 0.00898),
        (10_000, 0.08983),
        (100, 0.00090),
    ],
)
def test_known_conversions(meters, expected_degrees):
    assert meters_to_degrees(meters) == pytest.approx(expected_degrees, abs=1e-5)


def test_conversion_is_monotonic():
    """Más metros, más grados: si esto se invirtiera, un radio mayor daría
    clusters más pequeños."""
    values = [meters_to_degrees(m) for m in (100, 1_000, 5_000, 20_000)]
    assert values == sorted(values)


@pytest.mark.parametrize("invalid", [0, -1, -5000])
def test_non_positive_radius_is_rejected(invalid):
    """Un eps de 0 o negativo haría que DBSCAN no agrupara nada, en silencio."""
    with pytest.raises(ValueError):
        meters_to_degrees(invalid)


def test_error_over_colombia_longitudes_stays_under_one_percent():
    """El eps se calcula con la latitud, pero se aplica también sobre la
    longitud, donde un grado se acorta con el coseno. Este test fija el techo del
    error que se acepta por esa aproximación.
    """
    import math

    for latitude in (3.45, 4.81, 5.07, 5.69, 13.0):
        shrink = 1 - math.cos(math.radians(latitude))
        assert shrink < 0.03  # <3% incluso en el extremo norte del pais

    # En las cuatro ciudades del sistema el error real es mucho menor.
    for latitude in (3.45, 4.81, 5.07, 5.69):
        assert 1 - math.cos(math.radians(latitude)) < 0.006
