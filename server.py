"""
Flask server with SocketIO for One Night Werewolf multiplayer game.
Handles WebSocket connections and game events.
"""

from flask import Flask, render_template, send_from_directory, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
from game_state import GameManager
import os
import threading

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

# Store active timers for each game
game_timers = {}  # {game_code: Timer}


@app.route('/')
def index():
    """Serve the main HTML page."""
    return send_from_directory('webpage', 'main.html')


@app.route('/audio_files/<path:filename>')
def serve_audio(filename):
    """Serve audio files."""
    return send_from_directory('audio_files', filename)


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
    
    # Send each player their role privately with instructions
    for player_name, player_state in game.players.items():
        if player_state.socket_id and player_state.initial_role:
            role_instructions = game.get_role_instructions(player_state.initial_role)
            socketio.emit('role_assigned', {
                'role': player_state.initial_role,
                'player_name': player_name,
                'instructions': role_instructions
            }, room=player_state.socket_id)
    
    # Notify all players that game started (without revealing roles)
    emit('game_initialized', {
        'message': 'Game has started! Check your role.',
        'game_state': game.to_dict(include_roles=False),
        'center_cards_count': len(game.center_cards)
    }, room=game_code)
    
    # Start night phase
    emit('night_phase_started', {}, room=game_code)
    
    # Notify first player(s) it's their turn
    _notify_current_turn(game, game_code)


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
            role_instructions = game.get_role_instructions(role)
            emit('role_info', {
                'role': role,
                'player_name': player_name,
                'instructions': role_instructions
            })
        else:
            emit('error', {'message': 'Could not retrieve role'})
    else:
        emit('error', {'message': 'Player not found in game'})


@socketio.on('get_center_cards')
def handle_get_center_cards(data):
    """
    Get center cards - DISABLED for gameplay fairness.
    Center cards should not be visible to anyone.
    Expected data: {'game_code': str}
    """
    # Center cards are hidden from everyone to maintain game integrity
    emit('error', {'message': 'Center cards are not visible to anyone'})


# Helper function for night phase management
def _notify_current_turn(game, game_code):
    """Notify players whose turn it is during night phase."""
    current_role = game.get_current_night_role()
    if not current_role:
        # Night phase is over, start voting phase
        game.game_phase = "voting_phase"
        all_player_names = list(game.players.keys())
        socketio.emit('day_phase_started', {'all_players': all_player_names}, room=game_code)
        return
    
    # Get all players with this role
    players_with_role = game.get_players_with_role(current_role)
    
    if not players_with_role:
        # No one has this role, advance to next
        game.advance_night_phase()
        _notify_current_turn(game, game_code)
        return
    
    # Get role duration and audio files
    duration = game.get_role_duration(current_role)
    audio_files = game.get_role_audio_files(current_role)
    
    # Notify players with current role
    for player_name in players_with_role:
        player = game.players[player_name]
        if player.socket_id:
            other_players = game.get_other_players(player_name)
            
            # For roles that see each other, include team info
            team_info = None
            if current_role in ['volkodlak', 'zidar']:
                # Werewolves and Masons see each other
                team_info = [p for p in players_with_role if p != player_name]
            elif current_role == 'služabnik':
                # Minion sees werewolves
                team_info = game.get_players_with_role('volkodlak')
            
            socketio.emit('your_turn', {
                'role': current_role,
                'other_players': other_players,
                'team_info': team_info,
                'duration': duration,
                'audio_files': audio_files
            }, room=player.socket_id)
    
    # Notify all other players to wait (also send timer and audio)
    for player_name, player in game.players.items():
        if player_name not in players_with_role and player.socket_id:
            socketio.emit('wait_turn', {
                'message': f'Počakaj, {current_role} je na potezi...',
                'duration': duration,
                'audio_files': audio_files
            }, room=player.socket_id)
    
    # Cancel any existing timer for this game
    if game_code in game_timers:
        game_timers[game_code].cancel()
    
    # Set up auto-advance timer
    def auto_advance():
        """Auto-advance to next role after timer expires."""
        with app.app_context():
            game_instance = game_manager.get_game(game_code)
            if game_instance and game_instance.game_phase == "night_phase":
                # Advance to next role
                game_instance.advance_night_phase()
                _notify_current_turn(game_instance, game_code)
    
    # Start timer
    timer = threading.Timer(duration, auto_advance)
    timer.start()
    game_timers[game_code] = timer


# Night action handlers
@socketio.on('night_action_complete')
def handle_night_action_complete(data):
    """
    Player has completed their night action (optional - timer will auto-advance).
    Players can still complete actions early, but the phase won't advance until timer expires.
    Expected data: {'game_code': str, 'player_name': str}
    """
    game_code = data.get('game_code', '').strip().upper()
    player_name = data.get('player_name', '').strip()
    
    game = game_manager.get_game(game_code)
    if not game:
        emit('error', {'message': f'Game {game_code} not found'})
        return
    
    if player_name not in game.players:
        emit('error', {'message': 'Player not found'})
        return
    
    # Mark player as having acted (for tracking, but won't affect phase progression)
    game.mark_player_acted(player_name)
    
    # Send confirmation to player that action was recorded
    emit('action_recorded', {'message': 'Akcija zabeležena'})


@socketio.on('action_dvojnik')
def handle_action_dvojnik(data):
    """
    Dvojnik views another player's role.
    Expected data: {'game_code': str, 'player_name': str, 'target_player': str}
    """
    game_code = data.get('game_code', '').strip().upper()
    player_name = data.get('player_name', '').strip()
    target_player = data.get('target_player', '').strip()
    
    game = game_manager.get_game(game_code)
    if not game:
        emit('error', {'message': f'Game {game_code} not found'})
        return
    
    viewed_role = game.action_dvojnik_view_role(player_name, target_player)
    if not viewed_role:
        emit('error', {'message': 'Could not view role'})
        return
    
    # Check if viewed role has a secondary action
    roles_with_actions = ['videc', 'tat', 'težavnež', 'pijanec']
    has_secondary = viewed_role in roles_with_actions
    
    other_players = game.get_other_players(player_name)
    
    emit('dvojnik_result', {
        'viewed_role': viewed_role,
        'has_secondary_action': has_secondary,
        'other_players': other_players
    })


@socketio.on('action_dvojnik_secondary')
def handle_action_dvojnik_secondary(data):
    """
    Dvojnik performs secondary action based on copied role.
    Expected data: {'game_code': str, 'player_name': str, 'action_type': str, ...}
    """
    game_code = data.get('game_code', '').strip().upper()
    player_name = data.get('player_name', '').strip()
    action_type = data.get('action_type', '').strip()
    
    game = game_manager.get_game(game_code)
    if not game:
        emit('error', {'message': f'Game {game_code} not found'})
        return
    
    if action_type == 'videc_player':
        target_player = data.get('target_player', '').strip()
        role = game.action_videc_view_player(target_player)
        emit('videc_result', {'roles': [role] if role else []})
    elif action_type == 'videc_center':
        indices = data.get('center_indices', [])
        roles = game.action_videc_view_center(indices)
        emit('videc_result', {'roles': roles})
    elif action_type == 'tat':
        target_player = data.get('target_player', '').strip()
        new_role = game.action_tat_switch_role(player_name, target_player)
        emit('tat_result', {'new_role': new_role})
    elif action_type == 'težavnež':
        player1 = data.get('player1', '').strip()
        player2 = data.get('player2', '').strip()
        success = game.action_tezavnez_switch_cards(player1, player2)
        if success:
            emit('tezavnez_result', {'player1': player1, 'player2': player2})
    elif action_type == 'pijanec':
        center_index = data.get('center_index', 0)
        success = game.action_pijanec_switch_with_center(player_name, center_index)
        if success:
            emit('pijanec_result', {'success': True})


@socketio.on('action_videc')
def handle_action_videc(data):
    """
    Videc (Seer) views a player's role or center cards.
    Expected data: {'game_code': str, 'player_name': str, 'action_type': str, ...}
    """
    game_code = data.get('game_code', '').strip().upper()
    player_name = data.get('player_name', '').strip()
    action_type = data.get('action_type', '').strip()
    
    game = game_manager.get_game(game_code)
    if not game:
        emit('error', {'message': f'Game {game_code} not found'})
        return
    
    if action_type == 'player':
        target_player = data.get('target_player', '').strip()
        role = game.action_videc_view_player(target_player)
        emit('videc_result', {'roles': [role] if role else []})
    elif action_type == 'center':
        indices = data.get('center_indices', [])
        roles = game.action_videc_view_center(indices)
        emit('videc_result', {'roles': roles})


@socketio.on('action_tat')
def handle_action_tat(data):
    """
    Tat (Robber) switches roles with another player.
    Expected data: {'game_code': str, 'player_name': str, 'target_player': str}
    """
    game_code = data.get('game_code', '').strip().upper()
    player_name = data.get('player_name', '').strip()
    target_player = data.get('target_player', '').strip()
    
    game = game_manager.get_game(game_code)
    if not game:
        emit('error', {'message': f'Game {game_code} not found'})
        return
    
    new_role = game.action_tat_switch_role(player_name, target_player)
    if new_role:
        emit('tat_result', {'new_role': new_role})
    else:
        emit('error', {'message': 'Could not switch roles'})


@socketio.on('action_tezavnez')
def handle_action_tezavnez(data):
    """
    Težavnež (Troublemaker) switches two other players' cards.
    Expected data: {'game_code': str, 'player_name': str, 'player1': str, 'player2': str}
    """
    game_code = data.get('game_code', '').strip().upper()
    player_name = data.get('player_name', '').strip()
    player1 = data.get('player1', '').strip()
    player2 = data.get('player2', '').strip()
    
    game = game_manager.get_game(game_code)
    if not game:
        emit('error', {'message': f'Game {game_code} not found'})
        return
    
    success = game.action_tezavnez_switch_cards(player1, player2)
    if success:
        emit('tezavnez_result', {'player1': player1, 'player2': player2})
    else:
        emit('error', {'message': 'Could not switch cards'})


@socketio.on('action_pijanec')
def handle_action_pijanec(data):
    """
    Pijanec (Drunk) switches their card with a center card.
    Expected data: {'game_code': str, 'player_name': str, 'center_index': int}
    """
    game_code = data.get('game_code', '').strip().upper()
    player_name = data.get('player_name', '').strip()
    center_index = data.get('center_index', 0)
    
    game = game_manager.get_game(game_code)
    if not game:
        emit('error', {'message': f'Game {game_code} not found'})
        return
    
    success = game.action_pijanec_switch_with_center(player_name, center_index)
    if success:
        emit('pijanec_result', {'success': True})
    else:
        emit('error', {'message': 'Could not switch with center'})


@socketio.on('action_nespecznez')
def handle_action_nespecznez(data):
    """
    Nespečnež (Insomniac) views their own current role.
    Expected data: {'game_code': str, 'player_name': str}
    """
    game_code = data.get('game_code', '').strip().upper()
    player_name = data.get('player_name', '').strip()
    
    game = game_manager.get_game(game_code)
    if not game:
        emit('error', {'message': f'Game {game_code} not found'})
        return
    
    current_role = game.action_nespecznez_view_own_role(player_name)
    if current_role:
        emit('nespecznez_result', {'current_role': current_role})
    else:
        emit('error', {'message': 'Could not view role'})


@socketio.on('submit_vote')
def handle_submit_vote(data):
    """
    Player submits their vote for who they think is the werewolf.
    Expected data: {'game_code': str, 'player_name': str, 'voted_for': str}
    """
    game_code = data.get('game_code', '').strip().upper()
    player_name = data.get('player_name', '').strip()
    voted_for = data.get('voted_for', '').strip()
    
    game = game_manager.get_game(game_code)
    if not game:
        emit('error', {'message': f'Game {game_code} not found'})
        return
    
    success, message = game.submit_vote(player_name, voted_for)
    if not success:
        emit('error', {'message': message})
        return
    
    # Confirm vote received to this player
    emit('vote_received', {'message': 'Vote recorded'})
    
    # Check if all players have voted
    if game.all_votes_submitted():
        # All votes are in, send results to everyone
        votes = game.get_votes()
        socketio.emit('voting_complete', {'votes': votes}, room=game_code)


@socketio.on('request_end_game')
def handle_request_end_game(data):
    """
    Request to end the game and show all roles.
    Expected data: {'game_code': str}
    """
    game_code = data.get('game_code', '').strip().upper()
    
    game = game_manager.get_game(game_code)
    if not game:
        emit('error', {'message': f'Game {game_code} not found'})
        return
    
    end_data = game.end_game()
    
    # Broadcast to all players
    socketio.emit('game_ended', end_data, room=game_code)


if __name__ == '__main__':
    print("Starting One Night Werewolf Server...")
    print("Server will be available at: http://localhost:5000")
    print("Press Ctrl+C to stop the server")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
