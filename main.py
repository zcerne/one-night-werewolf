from pydub import AudioSegment
from pydub.silence import detect_nonsilent
import os
possible_characters = ["dvojnik", "volkodlak", "služabnik", "zidar", "videc", "tat", "težavnež", "pijanec", "nespečnež", "lovec", "nesrečnik", "meščan"]
possible_number_of_characters = [1,2,1,2,1,1,1,1,1,1,1,3]
file_names = ["dvojnik", "volkodlak", "sluzabnik", "zidar", "videc", "tat", "tezavnez", "pijanec", "nespecnez"]
audio_path = "/home/ziga/Nextcloud/programi/igre/werewolf/audio_files/"
class GameMusic:
    def __init__(self, number_of_players) -> None:
        self.characters_in_game_ids_list = []
        self.n_of_players = number_of_players
        self.combined_audio = AudioSegment.empty()
        pass

    def add_character(self, char_id) -> None:
        self.characters_in_game_ids_list.append(char_id)

    def add_full_audio(self):
        set_of_audio_file_ids = set(self.characters_in_game_ids_list)
        remove_ids = []
        for id in set_of_audio_file_ids:
            if id > 8:
                remove_ids.append(id)
        for r_id in remove_ids:
            set_of_audio_file_ids.remove(r_id)
        list_of_audio_file_ids = sorted(list(set_of_audio_file_ids))
        for id in list_of_audio_file_ids:
            audio_file_name = file_names[id]
            audio_file_path = os.path.join(audio_path, audio_file_name + ".wav")
            audio_segment = AudioSegment.from_file(audio_file_path)

            self.combined_audio += audio_segment
            if id == 0 and 2 in list_of_audio_file_ids: # check if dvojnik is in game
                audio_file_path = os.path.join(audio_path, "dvojnik_minion.wav")
                audio_segment = AudioSegment.from_file(audio_file_path)
                self.combined_audio += audio_segment

            # ad 10 seconds of quietness
            self.combined_audio += AudioSegment.silent(duration=10000)

            
            audio_end_file_path = os.path.join(audio_path, audio_file_name + "_konec.wav")
            audio_end_segment = AudioSegment.from_file(audio_end_file_path)
            self.combined_audio += audio_end_segment

        if 0 in list_of_audio_file_ids and 8 in list_of_audio_file_ids:
            audio_file_path = os.path.join(audio_path, "dvojnik_nespecnez.wav")
            audio_segment = AudioSegment.from_file(audio_file_path)
            self.combined_audio += audio_segment

            audio_end_file_path = os.path.join(audio_path, "dvojnik_nespecnez" + "_konec.wav")
            audio_end_segment = AudioSegment.from_file(audio_end_file_path)
            self.combined_audio += audio_end_segment

        self.combined_audio += AudioSegment.silent(duration=10000)

        # Add background with dynamic volume
        background_file_path = os.path.join(audio_path, "background.wav")
        background = AudioSegment.from_file(background_file_path)
        # Loop background to match length
        background = (background * ((len(self.combined_audio) // len(background)) + 1))[:len(self.combined_audio)]
        # Detect non-silent chunks
        chunks = detect_nonsilent(self.combined_audio, min_silence_len=3000, silence_thresh=-40)
        # Create background_mixed with varying volume
        background_mixed = AudioSegment.silent(len(self.combined_audio))
        current_pos = 0
        for chunk in chunks:
            start, end = chunk
            # Silent before
            if current_pos < start:
                background_mixed = background_mixed.overlay((background[current_pos:start].fade_in(1000).fade_out(1000)), position=current_pos)
            # Non-silent
            background_mixed = background_mixed.overlay(background[start:end].fade_in(500).fade_out(500)-30, position=start)
            current_pos = end
        # Silent after
        if current_pos < len(self.combined_audio):
            background_mixed = background_mixed.overlay((background[current_pos:].fade_in(500).fade_out(500)) - 20, position=current_pos)
        # Add fade in and out
        background_mixed = background_mixed.fade_in(2000).fade_out(2000)
        # Overlay on combined_audio
        self.combined_audio = self.combined_audio.apply_gain(5)

        self.combined_audio = self.combined_audio.overlay(background_mixed)

    def save_combined_audio(self, filename="combined_audio.wav"):
        self.combined_audio.export(filename, format="wav")


    def add_characters(self):
        # Show available characters with IDs
        print(f"Izberi {self.n_of_players + 3} likov.")
        print("Izbiraš lahko med:")
        for i, character in enumerate(possible_characters):
            print(f"{i}: {character}")

        while True:
            try:
                user_input = input("Vnesi ID-je ločene z vejicami (npr. 3,5,4,7,8): ")
                char_ids = [int(id.strip()) for id in user_input.split(',')]

                if len(char_ids) != self.n_of_players + 3:
                    print(f"Napaka: Potrebuješ vnesti točno {self.n_of_players + 3} ID-jev.")
                    continue

                # Validate IDs are within range
                invalid_ids = [id for id in char_ids if id < 0 or id >= len(possible_characters)]
                if invalid_ids:
                    print(f"Napaka: Neveljavni ID-ji znakov: {invalid_ids}")
                    continue

                # check for duplicates. Ignore 1, 3, 11
                valid = True
                for id in list(set(char_ids)):
                    if char_ids.count(id) > possible_number_of_characters[id]:
                        print(f"Napaka, karakter {id} se ponovi prevečkrat")
                        valid = False
                    
                if valid:
                    self.characters_in_game_ids_list = char_ids
                    print("Izbrani znaki:")
                    for char_id in char_ids:
                        print(f"- {possible_characters[char_id]}")
                    break

            except ValueError:
                print("Napaka: Vnesi veljavne številke ločene z vejicami.")
                continue
    

        
if __name__ == "__main__":
    user_input = input("Vnesi število igralcev")
    game = GameMusic(int(user_input))
    game.add_characters()
    game.add_full_audio()
    game.save_combined_audio()

     
