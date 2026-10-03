CREATE TABLE IF NOT EXISTS cells (
    id BIGSERIAL PRIMARY KEY,

    radio VARCHAR(10) NOT NULL,
    mcc INTEGER NOT NULL,
    mnc INTEGER,
    area INTEGER,
    cell_id BIGINT NOT NULL,
    unit INTEGER,

    longitude DOUBLE PRECISION,
    latitude DOUBLE PRECISION,
    range_m INTEGER,

    samples INTEGER,
    changeable BOOLEAN,

    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,

    average_signal INTEGER,

    -- Geographic enrichment
    wilaya_code INTEGER,
    wilaya_name VARCHAR(100),
    wilaya_name_fr VARCHAR(100),
    geo_match_status VARCHAR(30),
    geo_source VARCHAR(100),

    UNIQUE (radio, mcc, mnc, area, cell_id)
);


CREATE INDEX IF NOT EXISTS idx_cells_coordinates
    ON cells (latitude, longitude);

CREATE INDEX IF NOT EXISTS idx_cells_radio
    ON cells (radio);

CREATE INDEX IF NOT EXISTS idx_cells_mcc_mnc
    ON cells (mcc, mnc);

CREATE INDEX IF NOT EXISTS idx_cells_wilaya
    ON cells (wilaya_code);

CREATE INDEX IF NOT EXISTS idx_cells_wilaya_name
    ON cells (wilaya_name);

CREATE INDEX IF NOT EXISTS idx_cells_geo_status
    ON cells (geo_match_status);


CREATE TABLE IF NOT EXISTS network_kpis (
    id BIGSERIAL PRIMARY KEY,

    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,

    cell_db_id BIGINT NOT NULL REFERENCES cells(id),
    radio VARCHAR(10) NOT NULL,
    mcc INTEGER NOT NULL,
    mnc INTEGER,
    area INTEGER,
    cell_id BIGINT NOT NULL,

    longitude DOUBLE PRECISION,
    latitude DOUBLE PRECISION,

    availability DOUBLE PRECISION NOT NULL,
    latency_ms DOUBLE PRECISION NOT NULL,
    packet_loss_pct DOUBLE PRECISION NOT NULL,
    throughput_mbps DOUBLE PRECISION NOT NULL,
    prb_utilization_pct DOUBLE PRECISION NOT NULL,
    rrc_success_rate DOUBLE PRECISION NOT NULL,
    handover_success_rate DOUBLE PRECISION NOT NULL,
    call_drop_rate DOUBLE PRECISION NOT NULL,
    active_users INTEGER NOT NULL,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


CREATE INDEX IF NOT EXISTS idx_network_kpis_timestamp
    ON network_kpis (timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_network_kpis_cell
    ON network_kpis (cell_db_id);

CREATE INDEX IF NOT EXISTS idx_network_kpis_cell_timestamp
    ON network_kpis (cell_db_id, timestamp DESC);


CREATE TABLE IF NOT EXISTS network_alarms (
    id BIGSERIAL PRIMARY KEY,

    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,

    cell_db_id BIGINT NOT NULL REFERENCES cells(id),
    radio VARCHAR(10) NOT NULL,
    mcc INTEGER NOT NULL,
    mnc INTEGER,
    area INTEGER,
    cell_id BIGINT NOT NULL,

    alarm_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL,

    metric VARCHAR(100),
    metric_value DOUBLE PRECISION,
    threshold_value DOUBLE PRECISION,

    message TEXT NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


CREATE INDEX IF NOT EXISTS idx_network_alarms_timestamp
    ON network_alarms (timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_network_alarms_cell
    ON network_alarms (cell_db_id);

CREATE INDEX IF NOT EXISTS idx_network_alarms_severity
    ON network_alarms (severity);

CREATE INDEX IF NOT EXISTS idx_network_alarms_status
    ON network_alarms (status);

CREATE INDEX IF NOT EXISTS idx_network_alarms_type
    ON network_alarms (alarm_type);
    