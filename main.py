import random
import os
import subprocess
import tempfile
import threading
import tkinter as tk
from tkinter import messagebox
from mido import MidiFile, MidiTrack, Message, MetaMessage
from pydub import AudioSegment

# Chord formulas in semitones relative to the tonic.
chord_formulas = {
    "I": [0, 4, 7],
    "ii": [2, 5, 9],
    "iii": [4, 7, 11],
    "IV": [5, 9, 12],
    "V": [7, 11, 14],
    "vi": [9, 12, 16],
    "vii°": [11, 14, 17],
    "#II": [3, 7, 10]
}

# Mapping for TTS: roman numeral → number words.
roman_to_number = {
    "I": "one",
    "ii": "two",
    "iii": "three",
    "IV": "four",
    "V": "five",
    "vi": "six",
    "vii°": "seven",
    "#II": "sharp two"
}

# Additional chord choices (the first chord will always be "I")
additional_chords = ["ii", "iii", "IV", "V", "vi", "vii°", "#II"]

# All 12 possible root keys (using sharp notation) with their tonic MIDI note numbers.
possible_roots = {
    "C": 60,
    "C#": 61,
    "D": 62,
    "D#": 63,
    "E": 64,
    "F": 65,
    "F#": 66,
    "G": 67,
    "G#": 68,
    "A": 69,
    "A#": 70,
    "B": 71
}

def generate_progression(prog_length=None):
    """Generate a progression that always starts with I and adds (prog_length - 1) additional chords."""
    if prog_length is None:
        prog_length = random.randint(2, 4)
    else:
        prog_length = int(prog_length)
    if prog_length < 1:
        prog_length = 1
    if prog_length == 1:
        return ["I"]
    additional = random.sample(additional_chords, prog_length - 1)
    return ["I"] + additional

def get_chord_notes(tonic, roman):
    offsets = chord_formulas[roman]
    return [tonic + offset for offset in offsets]

def apply_inversion(chord, inversion):
    if inversion == 0:
        return chord
    elif inversion == 1:
        return [chord[1], chord[2], chord[0] + 12]
    elif inversion == 2:
        return [chord[2], chord[0] + 12, chord[1] + 12]

def choose_best_voicing(tonic, roman, target_avg):
    base = get_chord_notes(tonic, roman)
    best_voicing = None
    best_diff = float('inf')
    for inversion in [0, 1, 2]:
        voicing = apply_inversion(base, inversion)
        for octave_shift in [0, -12]:
            candidate = [note + octave_shift for note in voicing]
            avg_candidate = sum(candidate) / len(candidate)
            diff = abs(avg_candidate - target_avg)
            if diff < best_diff:
                best_diff = diff
                best_voicing = candidate
    return best_voicing

def create_midi_for_progression(progression, tonic, chord_duration_ticks=960, gap_ticks=240, rep_gap_ticks=960):
    mid = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    mid.tracks.append(track)
    track.append(MetaMessage('set_tempo', tempo=1000000, time=0))
    I_chord = get_chord_notes(tonic, "I")
    target_avg = sum(I_chord) / len(I_chord)
    voicings = []
    for roman in progression:
        if roman == "I":
            voicing = I_chord
        else:
            voicing = choose_best_voicing(tonic, roman, target_avg)
        voicings.append(voicing)
    for rep in range(2):
        for idx, roman in enumerate(progression):
            voicing = voicings[idx]
            for note in voicing:
                track.append(Message('note_on', note=note, velocity=100, time=0))
            for i, note in enumerate(voicing):
                track.append(Message('note_off', note=note, velocity=0, time=chord_duration_ticks if i == 0 else 0))
            if idx < len(progression) - 1:
                track.append(MetaMessage('marker', text='gap', time=gap_ticks))
        if rep < 1:
            track.append(MetaMessage('marker', text='rep_gap', time=rep_gap_ticks))
    return mid

def generate_tts(text, filename):
    subprocess.run(["say", "-o", filename, text], check=True)

def generate_audio(prog_length, num_progressions, output_filename):
    final_audio = AudioSegment.empty()
    soundfont = "FluidR3_GM.sf2"  # Update path if necessary.
    pause_between_prog_and_tts = AudioSegment.silent(duration=300)
    end_pause = AudioSegment.silent(duration=1000)
    with tempfile.TemporaryDirectory() as tmpdir:
        for i in range(num_progressions):
            key_name, tonic = random.choice(list(possible_roots.items()))
            progression = generate_progression(prog_length)
            tts_text = " to ".join(roman_to_number[ch] for ch in progression)
            print(f"Progression in key {key_name}: {tts_text}")
            midi_filename = os.path.join(tmpdir, f"temp_{i}.mid")
            wav_filename = os.path.join(tmpdir, f"temp_{i}.wav")
            tts_filename = os.path.join(tmpdir, f"tts_{i}.aiff")
            midi = create_midi_for_progression(progression, tonic)
            midi.save(midi_filename)
            subprocess.run(["fluidsynth", "-ni", soundfont, midi_filename, "-F", wav_filename, "-r", "44100"], check=True)
            chord_audio = AudioSegment.from_file(wav_filename, format="wav")
            generate_tts(tts_text, tts_filename)
            tts_audio = AudioSegment.from_file(tts_filename, format="aiff")
            tts_audio = tts_audio.apply_gain(-6)
            section = chord_audio + pause_between_prog_and_tts + tts_audio + end_pause
            final_audio += section

    base, ext = os.path.splitext(output_filename)
    if ext.lower() == '.mp3':
        final_audio.export(output_filename, format="mp3")
        print(f"Final audio saved as {output_filename}")
    else:
        final_audio.export(output_filename, format="wav")
        print(f"Final audio saved as {output_filename}")
        # Also export to MP3
        mp3_filename = base + ".mp3"
        final_audio.export(mp3_filename, format="mp3")
        print(f"Also exported as {mp3_filename}")

def run_gui():
    root = tk.Tk()
    root.title("Chord Progression Generator")

    tk.Label(root, text="Progression Length (chords per progression):").grid(row=0, column=0, sticky="w", padx=5, pady=5)
    prog_length_entry = tk.Entry(root)
    prog_length_entry.insert(0, "3")
    prog_length_entry.grid(row=0, column=1, padx=5, pady=5)

    tk.Label(root, text="Number of Progressions:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
    num_progressions_entry = tk.Entry(root)
    num_progressions_entry.insert(0, "3")
    num_progressions_entry.grid(row=1, column=1, padx=5, pady=5)

    tk.Label(root, text="Output Filename (wav or mp3):").grid(row=2, column=0, sticky="w", padx=5, pady=5)
    output_filename_entry = tk.Entry(root)
    output_filename_entry.insert(0, "chord_progressions.wav")
    output_filename_entry.grid(row=2, column=1, padx=5, pady=5)

    status_label = tk.Label(root, text="")
    status_label.grid(row=4, column=0, columnspan=2, padx=5, pady=5)

    def generate():
        try:
            prog_length = int(prog_length_entry.get())
            num_progressions = int(num_progressions_entry.get())
            output_filename = output_filename_entry.get().strip()
            if not output_filename:
                raise ValueError("Output filename cannot be empty")
        except ValueError as e:
            messagebox.showerror("Input error", str(e))
            return

        status_label.config(text="Generating...")
        def run_generation():
            try:
                generate_audio(prog_length, num_progressions, output_filename)
                status_label.config(text=f"Done! Saved as {output_filename}")
            except Exception as e:
                status_label.config(text="Error during generation")
                messagebox.showerror("Error", str(e))
        threading.Thread(target=run_generation).start()

    generate_button = tk.Button(root, text="Generate", command=generate)
    generate_button.grid(row=3, column=0, columnspan=2, padx=5, pady=5)

    root.mainloop()

if __name__ == '__main__':
    run_gui()
