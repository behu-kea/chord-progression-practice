import random
import os
import subprocess
import tempfile
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


def generate_progression():
    """Generate a progression that always starts with I and adds 1–3 additional chords."""
    prog_length = random.randint(2, 4)  # Total chords between 2 and 4.
    additional = random.sample(additional_chords, prog_length - 1)
    return ["I"] + additional


def get_chord_notes(tonic, roman):
    """Compute chord note MIDI numbers from the tonic and chord formula."""
    offsets = chord_formulas[roman]
    return [tonic + offset for offset in offsets]


def apply_inversion(chord, inversion):
    """
    Apply the given inversion to the chord.
    Inversion 0: no change.
    Inversion 1: move the first note up one octave.
    Inversion 2: move the first two notes up one octave.
    """
    if inversion == 0:
        return chord
    elif inversion == 1:
        return [chord[1], chord[2], chord[0] + 12]
    elif inversion == 2:
        return [chord[2], chord[0] + 12, chord[1] + 12]


def choose_best_voicing(tonic, roman, target_avg):
    """
    For the given chord (other than I), try each inversion (0, 1, 2)
    and also consider shifting the resulting voicing down an octave.
    Return the candidate whose average pitch is closest to target_avg.
    """
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
    """
    Create a MIDI file for the given progression (using ticks_per_beat=480).
    Tempo is set to 60 BPM (1 beat = 1 second).
    The progression is played twice.

    For chords other than I, choose the voicing (from all inversions and a possible octave drop)
    whose average pitch is closest to the I chord in root position.
    """
    mid = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    mid.tracks.append(track)

    # Set tempo: 60 BPM → 1,000,000 microseconds per beat.
    track.append(MetaMessage('set_tempo', tempo=1000000, time=0))

    # Compute target average from I chord in root position.
    I_chord = get_chord_notes(tonic, "I")
    target_avg = sum(I_chord) / len(I_chord)

    # Pre-calculate best voicings for each chord in the progression.
    voicings = []
    for roman in progression:
        if roman == "I":
            voicing = I_chord  # Use root position for I
        else:
            voicing = choose_best_voicing(tonic, roman, target_avg)
        voicings.append(voicing)

    # Play the progression twice.
    for rep in range(2):
        for idx, roman in enumerate(progression):
            voicing = voicings[idx]
            # Turn on all chord notes.
            for note in voicing:
                track.append(Message('note_on', note=note, velocity=100, time=0))
            # Hold chord for chord_duration_ticks.
            for i, note in enumerate(voicing):
                track.append(Message('note_off', note=note, velocity=0, time=chord_duration_ticks if i == 0 else 0))
            # Add gap only if this is not the last chord in the repetition.
            if idx < len(progression) - 1:
                track.append(MetaMessage('marker', text='gap', time=gap_ticks))
        # Add a longer gap between the two repetitions.
        if rep < 1:
            track.append(MetaMessage('marker', text='rep_gap', time=rep_gap_ticks))
    return mid


def generate_tts(text, filename):
    """Generate TTS audio using macOS’s 'say' command (output as AIFF)."""
    subprocess.run(["say", "-o", filename, text], check=True)


def main():
    final_audio = AudioSegment.empty()
    num_progressions = 3  # Maximum three progressions.
    soundfont = "FluidR3_GM.sf2"  # Update path if necessary.

    # Define pauses.
    pause_between_prog_and_tts = AudioSegment.silent(duration=300)  # 300 ms before TTS
    end_pause = AudioSegment.silent(duration=1000)  # 1-second pause at the end

    # Use a temporary directory for all intermediate files.
    with tempfile.TemporaryDirectory() as tmpdir:
        for i in range(num_progressions):
            # Choose a random root key from all 12 keys.
            key_name, tonic = random.choice(list(possible_roots.items()))
            progression = generate_progression()
            tts_text = " to ".join(roman_to_number[ch] for ch in progression)
            print(f"Progression in key {key_name}: {tts_text}")

            # Define file paths within the temporary directory.
            midi_filename = os.path.join(tmpdir, f"temp_{i}.mid")
            wav_filename = os.path.join(tmpdir, f"temp_{i}.wav")
            tts_filename = os.path.join(tmpdir, f"tts_{i}.aiff")

            # Create and save MIDI file.
            midi = create_midi_for_progression(progression, tonic)
            midi.save(midi_filename)

            # Render the MIDI file to WAV using FluidSynth.
            subprocess.run(["fluidsynth", "-ni", soundfont, midi_filename, "-F", wav_filename, "-r", "44100"],
                           check=True)

            chord_audio = AudioSegment.from_file(wav_filename, format="wav")

            # Generate TTS audio (only the numbers, no extra words).
            generate_tts(tts_text, tts_filename)
            tts_audio = AudioSegment.from_file(tts_filename, format="aiff")
            # Lower the TTS volume by 6 dB.
            tts_audio = tts_audio.apply_gain(-6)

            # Concatenate: chord progression, short pause, TTS announcement, then end pause.
            section = chord_audio + pause_between_prog_and_tts + tts_audio + end_pause
            final_audio += section

        # Export the final audio file.
        final_audio.export("chord_progressions.wav", format="wav")
        print("Final audio saved as chord_progressions.wav")
        # All intermediate files in tmpdir are automatically removed here.


if __name__ == '__main__':
    main()
