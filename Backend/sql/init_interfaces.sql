DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'interface' AND column_name = 'bpd_u_guard'
    ) AND NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'interface' AND column_name = 'bpdu_guard'
    ) THEN
        EXECUTE 'ALTER TABLE interface RENAME COLUMN bpd_u_guard TO bpdu_guard';
    END IF;
END $$;

INSERT INTO interface (
    id_interface,
    nom,
    ip,
    vlan_id,
    equipement_id,
    status,
    mode,
    speed,
    allowed_vlans,
    port_security,
    max_mac,
    violation_mode,
    bpdu_guard,
    type
)
SELECT
    generated.id_interface,
    generated.nom,
    generated.ip,
    generated.vlan_id,
    generated.equipement_id,
    generated.status,
    generated.mode,
    generated.speed,
    generated.allowed_vlans,
    generated.port_security,
    generated.max_mac,
    generated.violation_mode,
    generated.bpdu_guard,
    generated.type
FROM (
    SELECT
        gs AS id_interface,
        'Gi1/0/' || gs AS nom,
        CASE WHEN gs = 4 THEN '192.168.1.10' ELSE NULL END::VARCHAR(15) AS ip,
        CASE
            WHEN gs = 3 THEN 20
            WHEN gs = 24 THEN 30
            WHEN gs <= 4 THEN 10
            ELSE 1
        END AS vlan_id,
        (SELECT id_eq FROM equipement ORDER BY id_eq ASC LIMIT 1) AS equipement_id,
        CASE WHEN gs <= 4 THEN 'UP' ELSE 'DOWN' END::VARCHAR(10) AS status,
        'Access'::VARCHAR(10) AS mode,
        CASE WHEN gs <= 4 THEN '1Gb' ELSE NULL END::VARCHAR(10) AS speed,
        NULL::VARCHAR AS allowed_vlans,
        CASE WHEN gs <= 3 THEN TRUE ELSE FALSE END AS port_security,
        1 AS max_mac,
        'shutdown'::VARCHAR AS violation_mode,
        TRUE AS bpdu_guard,
        'access'::VARCHAR(10) AS type
    FROM generate_series(1, 24) AS gs

    UNION ALL

    SELECT
        24 + gs AS id_interface,
        'Te1/1/' || gs AS nom,
        NULL::VARCHAR(15) AS ip,
        CASE WHEN gs <= 2 THEN NULL ELSE 1 END::INTEGER AS vlan_id,
        (SELECT id_eq FROM equipement ORDER BY id_eq ASC LIMIT 1) AS equipement_id,
        CASE WHEN gs = 1 THEN 'UP' ELSE 'DOWN' END::VARCHAR(10) AS status,
        CASE WHEN gs <= 2 THEN 'Trunk' ELSE 'Access' END::VARCHAR(10) AS mode,
        CASE WHEN gs = 1 THEN '10Gb' ELSE NULL END::VARCHAR(10) AS speed,
        CASE WHEN gs <= 2 THEN 'all' ELSE NULL END::VARCHAR AS allowed_vlans,
        FALSE AS port_security,
        1 AS max_mac,
        'shutdown'::VARCHAR AS violation_mode,
        FALSE AS bpdu_guard,
        'uplink'::VARCHAR(10) AS type
    FROM generate_series(1, 4) AS gs
) AS generated
WHERE NOT EXISTS (
    SELECT 1
    FROM interface existing
    WHERE existing.nom = generated.nom
);
