from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import pandas as pd
import io
import os
import json

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Configuración de Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive']
CSV_FILE_ID = '1bTIrM42mmBL3L9i35b_y0eLnJEN9E0TU'  # ID real de tu archivo

# ------------------ Google Drive ------------------
# def get_drive_service():
#     SERVICE_ACCOUNT_FILE = 'credenciales.json'
#     creds = service_account.Credentials.from_service_account_file(
#         SERVICE_ACCOUNT_FILE, scopes=SCOPES)
#     return build('drive', 'v3', credentials=creds)
def get_drive_service():
    SERVICE_ACCOUNT_FILE = '/etc/secrets/credenciales.json'
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def leer_usuarios_csv(file_id):
    service = get_drive_service()
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    return pd.read_csv(fh)

def escribir_usuarios_csv(df, file_id):
    service = get_drive_service()
    df.to_csv("temp.csv", index=False)
    media = MediaFileUpload("temp.csv", mimetype='text/csv', resumable=True)
    service.files().update(fileId=file_id, media_body=media).execute()

# ------------------ Rutas ------------------

@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory(app.static_folder, 'sitemap.xml')

@app.route('/robots.txt')
def robots():
    return send_from_directory(app.static_folder, 'robots.txt')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        df = leer_usuarios_csv(CSV_FILE_ID)
        new_id = df['id'].max() + 1 if not df.empty else 1

        nuevo_usuario = {
            'id': new_id,
            'username': request.form['username'],
            'email': request.form['email'],
            'password': generate_password_hash(request.form['password']),
            'nombre': request.form['nombre'],
            'apellidos': request.form['apellidos'],
            'telefono': request.form['telefono'],
            'rol': request.form['role']
        }

        df = pd.concat([df, pd.DataFrame([nuevo_usuario])], ignore_index=True)
        escribir_usuarios_csv(df, CSV_FILE_ID)
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form['username']
        password = request.form['password']
        df = leer_usuarios_csv(CSV_FILE_ID)

        user = df[(df['username'] == identifier) | (df['email'] == identifier)]

        if not user.empty and check_password_hash(user.iloc[0]['password'], password):
            session['user_id'] = int(user.iloc[0]['id'])
            session['role'] = user.iloc[0]['rol']
            session['username'] = user.iloc[0]['nombre']
            return redirect(url_for('dashboard'))
        return render_template('login.html', error='Datos incorrectos')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    df = leer_usuarios_csv(CSV_FILE_ID)
    user = df[df['id'] == session['user_id']]
    if not user.empty:
        return render_template('user_dashboard.html', username=user.iloc[0]['nombre'])
    return redirect(url_for('login'))

@app.route('/trainings')
def trainings():
    return render_template('en_construccion.html')


@app.route('/exercises')
def exercises():
    return render_template('en_construccion.html')


@app.route('/sobre_mi')
def sobre_mi():
    return render_template('en_construccion.html')

@app.route('/my_info')
def my_info():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    df = leer_usuarios_csv(CSV_FILE_ID)
    user = df[df['id'] == session['user_id']]
    if not user.empty:
        return render_template('my_info.html', user=user.iloc[0])
    return redirect(url_for('dashboard'))

@app.route('/update_info', methods=['POST'])
def update_info():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    df = leer_usuarios_csv(CSV_FILE_ID)
    idx = df.index[df['id'] == session['user_id']].tolist()

    if idx:
        i = idx[0]
        df.at[i, 'nombre'] = request.form['nombre']
        df.at[i, 'apellidos'] = request.form['apellidos']
        df.at[i, 'telefono'] = request.form['telefono']
        df.at[i, 'email'] = request.form['email']
        df.at[i, 'username'] = request.form['username']

        escribir_usuarios_csv(df, CSV_FILE_ID)
        return redirect(url_for('my_info'))
    else:
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('role', None)
    session.pop('username', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
