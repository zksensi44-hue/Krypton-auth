import os, secrets
from urllib.parse import urlencode
from flask import Flask, redirect, render_template, session, url_for, request, jsonify
import requests
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY') or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=os.getenv('COOKIE_SECURE','false').lower()=='true')
DISCORD_API='https://discord.com/api/v10'

def oauth_configured():
    return all(os.getenv(k) for k in ('DISCORD_CLIENT_ID','DISCORD_CLIENT_SECRET','DISCORD_REDIRECT_URI'))

def discord_headers():
    return {'Authorization': 'Bearer '+session['access_token']}

@app.get('/')
def index():
    return render_template('index.html', user=session.get('user'), oauth_ready=oauth_configured())

@app.get('/login/discord')
def login():
    if not oauth_configured(): return render_template('error.html', message='O login Discord ainda não foi configurado no arquivo .env.'), 503
    session['oauth_state']=secrets.token_urlsafe(24)
    params={'client_id':os.environ['DISCORD_CLIENT_ID'],'redirect_uri':os.environ['DISCORD_REDIRECT_URI'],'response_type':'code','scope':'identify email','state':session['oauth_state'],'prompt':'consent'}
    return redirect('https://discord.com/oauth2/authorize?'+urlencode(params))

@app.get('/oauth/callback')
def callback():
    if request.args.get('error'): return render_template('error.html', message='A autorização foi cancelada ou negada.'), 400
    if not oauth_configured() or not request.args.get('code') or not secrets.compare_digest(request.args.get('state',''),session.pop('oauth_state','')):
        return render_template('error.html', message='Não foi possível validar a resposta do Discord. Tente entrar novamente.'), 400
    try:
        token=requests.post('https://discord.com/api/v10/oauth2/token', data={'client_id':os.environ['DISCORD_CLIENT_ID'],'client_secret':os.environ['DISCORD_CLIENT_SECRET'],'grant_type':'authorization_code','code':request.args['code'],'redirect_uri':os.environ['DISCORD_REDIRECT_URI']}, headers={'Content-Type':'application/x-www-form-urlencoded'}, timeout=12)
        token.raise_for_status(); data=token.json()
        profile=requests.get(DISCORD_API+'/users/@me',headers={'Authorization':'Bearer '+data['access_token']},timeout=12); profile.raise_for_status()
        session.clear(); session['access_token']=data['access_token']; session['user']=profile.json()
        return redirect(url_for('dashboard'))
    except (requests.RequestException, KeyError, ValueError):
        return render_template('error.html', message='Falha ao comunicar com o Discord. Tente novamente.'), 502

@app.get('/dashboard')
def dashboard():
    if not session.get('user'): return redirect(url_for('login'))
    # A source contém módulo Cloud no bot, mas a API de Cloud está desativada na configuração
    # e não foi encontrada uma API web autenticada para ler/controlar bots. Não simulamos dados.
    return render_template('dashboard.html', user=session['user'], cloud_api=os.getenv('KRYPTON_CLOUD_API_URL',''))

@app.get('/api/me')
def me():
    if not session.get('user'): return jsonify({'error':'unauthorized'}),401
    return jsonify({'user':session['user'],'cloud_integration':'not_configured','message':'Configure uma API Cloud autenticada para exibir dados reais.'})

@app.post('/logout')
def logout():
    session.clear(); return redirect(url_for('index'))

@app.get('/health')
def health(): return jsonify({'status':'ok','app':'Krypton Cloud'})

if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.getenv('PORT','5000')),debug=False)
