from flask import Flask, render_template, request, redirect, url_for, session
import os
import pickle
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # замените на свой ключ

# Путь к кэшу тревожных сообщений
CACHE_FILE = os.path.join(os.path.dirname(__file__), '../bot/cache/history_cache.pkl')

# Простые логины и пароли (в реальности используйте шифрование и БД)
USERS = {
    'teacher': 'pass123',
    'admin': 'adminpass'
}

# Декоратор для проверки авторизации
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/', methods=['GET'])
@login_required
def red_flags():
    alerts = []
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "rb") as f:
            data = pickle.load(f)
            for user_id, history in data.items():
                for entry in history:
                    if entry["role"] == "user":
                        text = entry["content"].lower()
                        if entry.get("red_flag"):
                            alerts.append({"user_id": user_id, "message": entry["content"]})

    return render_template("index.html", alerts=alerts, username=session['username'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if USERS.get(username) == password:
            session['username'] = username
            return redirect(url_for('red_flags'))
        else:
            return render_template("login.html", error="Неверный логин или пароль")
    return render_template("login.html")

@app.route('/logout')
@login_required
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, port=5001)
