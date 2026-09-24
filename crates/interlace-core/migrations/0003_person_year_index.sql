-- Additive year index. schema_epoch stays 1.
CREATE TABLE person_year_index (
    person_id INTEGER NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    include_groups INTEGER NOT NULL CHECK (include_groups IN (0, 1)),
    year INTEGER NOT NULL,
    message_count INTEGER NOT NULL CHECK (message_count > 0),
    first_local_day TEXT NOT NULL,
    PRIMARY KEY (person_id, include_groups, year)
);
