"""
Game state management for One Night Werewolf multiplayer game.
Handles game creation, player management, and role distribution.
"""

import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


# Night phase instructions for each role
ROLE_INSTRUCTIONS = {
    "dvojnik": "Ko si na potezi poglej karto drugega igralca. To je tvoja nova vloga. Če ima tvoja vloga nočno akcijo jo opravi zdaj. Če je tvoja vloga Služabnik ostani buden in poišči volkodlake.",
    "volkodlak": "Ko si na potezi se spoglej se z drugimi volkodlaki.",
    "služabnik": "Ko si na potezi poišči volkodlake, ki se razkrijejo",
    "zidar": "Ko si na potezi pogledaj druge zidarje.",
    "videc": "Ko si na potezi lahko pogledaš eno karto drugega igralca ali dve karti na sredini.",
    "tat": "Ko si na potezi lahko svojo karto zamenjaš z drugo karto in pogledaš svojo novo karto.",
    "težavnež": "Ko si na potezi lahko zamenjaš karti dveh drugih igralcev.",
    "pijanec": "Ko si na potezi zamenjaj svojo karto s karto iz sredine.",
    "nespečnež":"Ko si na potezi poglej svojo karto.",
    "dvojnik_nespečnež":"Na potezi si zadnji. Ko si na potezi poglej svojo karto.",
    "lovec":None,
    "nesrečnik": None,  # Tanner has no night action
    "meščan": None  # Villager has no night action
}

# Night phase order (roles wake up in this order)
NIGHT_PHASE_ORDER = [
    "dvojnik",
    "volkodlak",
    "služabnik",
    "zidar",
    "videc",
    "tat",
    "težavnež",
    "pijanec",
    "nespečnež",
    "dvojnik_nespečnež"  # Special case: doppelganger who copied insomniac
]

# Role durations in seconds (fixed time for each role's turn)
ROLE_DURATIONS = {
    "dvojnik": 15,
    "volkodlak": 15,
    "služabnik": 15,
    "zidar": 15,
    "videc": 15,
    "tat": 15,
    "težavnež": 15,
    "pijanec": 15,
    "nespečnež": 15,
    "dvojnik_nespečnež": 15,
    "lovec": 0,
    "nesrečnik": 0,
    "meščan": 0
}

# Audio files for each role
ROLE_AUDIO_FILES = {
    "dvojnik": {
        "start": "audio_files/dvojnik.wav",
        "end": "audio_files/dvojnik_konec.wav"
    },
    "volkodlak": {
        "start": "audio_files/volkodlak.wav",
        "end": "audio_files/volkodlak_konec.wav"
    },
    "služabnik": {
        "start": "audio_files/sluzabnik.wav",
        "end": "audio_files/sluzabnik_konec.wav"
    },
    "zidar": {
        "start": "audio_files/zidar.wav",
        "end": "audio_files/zidar_konec.wav"
    },
    "videc": {
        "start": "audio_files/videc.wav",
        "end": "audio_files/videc_konec.wav"
    },
    "tat": {
        "start": "audio_files/tat.wav",
        "end": "audio_files/tat_konec.wav"
    },
    "težavnež": {
        "start": "audio_files/tezavnez.wav",
        "end": "audio_files/tezavnez_konec.wav"
    },
    "pijanec": {
        "start": "audio_files/pijanec.wav",
        "end": "audio_files/pijanec_konec.wav"
    },
    "nespečnež": {
        "start": "audio_files/nespecnez.wav",
        "end": "audio_files/nespecnez_konec.wav"
    },
    "dvojnik_nespečnež": {
        "start": "audio_files/dvojnik_nespecnez.wav",
        "end": "audio_files/dvojnik_nespecnez_konec.wav"
    }
}


@dataclass
class PlayerState:
    """Represents a single player's state in the game."""
    name: str
    initial_role: Optional[str] = None
    current_role: Optional[str] = None
    ready: bool = False
    socket_id: Optional[str] = None
    has_acted: bool = False  # Track if player has completed their night action
    doppelganger_role: Optional[str] = None  # If doppelganger, what role they copied
    
    def to_dict(self) -> Dict:
        """Convert player state to dictionary (without revealing roles)."""
        return {
            "name": self.name,
            "ready": self.ready
        }
    
    def to_dict_with_role(self) -> Dict:
        """Convert player state to dictionary including role info."""
        return {
            "name": self.name,
            "initial_role": self.initial_role,
            "current_role": self.current_role,
            "ready": self.ready
        }


class GameState:
    """Represents the state of a single game instance."""
    
    # Available characters and their limits
    AVAILABLE_CHARACTERS = [
        "dvojnik", "volkodlak", "služabnik", "zidar", "videc",
        "tat", "težavnež", "pijanec", "nespečnež", "lovec",
        "nesrečnik", "meščan"
    ]
    CHARACTER_LIMITS = [1, 2, 1, 2, 1, 1, 1, 1, 1, 1, 1, 3]
    
    def __init__(self, game_code: str, host_name: str):
        """Initialize a new game."""
        self.game_code = game_code
        self.host_name = host_name
        self.players: Dict[str, PlayerState] = {}
        self.num_players: Optional[int] = None
        self.characters_in_game: List[str] = []
        self.center_cards: List[str] = []
        self.initial_center_cards: List[str] = []  # Store starting center cards
        self.game_phase: str = "setup"  # setup, character_selection, ready, initialized, night_phase, day_phase, voting_phase, ended
        self.initialized: bool = False
        self.current_role_index: int = 0  # Track which role's turn it is during night phase
        self.night_phase_roles: List[str] = []  # Actual roles in play during night phase
        self.votes: Dict[str, str] = {}  # Map of player_name -> voted_for_player_name
        
    def add_player(self, player_name: str, socket_id: Optional[str] = None) -> Tuple[bool, str]:
        """
        Add a player to the game.
        Returns: (success: bool, message: str)
        """
        if player_name in self.players:
            return False, "Player name already exists in this game"
        
        if self.initialized:
            return False, "Game has already started"
        
        if self.num_players and len(self.players) >= self.num_players:
            return False, f"Game is full ({self.num_players} players)"
        
        self.players[player_name] = PlayerState(name=player_name, socket_id=socket_id)
        return True, f"Player {player_name} joined successfully"
    
    def remove_player(self, player_name: str) -> Tuple[bool, str]:
        """Remove a player from the game."""
        if player_name not in self.players:
            return False, "Player not found"
        
        if self.initialized:
            return False, "Cannot remove player after game has started"
        
        del self.players[player_name]
        return True, f"Player {player_name} removed"
    
    def set_player_count(self, num_players: int) -> Tuple[bool, str]:
        """Set the expected number of players."""
        if num_players < 3 or num_players > 7:
            return False, "Number of players must be between 3 and 7"
        
        if self.initialized:
            return False, "Cannot change player count after game has started"
        
        self.num_players = num_players
        self.game_phase = "character_selection"
        return True, f"Player count set to {num_players}"
    
    def add_character(self, character: str) -> Tuple[bool, str]:
        """
        Add a character to the game.
        Returns: (success: bool, message: str)
        """
        if character not in self.AVAILABLE_CHARACTERS:
            return False, f"Character '{character}' not found"
        
        if self.num_players is None:
            return False, "Player count must be set first"
        
        total_needed = self.num_players + 3
        if len(self.characters_in_game) >= total_needed:
            return False, f"Already have {total_needed} characters"
        
        # Check character limit
        char_index = self.AVAILABLE_CHARACTERS.index(character)
        current_count = self.characters_in_game.count(character)
        max_count = self.CHARACTER_LIMITS[char_index]
        
        if current_count >= max_count:
            return False, f"Cannot add '{character}'. Maximum {max_count} allowed"
        
        self.characters_in_game.append(character)
        
        # Check if we have enough characters
        if len(self.characters_in_game) == total_needed:
            self.game_phase = "ready"
        
        return True, f"Character '{character}' added"
    
    def clear_characters(self) -> Tuple[bool, str]:
        """Clear all selected characters."""
        if self.initialized:
            return False, "Cannot clear characters after game has started"
        
        self.characters_in_game = []
        self.game_phase = "character_selection"
        return True, "All characters cleared"
    
    def initialize_game(self) -> Tuple[bool, str]:
        """
        Initialize the game by distributing roles to players and center.
        Returns: (success: bool, message: str)
        """
        if self.initialized:
            return False, "Game already initialized"
        
        if self.num_players is None:
            return False, "Player count not set"
        
        if len(self.players) != self.num_players:
            return False, f"Need {self.num_players} players, but have {len(self.players)}"
        
        if len(self.characters_in_game) != self.num_players + 3:
            return False, f"Need {self.num_players + 3} characters"
        
        # Shuffle characters
        shuffled_characters = self.characters_in_game.copy()
        random.shuffle(shuffled_characters)
        
        # Assign roles to players
        player_names = list(self.players.keys())
        for i, player_name in enumerate(player_names):
            role = shuffled_characters[i]
            self.players[player_name].initial_role = role
            self.players[player_name].current_role = role
        
        # Assign remaining 3 cards to center
        self.center_cards = shuffled_characters[self.num_players:]
        self.initial_center_cards = self.center_cards.copy()  # Store initial state
        
        self.initialized = True
        self.game_phase = "night_phase"
        
        # Build list of roles that will act during night phase (in order)
        self._build_night_phase_order()
        
        return True, "Game initialized successfully"
    
    def _build_night_phase_order(self):
        """Build the ordered list of roles that will act during night phase."""
        self.night_phase_roles = []
        # Get all roles from players (not center cards)
        player_roles = [p.initial_role for p in self.players.values()]
        
        # Add roles in the correct order if they exist in the game
        for role in NIGHT_PHASE_ORDER:
            if role in player_roles:
                self.night_phase_roles.append(role)
        
        self.current_role_index = 0
    
    def get_player_role(self, player_name: str) -> Optional[str]:
        """Get a specific player's initial role."""
        if player_name not in self.players:
            return None
        return self.players[player_name].initial_role
    
    def get_role_instructions(self, role: str) -> Optional[str]:
        """Get night phase instructions for a specific role."""
        return ROLE_INSTRUCTIONS.get(role)
    
    def get_role_duration(self, role: str) -> int:
        """Get the duration in seconds for a specific role."""
        return ROLE_DURATIONS.get(role, 30)
    
    def get_role_audio_files(self, role: str) -> Optional[Dict[str, str]]:
        """Get the audio file paths for a specific role."""
        return ROLE_AUDIO_FILES.get(role)
    
    def get_center_cards(self) -> List[str]:
        """Get the center cards."""
        return self.center_cards.copy()
    
    def get_players_info(self, include_roles: bool = False) -> List[Dict]:
        """Get information about all players."""
        if include_roles:
            return [player.to_dict_with_role() for player in self.players.values()]
        return [player.to_dict() for player in self.players.values()]
    
    def get_current_night_role(self) -> Optional[str]:
        """Get the current role whose turn it is during night phase."""
        if self.game_phase != "night_phase":
            return None
        if self.current_role_index >= len(self.night_phase_roles):
            return None
        return self.night_phase_roles[self.current_role_index]
    
    def get_players_with_role(self, role: str) -> List[str]:
        """Get list of player names who have a specific initial role."""
        return [name for name, player in self.players.items() if player.initial_role == role]
    
    def get_other_players(self, player_name: str) -> List[str]:
        """Get list of all other player names (excluding the given player)."""
        return [name for name in self.players.keys() if name != player_name]
    
    def advance_night_phase(self) -> Tuple[bool, Optional[str]]:
        """
        Advance to the next role in night phase.
        Returns: (is_night_complete: bool, next_role: Optional[str])
        """
        if self.game_phase != "night_phase":
            return False, None
        
        self.current_role_index += 1
        
        if self.current_role_index >= len(self.night_phase_roles):
            # Night phase is complete, move to voting phase
            self.game_phase = "voting_phase"
            return True, None
        
        return False, self.night_phase_roles[self.current_role_index]
    
    def mark_player_acted(self, player_name: str):
        """Mark that a player has completed their night action."""
        if player_name in self.players:
            self.players[player_name].has_acted = True
    
    # Role action methods
    
    def action_dvojnik_view_role(self, player_name: str, target_name: str) -> Optional[str]:
        """Doppelganger views another player's role and copies it."""
        if target_name not in self.players:
            return None
        
        target_role = self.players[target_name].initial_role
        self.players[player_name].doppelganger_role = target_role
        # Doppelganger's current role becomes the copied role
        self.players[player_name].current_role = target_role
        
        return target_role
    
    def action_videc_view_player(self, target_name: str) -> Optional[str]:
        """Seer views another player's current role."""
        if target_name not in self.players:
            return None
        return self.players[target_name].current_role
    
    def action_videc_view_center(self, card_indices: List[int]) -> List[str]:
        """Seer views center cards (up to 2)."""
        result = []
        for idx in card_indices:
            if 0 <= idx < len(self.center_cards):
                result.append(self.center_cards[idx])
        return result
    
    def action_tat_switch_role(self, player_name: str, target_name: str) -> Optional[str]:
        """Robber switches roles with another player and learns their new role."""
        if target_name not in self.players or player_name not in self.players:
            return None
        
        # Swap current roles
        player_role = self.players[player_name].current_role
        target_role = self.players[target_name].current_role
        
        self.players[player_name].current_role = target_role
        self.players[target_name].current_role = player_role
        
        # Return the robber's new role
        return target_role
    
    def action_tezavnez_switch_cards(self, player1_name: str, player2_name: str) -> bool:
        """Troublemaker switches cards between two other players."""
        if player1_name not in self.players or player2_name not in self.players:
            return False
        
        # Swap current roles
        role1 = self.players[player1_name].current_role
        role2 = self.players[player2_name].current_role
        
        self.players[player1_name].current_role = role2
        self.players[player2_name].current_role = role1
        
        return True
    
    def action_pijanec_switch_with_center(self, player_name: str, center_index: int) -> bool:
        """Drunk switches their card with a center card (doesn't see new role)."""
        if player_name not in self.players:
            return False
        if center_index < 0 or center_index >= len(self.center_cards):
            return False
        
        # Swap player's role with center card
        player_role = self.players[player_name].current_role
        center_role = self.center_cards[center_index]
        
        if player_role is None:
            return False
        
        self.players[player_name].current_role = center_role
        self.center_cards[center_index] = player_role
        
        return True
    
    def action_nespecznez_view_own_role(self, player_name: str) -> Optional[str]:
        """Insomniac views their own current role (may have changed)."""
        if player_name not in self.players:
            return None
        return self.players[player_name].current_role
    
    def submit_vote(self, player_name: str, voted_for: str) -> Tuple[bool, str]:
        """
        Record a player's vote.
        Returns: (success: bool, message: str)
        """
        if self.game_phase != "voting_phase":
            return False, "Not in voting phase"
        
        if player_name not in self.players:
            return False, "Player not found"
        
        if voted_for not in self.players:
            return False, "Voted player not found"
        
        self.votes[player_name] = voted_for
        return True, "Vote recorded"
    
    def all_votes_submitted(self) -> bool:
        """Check if all players have submitted their votes."""
        return len(self.votes) == len(self.players)
    
    def get_votes(self) -> Dict[str, str]:
        """Get all votes."""
        return self.votes.copy()
    
    def end_game(self) -> Dict:
        """End the game and return all role information."""
        self.game_phase = "ended"
        
        result = {
            "players": {},
            "center_cards": self.center_cards.copy(),
            "initial_center_cards": self.initial_center_cards.copy()
        }
        
        for name, player in self.players.items():
            result["players"][name] = {
                "initial_role": player.initial_role,
                "current_role": player.current_role
            }
        
        return result
    
    def to_dict(self, include_roles: bool = False) -> Dict:
        """Convert game state to dictionary."""
        data = {
            "game_code": self.game_code,
            "host_name": self.host_name,
            "num_players": self.num_players,
            "players": self.get_players_info(include_roles=include_roles),
            "characters_in_game": self.characters_in_game.copy(),
            "game_phase": self.game_phase,
            "initialized": self.initialized,
            "players_count": len(self.players)
        }
        
        if include_roles and self.initialized:
            data["center_cards"] = self.center_cards.copy()
        
        return data


class GameManager:
    """Manages multiple game instances."""
    
    def __init__(self):
        """Initialize the game manager."""
        self.games: Dict[str, GameState] = {}
    
    def generate_game_code(self) -> str:
        """Generate a unique 5-letter game code."""
        import string
        while True:
            code = ''.join(random.choices(string.ascii_uppercase, k=5))
            if code not in self.games:
                return code
    
    def create_game(self, host_name: str) -> Tuple[str, GameState]:
        """
        Create a new game.
        Returns: (game_code, game_state)
        """
        game_code = self.generate_game_code()
        game = GameState(game_code, host_name)
        game.add_player(host_name)
        self.games[game_code] = game
        return game_code, game
    
    def get_game(self, game_code: str) -> Optional[GameState]:
        """Get a game by its code."""
        return self.games.get(game_code)
    
    def remove_game(self, game_code: str) -> bool:
        """Remove a game from the manager."""
        if game_code in self.games:
            del self.games[game_code]
            return True
        return False
    
    def get_all_games(self) -> List[str]:
        """Get all active game codes."""
        return list(self.games.keys())


# Test script for game initialization
if __name__ == "__main__":
    print("=== One Night Werewolf - Game Initialization Test ===\n")
    
    # Create game manager
    manager = GameManager()
    
    # Create a new game
    game_code, game = manager.create_game("Alice")
    print(f"Game created with code: {game_code}")
    print(f"Host: {game.host_name}\n")
    
    # Add players
    players = ["Bob", "Charlie", "Diana", "Eve"]
    for player_name in players:
        success, message = game.add_player(player_name)
        print(f"Add {player_name}: {message}")
    
    print(f"\nTotal players: {len(game.players)}")
    
    # Set player count
    num_players = 5
    success, message = game.set_player_count(num_players)
    print(f"\n{message}")
    
    # Add characters
    print(f"\nAdding {num_players + 3} characters:")
    characters_to_add = ["volkodlak", "volkodlak", "videc", "služabnik", 
                         "zidar", "tat", "meščan", "pijanec"]
    
    for char in characters_to_add:
        success, message = game.add_character(char)
        print(f"  {message}")
    
    print(f"\nCharacters in game: {game.characters_in_game}")
    
    # Initialize game
    print("\n" + "="*50)
    success, message = game.initialize_game()
    print(f"Initialize game: {message}\n")
    
    if success:
        # Show each player's role
        print("Player Roles:")
        print("-" * 50)
        for player_name in game.players.keys():
            role = game.get_player_role(player_name)
            print(f"  {player_name}: {role}")
        
        # Show center cards
        print("\nCenter Cards:")
        print("-" * 50)
        for i, card in enumerate(game.get_center_cards(), 1):
            print(f"  Card {i}: {card}")
        
        # Show game state
        print("\n" + "="*50)
        print("Game State Summary:")
        print("-" * 50)
        game_dict = game.to_dict(include_roles=True)
        print(f"Game Code: {game_dict['game_code']}")
        print(f"Host: {game_dict['host_name']}")
        print(f"Phase: {game_dict['game_phase']}")
        print(f"Players: {game_dict['players_count']}/{game_dict['num_players']}")
        print(f"Initialized: {game_dict['initialized']}")
