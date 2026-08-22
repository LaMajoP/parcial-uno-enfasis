/**
 * /health agregado (§7 del spec).
 *
 * Nginx por sí solo no sabe consultar cuatro upstreams y combinar sus
 * respuestas, así que esta parte va en njs: lanza las cuatro subpeticiones en
 * paralelo y devuelve un único JSON con el mismo envoltorio que usan los
 * servicios.
 */

const SERVICES = ['intake', 'dispatch', 'geospatial', 'notification'];

async function aggregate(r) {
    // En paralelo: en serie, cuatro servicios lentos sumarían sus tiempos.
    const responses = await Promise.all(
        SERVICES.map((name) => r.subrequest(`/_health/${name}`, { method: 'GET' }))
    );

    const services = {};
    let allUp = true;

    responses.forEach((response, index) => {
        const up = response.status === 200;
        if (!up) {
            allUp = false;
        }
        services[SERVICES[index]] = up ? 'up' : 'down';
    });

    r.headersOut['Content-Type'] = 'application/json';
    r.headersOut['Cache-Control'] = 'no-store';

    // Mismo criterio que el /health de cada servicio: 200 si todo está sano,
    // 503 si algo no lo está, y el detalle siempre dentro de `data`.
    r.return(
        allUp ? 200 : 503,
        JSON.stringify({
            success: true,
            data: {
                gateway: 'up',
                status: allUp ? 'ok' : 'degraded',
                services: services,
            },
        })
    );
}

export default { aggregate };
