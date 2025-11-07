# Agent Guidelines for Werewolf Game Project

## Commands
- **Run**: `python main.py`
- **Test**: `python -m pytest` (no tests exist yet)
- **Test Single**: `python -m pytest tests/test_file.py::TestClass::test_method`
- **Type Check**: `python -m pyright` (basic mode configured)
- **Install**: `pip install -r requirements.txt`
- **System Deps**: `sudo apt install ffmpeg` (for audio processing)

## Code Style
- **Language**: Python 3.12 with pydub, reportlab, pillow dependencies
- **Imports**: Absolute imports, grouped: stdlib → third-party → local
- **Naming**: snake_case vars/functions, PascalCase classes, UPPER_CASE constants
- **Types**: Use type hints for params/returns (pyright configured)
- **Formatting**: 4 spaces indent, max 88 chars/line
- **Error Handling**: try/except blocks, descriptive exceptions
- **Docstrings**: Triple quotes for functions/classes
- **Comments**: Minimal and explanatory

## Project Structure
- Game logic in classes with clear responsibilities
- Slovenian variable names for game-specific terms
- Separate audio handling from game logic
- Webpage component in `webpage/` directory (HTML/JS/CSS)