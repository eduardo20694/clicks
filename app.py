import os
import psycopg2
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

# -------------------------------
# Configuração Flask
# -------------------------------
app = Flask(__name__)
CORS(app)

# -------------------------------
# Conexão com PostgreSQL (Railway)
# -------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:senha@localhost:5432/postgres")

def get_connection():
    """Cria e retorna uma nova conexão com o banco (melhor que usar global fixo)."""
    return psycopg2.connect(DATABASE_URL, sslmode="require")

# -------------------------------
# Função para geolocalização
# -------------------------------
def get_geo_info(ip):
    try:
        res = requests.get(f"https://ipapi.co/{ip}/json/", timeout=3)
        data = res.json()
        return data.get("city"), data.get("region"), data.get("country_name")
    except Exception as e:
        print(f"[GeoInfo Error] {e}")
        return None, None, None

# -------------------------------
# Endpoints
# -------------------------------

# Healthcheck (pra Railway saber se está ok)
@app.route("/")
def health():
    return jsonify({"status": "online", "message": "API de cliques rodando 🚀"})

# Adicionar novo site
@app.route("/api/sites", methods=["POST"])
def add_site():
    data = request.json
    if not data.get("name") or not data.get("url"):
        return jsonify({"error": "Campos 'name' e 'url' são obrigatórios"}), 400

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO sites (name, url) VALUES (%s, %s) RETURNING id",
        (data["name"], data["url"])
    )
    site_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"status": "ok", "site_id": site_id})

# Listar todos sites
@app.route("/api/sites", methods=["GET"])
def list_sites():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, url FROM sites")
    sites = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify([{"id": s[0], "name": s[1], "url": s[2]} for s in sites])

# Registrar clique
@app.route("/api/click", methods=["POST"])
def click():
    data = request.json
    site_id = data.get("site_id")
    if not site_id:
        return jsonify({"error": "site_id é obrigatório"}), 400

    ip = request.headers.get("X-Forwarded-For", request.remote_addr)  # pega IP real se estiver atrás de proxy
    city, region, country = get_geo_info(ip)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO clicks (site_id, ip, city, region, country) VALUES (%s, %s, %s, %s, %s)",
        (site_id, ip, city, region, country)
    )
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"status": "ok", "ip": ip, "city": city, "region": region, "country": country})

# Estatísticas de um site
@app.route("/api/stats/<int:site_id>", methods=["GET"])
def stats(site_id):
    conn = get_connection()
    cur = conn.cursor()

    # Pega todos cliques
    cur.execute(
        "SELECT city, region, country, created_at FROM clicks WHERE site_id=%s ORDER BY created_at DESC",
        (site_id,)
    )
    clicks = cur.fetchall()

    # Pega info do site
    cur.execute("SELECT name, url FROM sites WHERE id=%s", (site_id,))
    site = cur.fetchone()
    cur.close()
    conn.close()

    if not site:
        return jsonify({"error": "Site não encontrado"}), 404

    return jsonify({
        "site": {"name": site[0], "url": site[1]},
        "clicks": [
            {"city": c[0], "region": c[1], "country": c[2], "created_at": str(c[3])}
            for c in clicks
        ],
        "total_clicks": len(clicks)
    })

# -------------------------------
# Rodar servidor
# -------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Railway define a porta
    app.run(host="0.0.0.0", port=port)
