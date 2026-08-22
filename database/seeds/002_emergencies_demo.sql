-- 002_emergencies_demo.sql
-- 21 emergencias de demo. Las 9 primeras estan concentradas en un radio de ~800 m
-- alrededor de (3.4520, -76.5310) en Cali para que ST_ClusterDBSCAN produzca un
-- hotspot visible; una de ellas esta CANCELLED a proposito, porque los hotspots
-- solo cuentan emergencias activas (el cluster debe dar 8, no 9).
--
-- Las prioridades estan calculadas a mano con las reglas de triage de la §4 del
-- spec: si cambian esas reglas, estos valores deben revisarse.
-- `location` la calcula el trigger emergencies_sync_location.

INSERT INTO intake.emergencies (id, type, priority, city, status, latitude, longitude, details, created_at) VALUES
    -- ── Cluster de Cali (hotspot de la demo) ──────────────────────────────────
    ('e0000000-0000-4000-8000-000000000001', 'RESCUE',            'P1', 'CALI', 'ASSIGNED',    3.4521, -76.5312,
     '{"injured": 3, "trapped": 1, "fire": false, "gasLeak": false}',                                              now() - interval '95 minutes'),
    ('e0000000-0000-4000-8000-000000000002', 'RESCUE',            'P1', 'CALI', 'IN_PROGRESS', 3.4535, -76.5298,
     '{"injured": 0, "trapped": 0, "fire": true, "gasLeak": false}',                                               now() - interval '88 minutes'),
    ('e0000000-0000-4000-8000-000000000003', 'STRUCTURAL_DAMAGE', 'P2', 'CALI', 'TRIAGED',     3.4508, -76.5325,
     '{"buildingType": "RESIDENTIAL", "crackLevel": "HIGH", "collapseRisk": true}',                                now() - interval '76 minutes'),
    ('e0000000-0000-4000-8000-000000000004', 'SHELTER',           'P1', 'CALI', 'TRIAGED',     3.4544, -76.5330,
     '{"adults": 2, "children": 2, "elderly": 2, "accessibilityRequired": false, "houseHabitable": false}',        now() - interval '64 minutes'),
    ('e0000000-0000-4000-8000-000000000005', 'SUPPLIES',          'P2', 'CALI', 'RECEIVED',    3.4497, -76.5289,
     '{"categories": ["WATER", "FOOD"], "people": 12}',                                                            now() - interval '51 minutes'),
    ('e0000000-0000-4000-8000-000000000006', 'RESCUE',            'P2', 'CALI', 'RECEIVED',    3.4529, -76.5345,
     '{"injured": 0, "trapped": 0, "fire": false, "gasLeak": false}',                                              now() - interval '43 minutes'),
    ('e0000000-0000-4000-8000-000000000007', 'STRUCTURAL_DAMAGE', 'P3', 'CALI', 'TRIAGED',     3.4552, -76.5307,
     '{"buildingType": "COMMERCIAL", "crackLevel": "HIGH", "collapseRisk": false}',                                now() - interval '35 minutes'),
    ('e0000000-0000-4000-8000-000000000008', 'SUPPLIES',          'P2', 'CALI', 'ASSIGNED',    3.4490, -76.5316,
     '{"categories": ["FOOD"], "people": 25}',                                                                     now() - interval '22 minutes'),
    ('e0000000-0000-4000-8000-000000000009', 'RESCUE',            'P1', 'CALI', 'CANCELLED',   3.4515, -76.5300,
     '{"injured": 1, "trapped": 0, "fire": false, "gasLeak": false}',                                              now() - interval '110 minutes'),

    -- ── Cali, fuera del cluster ───────────────────────────────────────────────
    ('e0000000-0000-4000-8000-000000000010', 'SHELTER',           'P2', 'CALI', 'RECEIVED',    3.3980, -76.5450,
     '{"adults": 1, "children": 0, "elderly": 0, "accessibilityRequired": false, "houseHabitable": true}',         now() - interval '30 minutes'),
    ('e0000000-0000-4000-8000-000000000011', 'STRUCTURAL_DAMAGE', 'P4', 'CALI', 'RESOLVED',    3.4890, -76.4880,
     '{"buildingType": "RESIDENTIAL", "crackLevel": "LOW", "collapseRisk": false}',                                now() - interval '180 minutes'),

    -- ── Pereira ───────────────────────────────────────────────────────────────
    ('e0000000-0000-4000-8000-000000000012', 'RESCUE',            'P1', 'PEREIRA', 'ASSIGNED',    4.8100, -75.6930,
     '{"injured": 2, "trapped": 0, "fire": false, "gasLeak": false}',                                              now() - interval '70 minutes'),
    ('e0000000-0000-4000-8000-000000000013', 'SHELTER',           'P1', 'PEREIRA', 'TRIAGED',     4.8210, -75.6975,
     '{"adults": 2, "children": 1, "elderly": 0, "accessibilityRequired": true, "houseHabitable": true}',          now() - interval '58 minutes'),
    ('e0000000-0000-4000-8000-000000000014', 'SUPPLIES',          'P3', 'PEREIRA', 'RECEIVED',    4.8035, -75.6880,
     '{"categories": ["MEDICINE"], "people": 8}',                                                                  now() - interval '26 minutes'),
    ('e0000000-0000-4000-8000-000000000015', 'STRUCTURAL_DAMAGE', 'P2', 'PEREIRA', 'IN_PROGRESS', 4.8290, -75.7020,
     '{"buildingType": "SCHOOL", "crackLevel": "MEDIUM", "collapseRisk": true}',                                   now() - interval '15 minutes'),

    -- ── Choco (Quibdo) ────────────────────────────────────────────────────────
    ('e0000000-0000-4000-8000-000000000016', 'RESCUE',            'P1', 'CHOCO', 'TRIAGED',  5.6930, -76.6600,
     '{"injured": 0, "trapped": 2, "fire": false, "gasLeak": false}',                                              now() - interval '82 minutes'),
    ('e0000000-0000-4000-8000-000000000017', 'SUPPLIES',          'P2', 'CHOCO', 'RECEIVED', 5.6875, -76.6540,
     '{"categories": ["WATER", "HYGIENE"], "people": 40}',                                                         now() - interval '47 minutes'),
    ('e0000000-0000-4000-8000-000000000018', 'SHELTER',           'P1', 'CHOCO', 'ASSIGNED', 5.7010, -76.6670,
     '{"adults": 3, "children": 2, "elderly": 1, "accessibilityRequired": false, "houseHabitable": false}',        now() - interval '19 minutes'),

    -- ── Manizales ─────────────────────────────────────────────────────────────
    ('e0000000-0000-4000-8000-000000000019', 'STRUCTURAL_DAMAGE', 'P4', 'MANIZALES', 'RECEIVED', 5.0680, -75.5100,
     '{"buildingType": "RESIDENTIAL", "crackLevel": "LOW", "collapseRisk": false}',                                now() - interval '61 minutes'),
    ('e0000000-0000-4000-8000-000000000020', 'RESCUE',            'P1', 'MANIZALES', 'TRIAGED',  5.0740, -75.5190,
     '{"injured": 1, "trapped": 0, "fire": false, "gasLeak": true}',                                               now() - interval '38 minutes'),
    ('e0000000-0000-4000-8000-000000000021', 'SUPPLIES',          'P3', 'MANIZALES', 'RECEIVED', 5.0600, -75.5240,
     '{"categories": ["FOOD"], "people": 5}',                                                                      now() - interval '9 minutes')
ON CONFLICT (id) DO NOTHING;
