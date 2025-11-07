"""
Game state management for One Night Werewolf multiplayer game.
Handles game creation, player management, and role distribution.
"""

import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class PlayerState:
    """Represents a single player's state in the game."""
    name: str
    initial_role: Optional[str] = None
    current_role: Optional[str] = None
    ready: bool = False
    socket_id: Optional[str] = None
    
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
        self.game_phase: str = "setup"  # setup, character_selection, ready, initialized
        self.initialized: bool = False
        
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
        
        self.initialized = True
        self.game_phase = "initialized"
        
        return True, "Game initialized successfully"
    
    def get_player_role(self, player_name: str) -> Optional[str]:
        """Get a specific player's initial role."""
        if player_name not in self.players:
            return None
        return self.players[player_name].initial_role
    
    def get_center_cards(self) -> List[str]:
        """Get the center cards."""
        return self.center_cards.copy()
    
    def get_players_info(self, include_roles: bool = False) -> List[Dict]:
        """Get information about all players."""
        if include_roles:
            return [player.to_dict_with_role() for player in self.players.values()]
        return [player.to_dict() for player in self.players.values()]
    
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
