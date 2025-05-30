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
SERVICE_ACCOUNT_FILE = 'clave.json'
CSV_FILE_ID = '1-0aIHyyoUmUg07YqZWjLcL0dqfcrBW9w'  # usuarios.csv
EJERCICIOS_FILE_ID = '1L2SdCBEWaxSaqtl5vWK4HRbqhiv7J-yY'  # ejercicios.csv
# ASIGNACIONES_FILE_ID = 'PENDIENTE_DE_REEMPLAZAR'  # asignaciones.csv (pendiente)

# ------------------ Google Drive ------------------
def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def leer_csv(file_id):
    service = get_drive_service()
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    fh.seek(0)
    return pd.read_csv(fh)

def escribir_csv(df, file_id):
    service = get_drive_service()
    temp_file = 'temp.csv'
    df.to_csv(temp_file, index=False)
    media = MediaFileUpload(temp_file, mimetype='text/csv', resumable=True)
    service.files().update(fileId=file_id, media_body=media).execute()

# Funciones específicas

def leer_usuarios_csv():
    return leer_csv(CSV_FILE_ID)

def escribir_usuarios_csv(df):
    escribir_csv(df, CSV_FILE_ID)

def leer_ejercicios_csv():
    return leer_csv(EJERCICIOS_FILE_ID)

# def leer_asignaciones_csv():
#     return leer_csv(ASIGNACIONES_FILE_ID)

# def escribir_asignaciones_csv(df):
#     escribir_csv(df, ASIGNACIONES_FILE_ID)

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

#---------------------LOGIN/REGISTER---------------------------------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        df = leer_usuarios_csv()
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
        escribir_usuarios_csv(df)
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form['username']
        password = request.form['password']
        df = leer_usuarios_csv()

        user = df[(df['username'] == identifier) | (df['email'] == identifier)]

        if not user.empty and check_password_hash(user.iloc[0]['password'], password):
            session['user_id'] = int(user.iloc[0]['id'])
            session['role'] = user.iloc[0]['rol']
            session['username'] = user.iloc[0]['nombre']

            # Redirige según el rol
            if user.iloc[0]['rol'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('dashboard'))

        return render_template('login.html', error='Datos incorrectos')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('role', None)
    session.pop('username', None)
    return redirect(url_for('index'))

#---------------------ADMIN---------------------------------------------

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('dashboard'))

    df = leer_usuarios_csv()

    # Filtrar solo usuarios normales (no admins)
    solo_usuarios = df[df['rol'] == 'user']

    total_usuarios = len(solo_usuarios)
    ultimos_usuarios = solo_usuarios.sort_values(by='id', ascending=False).head(5).to_dict(orient='records')

    return render_template('admin_dashboard.html',
                           username=session.get('username'),
                           total_usuarios=total_usuarios,
                           ultimos_usuarios=ultimos_usuarios,
                           active_page='panel')



@app.route('/admin_usuarios')
def admin_usuarios():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('dashboard'))

    df = leer_usuarios_csv()
    usuarios = df[df['rol'] != 'admin'].to_dict(orient='records')
    return render_template('admin_usuarios.html', usuarios=usuarios, active_page='usuarios')


@app.route('/admin_entrenamientos')
def admin_entrenamientos():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('dashboard'))

    df = leer_usuarios_csv()
    usuarios = df[df['rol'] != 'admin'].to_dict(orient='records')

    return render_template('asignar_entrenamientos.html', usuarios=usuarios, active_page='entrenamientos')

@app.route('/admin/entrenamientos/<int:user_id>')
def ver_rutina_usuario(user_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('dashboard'))

    df_usuarios = leer_usuarios_csv()
    usuario = df_usuarios[df_usuarios['id'] == user_id].to_dict(orient='records')

    if not usuario:
        return "Usuario no encontrado", 404

    usuario = usuario[0]
    dias = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']

    # Leer y agrupar los ejercicios desde el CSV
    df_ejercicios = leer_ejercicios_csv()
    ejercicios = {}
    for _, row in df_ejercicios.iterrows():
        cat = row['categoria']
        sub = row['subcategoria']
        nombre = row['ejercicio']
        ejercicios.setdefault(cat, {}).setdefault(sub, []).append(nombre)

    ejercicios_json = json.dumps(ejercicios, ensure_ascii=False)

    return render_template('ver_rutina_usuario.html',
                           usuario=usuario,
                           dias=dias,
                           ejercicios_json=ejercicios_json,
                           active_page='entrenamientos')




@app.route('/admin_estadisticas')
def admin_estadisticas():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('dashboard'))
    return render_template('en_construccion_admin.html', titulo="Estadísticas", mensaje="Próximamente podrás ver estadísticas detalladas aquí.", active_page='estadisticas')



#---------------------USUARIO---------------------------------------------

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    df = leer_usuarios_csv()
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
    df = leer_usuarios_csv()
    user = df[df['id'] == session['user_id']]
    if not user.empty:
        return render_template('my_info.html', user=user.iloc[0])
    return redirect(url_for('dashboard'))

@app.route('/update_info', methods=['POST'])
def update_info():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    df = leer_usuarios_csv()
    idx = df.index[df['id'] == session['user_id']].tolist()

    if idx:
        i = idx[0]
        df.at[i, 'nombre'] = request.form['nombre']
        df.at[i, 'apellidos'] = request.form['apellidos']
        df.at[i, 'telefono'] = request.form['telefono']
        df.at[i, 'email'] = request.form['email']
        df.at[i, 'username'] = request.form['username']

        escribir_usuarios_csv(df)
        return redirect(url_for('my_info'))
    else:
        return redirect(url_for('login'))

#---------------------MAIN---------------------------------------------

if __name__ == '__main__':
    app.run(debug=True)
