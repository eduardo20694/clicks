import os
import psycopg2

# URL do banco Railway
DATABASE_URL = os.getenv("DATABASE_URL") or \
    "postgresql://postgres:jghiePewYfPTZltWEEWnVhySPcMxwKkh@tramway.proxy.rlwy.net:14408/railway"

# Conecta ao banco
conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cursor = conn.cursor()

# Criação das tabelas
tables = [
    """
    CREATE TABLE IF NOT EXISTS sites (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        url VARCHAR(255) NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS clicks (
        id SERIAL PRIMARY KEY,
        site_id INT REFERENCES sites(id),
        ip VARCHAR(50),
        city VARCHAR(100),
        region VARCHAR(100),
        country VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
]

for table_sql in tables:
    cursor.execute(table_sql)
    print("Tabela criada ou já existe!")

conn.commit()
cursor.close()
conn.close()
print("Banco inicializado com sucesso!")
