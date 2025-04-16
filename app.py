from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask import send_from_directory

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/fitness'
db = SQLAlchemy(app)

# Modelos
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    nombre = db.Column(db.String(255), nullable=False)
    apellidos = db.Column(db.String(255), nullable=False)
    telefono = db.Column(db.String(20), nullable=False)
    rol = db.Column(db.String(50), nullable=False)


class Training(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)  # <--- Corregido
    date = db.Column(db.String(50), nullable=False)
    exercises = db.Column(db.Text, nullable=False)  # JSON con ejercicios


@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory(app.static_folder, 'sitemap.xml')

@app.route('/robots.txt')
def robots():
    return send_from_directory(app.static_folder, 'robots.txt')


# Rutas
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form['username']  # Puede ser username o email
        password = request.form['password']
        user = Usuario.query.filter(
            (Usuario.username == identifier) | (Usuario.email == identifier)
        ).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = user.rol
            return redirect(url_for('dashboard'))
        return render_template('login.html', error='Datos incorrectos')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        nombre = request.form['nombre']
        apellidos = request.form['apellidos']
        telefono = request.form['telefono']
        rol = request.form['role']

        new_user = Usuario(
            username=username,
            email=email,
            password=password,
            nombre=nombre,
            apellidos=apellidos,
            telefono=telefono,
            rol=rol
        )

        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Obtener el usuario de la base de datos
    user = Usuario.query.get(session['user_id'])
    
    if user:
        return render_template('user_dashboard.html', username=user.nombre)  # Pasar el nombre del usuario
    return redirect(url_for('login'))

# Rutas
@app.route('/trainings')
def trainings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('trainings.html')  # Crearemos este archivo luego

@app.route('/my_info', methods=['GET'])
def my_info():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Obtener el usuario de la base de datos
    user = Usuario.query.get(session['user_id'])
    
    if user:
        return render_template('my_info.html', user=user)
    return redirect(url_for('dashboard'))

@app.route('/update_info', methods=['POST'])
def update_info():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = Usuario.query.get(session['user_id'])
    if user:
        user.nombre = request.form['nombre']
        user.apellidos = request.form['apellidos']
        user.telefono = request.form['telefono']
        user.email = request.form['email']
        user.username = request.form['username']

        db.session.commit()
        return redirect(url_for('my_info'))
    else:
        return redirect(url_for('login'))


@app.route('/exercises')
def exercises():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('exercises.html')  # Crearemos este archivo luego

@app.route('/sobre_mi')
def sobre_mi():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('sobre_mi.html')  # Crearemos este archivo luego


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('role', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
