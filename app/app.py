from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from pool_rating import calculate_new_ratings

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pool_rating.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database Models
class Player(db.Model):
    __tablename__ = 'PLAYER'
    player_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    rating = db.Column(db.Integer, default=1000)
    streak = db.Column(db.Integer, default=0)
    games_played = db.Column(db.Integer, default=0)
    last_played = db.Column(db.Integer, db.ForeignKey('GAME.game_id'))
    total_wins = db.Column(db.Integer, default=0)
    total_losses = db.Column(db.Integer, default=0)

class Game(db.Model):
    __tablename__ = 'GAME'
    game_id = db.Column(db.Integer, primary_key=True)
    player_id_1 = db.Column(db.Integer, db.ForeignKey('PLAYER.player_id'), nullable=False)
    player_id_2 = db.Column(db.Integer, db.ForeignKey('PLAYER.player_id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow)
    winner = db.Column(db.Integer, db.CheckConstraint('winner IN (0, 1, 2)'), nullable=False)

def create_database():
    if not os.path.exists('pool_rating.db'):
        db.create_all()
        print("Database created successfully.")
    else:
        print("Database already exists.")

with app.app_context():
    create_database()

# Helper Functions
def validate_player_names(data):
    if 'name' not in data or not data['name']:
        return "Name is required", 400
    return None

def validate_game_data(data):
    required_fields = ['player_id_1', 'player_id_2', 'winner']
    for field in required_fields:
        if field not in data:
            return f"{field} is required", 400
    return None

def get_multiplier(data):
    try:
        return max(int(data.get('multiplier', 1)), 1)
    except ValueError:
        return 1

# Player CRUD Operations
@app.route('/players', methods=['POST'])
def add_player():
    data = request.get_json()
    validation_error = validate_player_names(data)
    if validation_error:
        return jsonify({"message": validation_error[0]}), validation_error[1]

    if Player.query.filter_by(name=data['name']).first():
        return jsonify({"message": "Player name must be unique"}), 400

    new_player = Player(name=data['name'])
    db.session.add(new_player)
    db.session.commit()
    return jsonify({"message": "Player added", "player_id": new_player.player_id}), 201

@app.route('/players', methods=['GET'])
def get_players():
    players = Player.query.all()
    return jsonify([{
        'player_id': p.player_id,
        'name': p.name,
        'rating': p.rating,
        'streak': p.streak,
        'games_played': p.games_played,
        'total_wins': p.total_wins,
        'total_losses': p.total_losses
    } for p in players])

@app.route('/players/<int:player_id>', methods=['PUT'])
def update_player(player_id):
    data = request.get_json()
    player = Player.query.get(player_id)
    if not player:
        return jsonify({"message": "Player not found"}), 404

    for field, value in data.items():
        if hasattr(player, field):
            setattr(player, field, value)

    db.session.commit()
    return jsonify({"message": "Player updated"})

@app.route('/players/<int:player_id>', methods=['DELETE'])
def delete_player(player_id):
    player = Player.query.get(player_id)
    if not player:
        return jsonify({"message": "Player not found"}), 404

    db.session.delete(player)
    db.session.commit()
    return jsonify({"message": "Player deleted"})

# Record a game and update ratings
@app.route('/games', methods=['POST'])
def add_game():
    data = request.get_json()
    validation_error = validate_game_data(data)
    if validation_error:
        return jsonify({"message": validation_error[0]}), validation_error[1]

    player1, player2 = Player.query.get(data['player_id_1']), Player.query.get(data['player_id_2'])
    if not player1 or not player2:
        return jsonify({"message": "Both players must exist"}), 400

    if data['winner'] not in [0, 1, 2]:
        return jsonify({"message": "Winner must be 0, 1, or 2"}), 400

    multiplier = get_multiplier(data)
    
    new_game = Game(player_id_1=data['player_id_1'], player_id_2=data['player_id_2'], winner=data['winner'])
    db.session.add(new_game)
    db.session.commit()

    new_rating_a, new_rating_b = calculate_new_ratings(
        player1.rating, player2.rating,
        player1.games_played, player2.games_played,
        player1.streak, player2.streak,
        data['winner'],
        multiplier
    )

    player1.rating, player2.rating = new_rating_a, new_rating_b
    player1.games_played += 1
    player2.games_played += 1
    player1.last_played = player2.last_played = new_game.game_id

    # Update win/loss records and streaks
    if data['winner'] == 0:
        player1.total_wins += 1
        player2.total_losses += 1
        player1.streak = player1.streak + 1 if player1.streak >= 0 else 1
        player2.streak = max(player2.streak - 1, -5) if player2.streak > 0 else -1
    elif data['winner'] == 1:
        player2.total_wins += 1
        player1.total_losses += 1
        player2.streak = player2.streak + 1 if player2.streak >= 0 else 1
        player1.streak = max(player1.streak - 1, -5) if player1.streak > 0 else -1
    else:
        player1.streak = player2.streak = 0

    db.session.commit()
    return jsonify({"message": "Game added and ratings updated"})

@app.errorhandler(Exception)
def handle_exception(e):
    return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
