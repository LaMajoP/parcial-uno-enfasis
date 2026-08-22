"""Conversión de radio en metros al `eps` que espera ST_ClusterDBSCAN.

`ST_ClusterDBSCAN` trabaja sobre *geometry*, no sobre *geography*, así que su
`eps` va en las unidades del SRID: grados, no metros. Esta es la única aritmética
del servicio y está aquí, aislada y con tests, porque equivocarla no rompe nada
de forma visible — simplemente devuelve clusters de un tamaño que no es el pedido.
"""

# Longitud de un grado de latitud, constante en toda la Tierra.
METERS_PER_DEGREE_LATITUDE = 111_320.0


def meters_to_degrees(meters: float) -> float:
    """Radio en metros → eps en grados.

    Se usa la equivalencia de la latitud, que es exacta. Sobre la longitud un
    grado se acorta con el coseno de la latitud, así que el eps queda algo
    generoso en el eje este-oeste; en Colombia (latitudes de 3° a 6°) ese exceso
    es inferior al 0,6 %, muy por debajo de la precisión con la que alguien
    escoge un radio de agrupación.
    """
    if meters <= 0:
        raise ValueError("El radio debe ser mayor que cero")
    return meters / METERS_PER_DEGREE_LATITUDE
