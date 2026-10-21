CREATE TABLE IF NOT EXISTS eventos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT NOT NULL,
  tipo TEXT NOT NULL,          -- visita | clique
  quando TEXT NOT NULL DEFAULT (datetime('now', '-3 hours'))  -- horário de Brasília
);
CREATE INDEX IF NOT EXISTS ix_slug ON eventos(slug);
