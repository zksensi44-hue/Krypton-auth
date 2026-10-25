
import os
import secrets
from urllib.parse import urlencode
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import (
    Flask, redirect, render_template, session,
    url_for, request, jsonify
)

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static")
)

app.secret_key = os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32)

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=True
)

DISCORD_API = "https://discord.com/api/v10"


def oauth_configured():
    return all(os.getenv(key) for key in (
        "DISCORD_CLIENT_ID",
        "DISCORD_CLIENT_SECRET",
        "DISCORD_REDIRECT_URI"
    ))


@app.get("/")
def index():
    return render_template(
        "index.html",
        user=session.get("user"),
        oauth_ready=oauth_configured()
    )


@app.get("/login/discord")
def login():
    if not oauth_configured():
        return render_template(
            "error.html",
            message="Configure as variáveis do Discord OAuth2 no Render."
        ), 503

    session["oauth_state"] = secrets.token_urlsafe(32)

    params = {
        "client_id": os.environ["DISCORD_CLIENT_ID"],
        "redirect_uri": os.environ["DISCORD_REDIRECT_URI"],
        "response_type": "code",
        "scope": "identify email",
        "state": session["oauth_state"]
    }

    return redirect(
        "https://discord.com/oauth2/authorize?" + urlencode(params)
    )


@app.get("/oauth/callback")
def callback():
    if request.args.get("error"):
        return render_template(
            "error.html",
            message="A autorização do Discord foi cancelada."
        ), 400

    state = session.pop("oauth_state", "")
    received_state = request.args.get("state", "")
    code = request.args.get("code")

    if (
        not oauth_configured()
        or not code
        or not state
        or not secrets.compare_digest(state, received_state)
    ):
        return render_template(
            "error.html",
            message="Resposta de autenticação inválida. Tente novamente."
        ), 400

    try:
        token_response = requests.post(
            f"{DISCORD_API}/oauth2/token",
            data={
                "client_id": os.environ["DISCORD_CLIENT_ID"],
                "client_secret": os.environ["DISCORD_CLIENT_SECRET"],
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": os.environ["DISCORD_REDIRECT_URI"]
            },
            timeout=15
        )
        token_response.raise_for_status()
        token_data = token_response.json()

        profile_response = requests.get(
            f"{DISCORD_API}/users/@me",
            headers={
                "Authorization": f"Bearer {token_data['access_token']}"
            },
            timeout=15
        )
        profile_response.raise_for_status()

        session.clear()
        session["user"] = profile_response.json()

        return redirect(url_for("dashboard"))

    except (requests.RequestException, KeyError, ValueError):
        app.logger.exception("Falha na autenticação Discord")
        return render_template(
            "error.html",
            message="Falha ao comunicar com o Discord. Tente novamente."
        ), 502


@app.get("/dashboard")
def dashboard():
    if not session.get("user"):
        return redirect(url_for("login"))

    return render_template(
        "dashboard.html",
        user=session["user"],
        cloud_api=os.getenv("KRYPTON_CLOUD_API_URL", "")
    )


@app.get("/api/me")
def me():
    if not session.get("user"):
        return jsonify({"error": "unauthorized"}), 401

    return jsonify({
        "user": session["user"],
        "cloud_integration": "not_configured",
        "message": "A API Cloud precisa ser configurada."
    })


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.get("/health")
def health():
    return jsonify({"status": "ok", "app": "Krypton Cloud"})


@app.errorhandler(500)
def internal_error(error):
    app.logger.exception("Erro interno ao processar a requisição")
    return (
        "Erro interno do servidor. Consulte os logs do Render.",
        500
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=False
    )
    
