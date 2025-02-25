# Chord Progression Trainer

This Python script generates random chord progressions, plays them twice with a short delay in between, and announces the chord numbers using text-to-speech. The goal is to help train your ear to recognize chord progressions in different keys with varied inversions.

## Features

- Generates random chord progressions that always start with the I chord.
- Uses all 12 root keys (C, C#, D, etc.).
- Picks inversions that keep the chord progression within a close frequency range.
- Plays each progression twice, with a longer delay between repetitions.
- Uses macOS's built-in `say` command for text-to-speech.
- Exports a `.wav` file with the chord progressions and spoken numbers.

## Requirements

### Install Dependencies

```bash
pip install mido python-rtmidi pydub
```

### Install FluidSynth

#### macOS (via Homebrew)
```bash
brew install fluidsynth
```

#### Linux (Debian/Ubuntu)
```bash
sudo apt install fluidsynth
```

#### Windows
Download and install FluidSynth from [https://www.fluidsynth.org](https://www.fluidsynth.org)

### SoundFont
Make sure you have a valid SoundFont file (e.g., `FluidR3_GM.sf2`). Place it in the working directory or update the script with the correct path.

## Usage

1. Run the script:

```bash
python main.py
```

2. The script will generate a file named `chord_progressions.wav` containing three progressions with their corresponding spoken chord numbers.

## Example Output

- You will hear a chord progression like: **I - IV - V** played in a chosen key.
- The progression is repeated after a slight pause.
- Then, a voice will announce: _"one to four to five"_.

## Customization

- Modify the `num_progressions` variable to generate more or fewer progressions.
- Adjust `rep_gap_ticks` to change the delay between repetitions.
- Modify the `apply_gain(-6)` in the script to adjust the TTS volume.

## ChatGPT
All code was generated by ChatGPT: https://chatgpt.com/share/67a90220-d264-8008-9295-4ef57879d334


