import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import requests

# -------------------------------
# Configuração Flask
# -------------------------------
app = Flask(__name__)
CORS(app)

# -------------------------------
# Conexão com PostgreSQL (Railway)
# -------------------------------
DATABASE_URL = os.getenv("DATABASE_URL") or \
    "postgresql://postgres:jghiePewYfPTZltWEEWnVhySPcMxwKkh@tramway.proxy.rlwy.net:14408/railway"

conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cursor = conn.cursor()

# -------------------------------
# Função para geolocalização
# -------------------------------
def get_geo_info(ip):
    try:
        res = requests.get(f"https://ipapi.co/{ip}/json/")
        data = res.json()
        return data.get("city"), data.get("region"), data.get("country_name")
    except:
        return None, None, None

# -------------------------------
# Endpoints
# -------------------------------

# Adicionar novo site
@app.route("/api/sites", methods=["POST"])
def add_site():
    data = request.json
    cursor.execute(
        "INSERT INTO sites (name, url) VALUES (%s, %s) RETURNING id",
        (data["name"], data["url"])
    )
    site_id = cursor.fetchone()[0]
    conn.commit()
    return jsonify({"status": "ok", "site_id": site_id})

# Listar todos sites
@app.route("/api/sites", methods=["GET"])
def list_sites():
    cursor.execute("SELECT id, name, url FROM sites")
    sites = cursor.fetchall()
    return jsonify([{"id": s[0], "name": s[1], "url": s[2]} for s in sites])

# Registrar clique
@app.route("/api/click", methods=["POST"])
def click():
    data = request.json
    site_id = data.get("site_id")
    if not site_id:
        return jsonify({"error": "site_id é obrigatório"}), 400

    ip = request.remote_addr
    city, region, country = get_geo_info(ip)

    cursor.execute(
        "INSERT INTO clicks (site_id, ip, city, region, country) VALUES (%s,%s,%s,%s,%s)",
        (site_id, ip, city, region, country)
    )
    conn.commit()
    return jsonify({"status": "ok", "ip": ip, "city": city, "region": region, "country": country})

# Estatísticas de um site
@app.route("/api/stats/<int:site_id>", methods=["GET"])
def stats(site_id):
    # Pega todos cliques
    cursor.execute(
        "SELECT city, region, country, created_at FROM clicks WHERE site_id=%s ORDER BY created_at DESC",
        (site_id,)
    )
    clicks = cursor.fetchall()

    # Pega info do site
    cursor.execute("SELECT name, url FROM sites WHERE id=%s", (site_id,))
    site = cursor.fetchone()
    if not site:
        return jsonify({"error": "Site não encontrado"}), 404

    return jsonify({
        "site": {"name": site[0], "url": site[1]},
        "clicks": [{"city": c[0], "region": c[1], "country": c[2], "created_at": str(c[3])} for c in clicks],
        "total_clicks": len(clicks)
    })

# -------------------------------
# Rodar servidor
# -------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
