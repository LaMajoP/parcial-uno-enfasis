-- 001_resources.sql
-- 5 recursos por ciudad (uno de cada tipo), con coordenadas reales dispersas.
-- `location` la calcula el trigger resources_sync_location: no se inserta aqui.
-- Idempotente por UUID fijo + ON CONFLICT DO NOTHING.

INSERT INTO dispatch.resources (id, name, type, city, status, latitude, longitude) VALUES
    -- CHOCO (Quibdo)
    ('a0000000-0000-4000-8000-000000000001', 'Ambulancia Chocó 01',         'AMBULANCE',        'CHOCO',     'AVAILABLE', 5.6890, -76.6570),
    ('a0000000-0000-4000-8000-000000000002', 'Bomberos Chocó 01',           'FIRE_BRIGADE',     'CHOCO',     'AVAILABLE', 5.7020, -76.6685),
    ('a0000000-0000-4000-8000-000000000003', 'Rescate Chocó 01',            'RESCUE_TEAM',      'CHOCO',     'AVAILABLE', 5.6805, -76.6520),
    ('a0000000-0000-4000-8000-000000000004', 'Defensa Civil Chocó 01',      'CIVIL_DEFENSE',    'CHOCO',     'AVAILABLE', 5.7105, -76.6740),
    ('a0000000-0000-4000-8000-000000000005', 'Equipo Humanitario Chocó 01', 'HUMANITARIAN_TEAM','CHOCO',     'AVAILABLE', 5.6960, -76.6465),

    -- PEREIRA
    ('b0000000-0000-4000-8000-000000000001', 'Ambulancia Pereira 01',         'AMBULANCE',        'PEREIRA',   'AVAILABLE', 4.8087, -75.6906),
    ('b0000000-0000-4000-8000-000000000002', 'Bomberos Pereira 01',           'FIRE_BRIGADE',     'PEREIRA',   'AVAILABLE', 4.8255, -75.7015),
    ('b0000000-0000-4000-8000-000000000003', 'Rescate Pereira 01',            'RESCUE_TEAM',      'PEREIRA',   'AVAILABLE', 4.7980, -75.6820),
    ('b0000000-0000-4000-8000-000000000004', 'Defensa Civil Pereira 01',      'CIVIL_DEFENSE',    'PEREIRA',   'AVAILABLE', 4.8320, -75.6790),
    ('b0000000-0000-4000-8000-000000000005', 'Equipo Humanitario Pereira 01', 'HUMANITARIAN_TEAM','PEREIRA',   'AVAILABLE', 4.7895, -75.7100),

    -- CALI
    ('c0000000-0000-4000-8000-000000000001', 'Ambulancia Cali 01',         'AMBULANCE',        'CALI',      'AVAILABLE', 3.4372, -76.5225),
    ('c0000000-0000-4000-8000-000000000002', 'Bomberos Cali 01',           'FIRE_BRIGADE',     'CALI',      'AVAILABLE', 3.4680, -76.5180),
    ('c0000000-0000-4000-8000-000000000003', 'Rescate Cali 01',            'RESCUE_TEAM',      'CALI',      'AVAILABLE', 3.4210, -76.5410),
    ('c0000000-0000-4000-8000-000000000004', 'Defensa Civil Cali 01',      'CIVIL_DEFENSE',    'CALI',      'AVAILABLE', 3.4795, -76.5045),
    ('c0000000-0000-4000-8000-000000000005', 'Equipo Humanitario Cali 01', 'HUMANITARIAN_TEAM','CALI',      'AVAILABLE', 3.4055, -76.5480),

    -- MANIZALES
    ('d0000000-0000-4000-8000-000000000001', 'Ambulancia Manizales 01',         'AMBULANCE',        'MANIZALES', 'AVAILABLE', 5.0655, -75.5075),
    ('d0000000-0000-4000-8000-000000000002', 'Bomberos Manizales 01',           'FIRE_BRIGADE',     'MANIZALES', 'AVAILABLE', 5.0790, -75.5215),
    ('d0000000-0000-4000-8000-000000000003', 'Rescate Manizales 01',            'RESCUE_TEAM',      'MANIZALES', 'AVAILABLE', 5.0570, -75.4980),
    ('d0000000-0000-4000-8000-000000000004', 'Defensa Civil Manizales 01',      'CIVIL_DEFENSE',    'MANIZALES', 'AVAILABLE', 5.0845, -75.5320),
    ('d0000000-0000-4000-8000-000000000005', 'Equipo Humanitario Manizales 01', 'HUMANITARIAN_TEAM','MANIZALES', 'AVAILABLE', 5.0620, -75.5260)
ON CONFLICT (id) DO NOTHING;
