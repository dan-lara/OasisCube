CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    photo_data BLOB,  -- Para armazenar a imagem original
    photo_mime_type TEXT,  -- Para armazenar o tipo de arquivo da imagem
    result TEXT,  -- JSON com os resultados da API
    project_id TEXT,  -- ID do projeto usado
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (username) REFERENCES users(username)
);

-- Índices para melhorar performance
CREATE INDEX idx_predictions_username ON predictions(username);
CREATE INDEX idx_predictions_created_at ON predictions(created_at);