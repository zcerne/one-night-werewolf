"""
Flask server with SocketIO for One Night Werewolf multiplayer game.
Handles WebSocket connections and game events.
"""

from flask import Flask, render_template, send_from_directory, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
from game_state import GameManager
import os

app = Flask(__name__, 
            static_folder='webpage',
            template_folder='webpage')
app.config['SECRET_KEY'] = 'werewolf-secret-key-change-in-production'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize game manager
game_manager = GameManager()

# Store socket_id to player mapping
socket_to_player = {}  # {socket_id: (game_code, player_name)}


@app.route('/')
def index():
    """Serve the main HTML page."""
    return send_from_directory('webpage', 'main.html')


@app.route('/<path:path>')
def serve_static(path):
    """Serve static files from webpage directory."""
    return send_from_directory('webpage', path)


@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    print(f"Client connected: {request.sid}")
    emit('connected', {'message': 'Connected to server'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    sid = request.sid
    print(f"Client disconnected: {sid}")
    
    # Remove player from game if they were in one
    if sid in socket_to_player:
        game_code, player_name = socket_to_player[sid]
        game = game_manager.get_game(game_code)
        if game and not game.initialized:
            game.remove_player(player_name)
            # Notify other players
            emit('player_left', {
                'player_name': player_name,
                'players': game.get_players_info()
            }, room=game_code)
        del socket_to_player[sid]


@socketio.on('create_game')
def handle_create_game(data):
    """
    Create a new game.
    Expected data: {'player_name': str}
    """
    player_name = data.get('player_name', '').strip()
    
    if not player_name:
        emit('error', {'message': 'Player name is required'})
        return
    
    # Create game
    game_code, game = game_manager.create_game(player_name)
    
    # Store socket mapping
    socket_to_player[request.sid] = (game_code, player_name)
    
    # Join room for this game
    join_room(game_code)
    
    # Update player's socket_id
    game.players[player_name].socket_id = request.sid
    
    print(f"Game created: {game_code} by {player_name}")
    
    emit('game_created', {
        'game_code': game_code,
        'player_name': player_name,
        'is_host': True,
        'game_state': game.to_dict()
    })


@socketio.on('join_game')
def handle_join_game(data):
    """
    Join an existing game.
    Expected data: {'game_code': str, 'player_name': str}
    """
    game_code = data.get('game_code', '').strip().upper()
    player_name = data.get('player_name', '').strip()
    
    if not game_code or not player_name:
        emit('error', {'message': 'Game code and player name are required'})
        return
    
    # Get game
    game = game_manager.get_game(game_code)
    if not game:
        emit('error', {'message': f'Game {game_code} not found'})
        return
    
    # Add player to game
    success, message = game.add_player(player_name, request.sid)
    if not success:
        emit('error', {'message': message})
        return
    
    # Store socket mapping
    socket_to_player[request.sid] = (game_code, player_name)
    
    # Join room for this game
    join_room(game_code)
    
    print(f"Player {player_name} joined game {game_code}")
    
    # Notify the joining player
    emit('game_joined', {
        'game_code': game_code,
        'player_name': player_name,
        'is_host': player_name == game.host_name,
        'game_state': game.to_dict()
    })
    
    # Notify all players in the game
    emit('player_joined', {
        'player_name': player_name,
        'players': game.get_players_info(),
        'players_count': len(game.players)
    }, room=game_code)


@socketio.on('set_player_count')
def handle_set_player_count(data):
    """
    Set the number of players for the game (host only).
    Expected data: {'game_code': str, 'num_players': int}
    """
    game_code = data.get('game_code', '').strip().upper()
    num_players = data.get('num_players')
    
    game = game_manager.get_game(game_code)
    if not game:
        emit('error', {'message': f'Game {game_code} not found'})
        return
    
    # Verify this is the host
    if request.sid in socket_to_player:
        _, player_name = socket_to_player[request.sid]
        if player_name != game.host_name:
            emit('error', {'message': 'Only the host can set player count'})
            return
    
    success, message = game.set_player_count(num_players)
    if not success:
        emit('error', {'message': message})
        return
    
    print(f"Game {game_code}: Player count set to {num_players}")
    
    # Notify all players
    emit('player_count_set', {
        'num_players': num_players,
        'game_state': game.to_dict()
    }, room=game_code)


@socketio.on('add_character')
def handle_add_character(data):
    """
    Add a character to the game (host only).
    Expected data: {'game_code': str, 'character': str}
    """
    game_code = data.get('game_code', '').strip().upper()
    character = data.get('character', '').strip()
    
    game = game_manager.get_game(game_code)
    if not game:
        emit('error', {'message': f'Game {game_code} not found'})
        return
    
    # Verify this is the host
    if request.sid in socket_to_player:
        _, player_name = socket_to_player[request.sid]
        if player_name != game.host_name:
            emit('error', {'message': 'Only the host can add characters'})
            return
    
    success, message = game.add_character(character)
    if not success:
        emit('error', {'message': message})
        return
    
    print(f"Game {game_code}: Character '{character}' added")
    
    # Notify all players
    emit('character_added', {
        'character': character,
        'characters_in_game': game.characters_in_game,
        'game_state': game.to_dict()
    }, room=game_code)


@socketio.on('clear_characters')
def handle_clear_characters(data):
    """
    Clear all characters (host only).
    Expected data: {'game_code': str}
    """
    game_code = data.get('game_code', '').strip().upper()
    
    game = game_manager.get_game(game_code)
    if not game:
        emit('error', {'message': f'Game {game_code} not found'})
        return
    
    # Verify this is the host
    if request.sid in socket_to_player:
        _, player_name = socket_to_player[request.sid]
        if player_name != game.host_name:
            emit('error', {'message': 'Only the host can clear characters'})
            return
    
    success, message = game.clear_characters()
    if not success:
        emit('error', {'message': message})
        return
    
    print(f"Game {game_code}: Characters cleared")
    
    # Notify all players
    emit('characters_cleared', {
        'game_state': game.to_dict()
    }, room=game_code)


@socketio.on('initialize_game')
def handle_initialize_game(data):
    """
    Initialize the game and distribute roles (host only).
    Expected data: {'game_code': str}
    """
    game_code = data.get('game_code', '').strip().upper()
    
    game = game_manager.get_game(game_code)
    if not game:
        emit('error', {'message': f'Game {game_code} not found'})
        return
    
    # Verify this is the host
    if request.sid in socket_to_player:
        _, player_name = socket_to_player[request.sid]
        if player_name != game.host_name:
            emit('error', {'message': 'Only the host can initialize the game'})
            return
    
    success, message = game.initialize_game()
    if not success:
        emit('error', {'message': message})
        return
    
    print(f"Game {game_code}: Game initialized")
    
    # Send each player their role privately
    for player_name, player_state in game.players.items():
        if player_state.socket_id:
            socketio.emit('role_assigned', {
                'role': player_state.initial_role,
                'player_name': player_name
            }, room=player_state.socket_id)
    
    # Notify all players that game started (without revealing roles)
    emit('game_initialized', {
        'message': 'Game has started! Check your role.',
        'game_state': game.to_dict(include_roles=False),
        'center_cards_count': len(game.center_cards)
    }, room=game_code)


@socketio.on('request_role')
def handle_request_role(data):
    """
    Request player's own role.
    Expected data: {'game_code': str}
    """
    game_code = data.get('game_code', '').strip().upper()
    
    game = game_manager.get_game(game_code)
    if not game:
        emit('error', {'message': f'Game {game_code} not found'})
        return
    
    if not game.initialized:
        emit('error', {'message': 'Game not initialized yet'})
        return
    
    # Get player name from socket
    if request.sid in socket_to_player:
        _, player_name = socket_to_player[request.sid]
        role = game.get_player_role(player_name)
        if role:
            emit('role_info', {
                'role': role,
                'player_name': player_name
            })
        else:
            emit('error', {'message': 'Could not retrieve role'})
    else:
        emit('error', {'message': 'Player not found in game'})


@socketio.on('get_center_cards')
def handle_get_center_cards(data):
    """
    Get center cards (only after game is initialized, for host/debugging).
    Expected data: {'game_code': str}
    """
    game_code = data.get('game_code', '').strip().upper()
    
    game = game_manager.get_game(game_code)
    if not game:
        emit('error', {'message': f'Game {game_code} not found'})
        return
    
    if not game.initialized:
        emit('error', {'message': 'Game not initialized yet'})
        return
    
    # Verify this is the host
    if request.sid in socket_to_player:
        _, player_name = socket_to_player[request.sid]
        if player_name != game.host_name:
            emit('error', {'message': 'Only the host can view center cards'})
            return
    
    emit('center_cards', {
        'cards': game.get_center_cards()
    })


if __name__ == '__main__':
    print("Starting One Night Werewolf Server...")
    print("Server will be available at: http://localhost:5000")
    print("Press Ctrl+C to stop the server")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
