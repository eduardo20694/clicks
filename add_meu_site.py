import os
import psycopg2

# URL do PostgreSQL do Railway
DATABASE_URL = os.getenv("DATABASE_URL") or \
    "postgresql://postgres:jghiePewYfPTZltWEEWnVhySPcMxwKkh@tramway.proxy.rlwy.net:14408/railway"

# Conecta ao banco
conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cursor = conn.cursor()

# Informações do seu site
site_name = "Renda Extra Drop"
site_url = "https://renda-extra-drop.onrender.com"

# Verifica se o site já existe
cursor.execute("SELECT id FROM sites WHERE url=%s", (site_url,))
res = cursor.fetchone()

if res:
    site_id = res[0]
    print(f"Site já está cadastrado! site_id = {site_id}")
else:
    # Adiciona site no banco
    cursor.execute(
        "INSERT INTO sites (name, url) VALUES (%s, %s) RETURNING id",
        (site_name, site_url)
    )
    site_id = cursor.fetchone()[0]
    conn.commit()
    print(f"Site adicionado com sucesso! site_id = {site_id}")

cursor.close()
conn.close()
