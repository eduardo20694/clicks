import os
import logging
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
import psycopg2
from psycopg2 import pool
import requests

# -------------------------------
# Configuração Flask
# -------------------------------
app = Flask(__name__)

# -------------------------------
# Logs configurados
# -------------------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# -------------------------------
# CORS PERFEITO
# -------------------------------
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True,
     allow_headers="*", methods=["GET", "POST", "OPTIONS"])

# -------------------------------
# Conexão com PostgreSQL (Railway) usando pool
# -------------------------------
DATABASE_URL = os.getenv("DATABASE_URL") or \
    "postgresql://postgres:jghiePewYfPTZltWEEWnVhySPcMxwKkh@tramway.proxy.rlwy.net:14408/railway"

try:
    db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, dsn=DATABASE_URL, sslmode="require")
    logging.info("Conexão com PostgreSQL inicializada com sucesso!")
except Exception as e:
    logging.error(f"Erro ao conectar no PostgreSQL: {e}")
    raise e

def get_cursor():
    conn = db_pool.getconn()
    cursor = conn.cursor()
    return conn, cursor

def release_cursor(conn, cursor):
    cursor.close()
    db_pool.putconn(conn)

# -------------------------------
# Função para geolocalização
# -------------------------------
def get_geo_info(ip):
    try:
        res = requests.get(f"https://ipapi.co/{ip}/json/", timeout=3)
        res.raise_for_status()
        data = res.json()
        return data.get("city"), data.get("region"), data.get("country_name")
    except Exception as e:
        logging.warning(f"Não foi possível obter geolocalização para IP {ip}: {e}")
        return None, None, None

# -------------------------------
# Endpoints
# -------------------------------

@app.route("/api/sites", methods=["POST"])
def add_site():
    try:
        data = request.json
        conn, cursor = get_cursor()
        cursor.execute(
            "INSERT INTO sites (name, url) VALUES (%s, %s) RETURNING id",
            (data["name"], data["url"])
        )
        site_id = cursor.fetchone()[0]
        conn.commit()
        release_cursor(conn, cursor)
        logging.info(f"Novo site adicionado: {data['name']} ({site_id})")
        return jsonify({"status": "ok", "site_id": site_id})
    except Exception as e:
        logging.error(f"Erro ao adicionar site: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/sites", methods=["GET"])
def list_sites():
    try:
        conn, cursor = get_cursor()
        cursor.execute("SELECT id, name, url FROM sites")
        sites = cursor.fetchall()
        release_cursor(conn, cursor)
        return jsonify([{"id": s[0], "name": s[1], "url": s[2]} for s in sites])
    except Exception as e:
        logging.error(f"Erro ao listar sites: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/click", methods=["POST"])
def click():
    try:
        data = request.json
        site_id = data.get("site_id")
        if not site_id:
            return jsonify({"error": "site_id é obrigatório"}), 400

        ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        city, region, country = get_geo_info(ip)

        conn, cursor = get_cursor()
        cursor.execute(
            "INSERT INTO clicks (site_id, ip, city, region, country) VALUES (%s,%s,%s,%s,%s)",
            (site_id, ip, city, region, country)
        )
        conn.commit()
        release_cursor(conn, cursor)

        logging.info(f"Clique registrado no site {site_id} - IP: {ip}")
        return jsonify({"status": "ok", "ip": ip, "city": city, "region": region, "country": country})
    except Exception as e:
        logging.error(f"Erro ao registrar clique: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/stats/<int:site_id>", methods=["GET"])
def stats(site_id):
    try:
        conn, cursor = get_cursor()
        cursor.execute(
            "SELECT city, region, country, created_at FROM clicks WHERE site_id=%s ORDER BY created_at DESC",
            (site_id,)
        )
        clicks = cursor.fetchall()

        cursor.execute("SELECT name, url FROM sites WHERE id=%s", (site_id,))
        site = cursor.fetchone()
        release_cursor(conn, cursor)

        if not site:
            return jsonify({"error": "Site não encontrado"}), 404

        return jsonify({
            "site": {"name": site[0], "url": site[1]},
            "clicks": [{"city": c[0], "region": c[1], "country": c[2], "created_at": str(c[3])} for c in clicks],
            "total_clicks": len(clicks)
        })
    except Exception as e:
        logging.error(f"Erro ao buscar stats do site {site_id}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# -------------------------------
# Endpoint de redirecionamento de cliques (contagem em tempo real)
# -------------------------------
@app.route("/r/<int:site_id>", methods=["GET"])
def redirect_site(site_id):
    try:
        conn, cursor = get_cursor()
        cursor.execute("SELECT url FROM sites WHERE id=%s", (site_id,))
        site = cursor.fetchone()

        if not site:
            release_cursor(conn, cursor)
            return "Site não encontrado", 404

        url_real = site[0]

        ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        city, region, country = get_geo_info(ip)

        cursor.execute(
            "INSERT INTO clicks (site_id, ip, city, region, country) VALUES (%s,%s,%s,%s,%s)",
            (site_id, ip, city, region, country)
        )
        conn.commit()
        release_cursor(conn, cursor)

        logging.info(f"Clique redirecionado para site {site_id} - IP: {ip}")
        return redirect(url_real)
    except Exception as e:
        logging.error(f"Erro no redirecionamento: {e}")
        return "Erro ao redirecionar", 500

# -------------------------------
# Rodar servidor
# -------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logging.info(f"API de cliques rodando na porta {port}")
    app.run(host="0.0.0.0", port=port)
