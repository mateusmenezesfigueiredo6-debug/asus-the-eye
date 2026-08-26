-- Captura de leads dos fronts Ledger e Markets.
-- Uma linha por envio; dedupe lógico fica na leitura (email+product).
CREATE TABLE IF NOT EXISTS leads (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL,
  product TEXT NOT NULL CHECK (product IN ('ledger', 'markets')),
  source TEXT NOT NULL DEFAULT 'unknown',
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_leads_email ON leads (email);
CREATE INDEX IF NOT EXISTS idx_leads_product ON leads (product, created_at);

-- Rate limit por IP: janela deslizante simples.
CREATE TABLE IF NOT EXISTS rate (
  ip TEXT NOT NULL,
  window_start TEXT NOT NULL,
  hits INTEGER NOT NULL DEFAULT 1,
  PRIMARY KEY (ip, window_start)
);
