CREATE TABLE IF NOT EXISTS heroes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    win_rate FLOAT NOT NULL,
    best_aspect TEXT NOT NULL,
    best_aspect_win_rate double precision,
    best_aspect_pick_rate double precision,
    strong_against TEXT NOT NULL,
    weak_against TEXT NOT NULL
);
