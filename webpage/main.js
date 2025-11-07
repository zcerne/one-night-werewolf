class Player {
    constructor(name) {
        this.name = name;
        this.initialCard = null;
        this.currentCard = null; // Initially same as initial card
    }

    // Method to change current card (for game mechanics)
    setCurrentCard(card) {
        this.currentCard = card;
    }

    // Get player info as object
    getInfo() {
        return {
            name: this.name,
            initialCard: this.initialCard,
            currentCard: this.currentCard
        };
    }
}

class Game {
    constructor() {
        this.players = [];
        this.characters_in_game = [];
        this.centerCards = [];
        this.gameInitialized = false;
        this.availableCharacters = [
            "dvojnik", "volkodlak", "služabnik", "zidar", "videc",
            "tat", "težavnež", "pijanec", "nespečnež", "lovec",
            "nesrečnik", "meščan"
        ];
        this.characterLimits = [1, 2, 1, 2, 1, 1, 1, 1, 1, 1, 1, 3]; // Max count for each character
    }

    // Add a player to the game
    addPlayer(name) {
        const player = new Player(name);
        this.players.push(player);
        return player;
    }

    addCardInGame(character) {
        // Validate character exists
        const characterIndex = this.availableCharacters.indexOf(character);
        if (characterIndex === -1) {
            throw new Error(`Character "${character}" not found in available characters`);
        }

        // Check character limit
        const currentCount = this.characters_in_game.filter(card => card === character).length;
        const maxCount = this.characterLimits[characterIndex];
        if (currentCount >= maxCount) {
            throw new Error(`Cannot add "${character}". Maximum ${maxCount} allowed, currently have ${currentCount}`);
        }

        // Add character to game
        this.characters_in_game.push(character);
        return this.characters_in_game.length;
    }

    // Remove a player by name
    removePlayer(playerName) {
        this.players = this.players.filter(player => player.name !== playerName);
    }

    // Get all players info
    getAllPlayersInfo() {
        return this.players.map(player => player.getInfo());
    }

    // Get player by name
    getPlayer(playerName) {
        return this.players.find(player => player.name === playerName);
    }

    // Reset all players' current cards to initial cards
    resetGame() {
        this.players.forEach(player => {
            player.currentCard = player.initialCard;
        });
    }

    // Get center cards info
    getCenterCards() {
        return this.centerCards;
    }

    // Check if game is initialized
    isInitialized() {
        return this.gameInitialized;
    }

    initializeGame() {
        const numPlayers = this.players.length;

        // Validate player count (One Night Werewolf typically supports 3-7 players)
        if (numPlayers < 3 || numPlayers > 7) {
            throw new Error('One Night Werewolf requires 3-7 players');
        }

        // Calculate total cards needed: players + 3 center cards
        const totalCardsNeeded = numPlayers + 3;

        // Create a pool of available cards respecting character limits
        const cardPool = this.characters_in_game;
        // Shuffle the card pool
        for (let i = cardPool.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [cardPool[i], cardPool[j]] = [cardPool[j], cardPool[i]];
        }
        // Assign cards to players (first n cards)
        for (let i = 0; i < numPlayers; i++) {
            this.players[i].initialCard = cardPool[i];
            this.players[i].currentCard = cardPool[i];
        }

        // Place remaining 3 cards in center
        this.centerCards = cardPool.slice(numPlayers);

        this.gameInitialized = true;

        return {
            playerCards: this.players.map(p => ({ name: p.name, card: p.initialCard })),
            centerCards: this.centerCards
        };
    }
}







