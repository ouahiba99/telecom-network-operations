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

    UNIQUE (radio, mcc, mnc, area, cell_id)
);

CREATE INDEX IF NOT EXISTS idx_cells_coordinates
    ON cells (latitude, longitude);

CREATE INDEX IF NOT EXISTS idx_cells_radio
    ON cells (radio);

CREATE INDEX IF NOT EXISTS idx_cells_mcc_mnc
    ON cells (mcc, mnc);
