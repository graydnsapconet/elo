from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = 'key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pool_rating.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)  # Session expiration time
db = SQLAlchemy(app)

# Database models
class Player(db.Model):
    __tablename__ = 'players'

    player_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    rating = db.Column(db.Float, default=1000)
    lowest_rating = db.Column(db.Float, default=1000)
    highest_rating = db.Column(db.Float, default=1000)
    games_played = db.Column(db.Integer, default=0)
    streak = db.Column(db.Integer, default=0)
    longest_streak = db.Column(db.Integer, default=0)
    last_played = db.Column(db.Integer, db.ForeignKey('games.game_id'), nullable=True)
    total_wins = db.Column(db.Integer, default=0)
    total_losses = db.Column(db.Integer, default=0)

class Game(db.Model):
    __tablename__ = 'games'

    game_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    player_a = db.Column(db.Integer, db.ForeignKey('players.player_id'))
    player_b = db.Column(db.Integer, db.ForeignKey('players.player_id'))
    k_multiplier = db.Column(db.Integer, default=1)
    rated = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(20), default='pending')  # Possible values: 'pending', 'completed', 'no_contest'
    date_completed = db.Column(db.String(10), nullable=True)
    result = db.Column(db.Integer, nullable=True)  # 0 = player_a, 1 = player_b, 2 = draw

class Challenge(db.Model):
    __tablename__ = 'challenges'

    challenge_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timestamp = db.Column(db.DateTime, nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('games.game_id'))
    status = db.Column(db.String(20), default='pending')  # Possible values: 'pending', 'accepted', 'declined', 'completed', 'no_contest'

with app.app_context():
    db.create_all()

def authenticate(username, password):
    player = Player.query.filter_by(username=username).first()
    return player and player.password == password

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if authenticate(username, password):
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('challenge'))
        flash('Invalid credentials, please try again.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password == confirm_password:
            new_player = Player(username=username, password=password)
            db.session.add(new_player)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        flash('Passwords do not match.', 'danger')
    return render_template('register.html')

@app.route('/challenge', methods=['GET', 'POST'])
def challenge():
    if 'username' not in session:
        flash('Please log in to access this page.', 'danger')
        return redirect(url_for('login'))

    current_player = Player.query.filter_by(username=session['username']).first()

    ongoing_challenges = Challenge.query.filter(
        Challenge.status.notin_(['no_contest', 'completed']),
        Challenge.game_id.isnot(None)
    ).all()

    filtered_challenges = []
    for challenge in ongoing_challenges:
        game = Game.query.get(challenge.game_id)
        if game and game.player_b == current_player.player_id:
            filtered_challenges.append(challenge)

    players = Player.query.all()

    return render_template('challenge.html', players=players, ongoing_challenges=filtered_challenges, current_player=current_player)

@app.route('/challenge_player/<int:player_id>', methods=['POST'])
def challenge_player(player_id):
    if 'username' not in session:
        flash('Please log in to access this page.', 'danger')
        return redirect(url_for('login'))

    current_player = Player.query.filter_by(username=session['username']).first()

    # Check if a challenge already exists between the current player and the player being challenged
    existing_challenge = Challenge.query.join(Game).filter(
        ((Game.player_a == current_player.player_id) & (Game.player_b == player_id)) |
        ((Game.player_a == player_id) & (Game.player_b == current_player.player_id)),
        Challenge.status.notin_(['completed', 'no_contest'])  # Exclude completed or no contest challenges
    ).first()

    if existing_challenge:
        flash('A challenge already exists between you and this player.', 'warning')
        return redirect(url_for('challenge'))

    new_game = Game(player_a=current_player.player_id, player_b=player_id)
    db.session.add(new_game)
    db.session.commit()

    new_challenge = Challenge(game_id=new_game.game_id, timestamp=datetime.now())
    db.session.add(new_challenge)
    db.session.commit()

    flash('Challenge sent successfully!', 'success')
    return redirect(url_for('challenge'))


@app.route('/respond_to_challenge/<int:challenge_id>', methods=['POST'])
def respond_to_challenge(challenge_id):
    if 'username' not in session:
        flash('Please log in to access this page.', 'danger')
        return redirect(url_for('login'))

    challenge = Challenge.query.get(challenge_id)
    if not challenge:
        flash('Challenge not found.', 'danger')
        return redirect(url_for('challenge'))

    response = request.form['response']
    if response == 'accept':
        challenge.status = 'accepted'
        flash('Challenge accepted!', 'success')
    elif response == 'decline':
        challenge.status = 'declined'
        flash('Challenge declined.', 'info')

    db.session.commit()
    return redirect(url_for('challenge'))


@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run("0.0.0.0", 5000)
