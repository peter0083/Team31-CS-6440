-- init-ms3-db.sql - Fixed with AGE column

CREATE TABLE IF NOT EXISTS patient (
    id UUID PRIMARY KEY,
    birth_date DATE,
    age INT,
    gender VARCHAR(50),
    race VARCHAR(100),
    ethnicity VARCHAR(100),
    marital_status VARCHAR(100),
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS condition (
    id UUID PRIMARY KEY,
    subject_id UUID,
    code VARCHAR(50),
    code_system VARCHAR(100),
    description VARCHAR(500),
    onset_date_time TIMESTAMP,
    clinical_status VARCHAR(50),
    FOREIGN KEY (subject_id) REFERENCES patient(id)
);

CREATE TABLE IF NOT EXISTS observation (
    id UUID PRIMARY KEY,
    subject_id UUID,
    code VARCHAR(50),
    code_system VARCHAR(100),
    display VARCHAR(500),
    value_quantity_value FLOAT,
    value_quantity_unit VARCHAR(50),
    effective_date_time TIMESTAMP,
    reference_range_text VARCHAR(200),
    status VARCHAR(50),
    FOREIGN KEY (subject_id) REFERENCES patient(id)
);

CREATE TABLE IF NOT EXISTS medicationrequest (
    id UUID PRIMARY KEY,
    subject_id UUID,
    medication_text VARCHAR(500),
    generic_name VARCHAR(500),
    dose_text VARCHAR(200),
    frequency_text VARCHAR(200),
    authored_on TIMESTAMP,
    status VARCHAR(50),
    FOREIGN KEY (subject_id) REFERENCES patient(id)
);

CREATE INDEX IF NOT EXISTS idx_patient_id ON patient(id);
CREATE INDEX IF NOT EXISTS idx_condition_subject ON condition(subject_id);
CREATE INDEX IF NOT EXISTS idx_observation_subject ON observation(subject_id);
CREATE INDEX IF NOT EXISTS idx_medication_subject ON medicationrequest(subject_id);
