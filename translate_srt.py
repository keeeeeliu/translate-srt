#!/usr/bin/env python3
"""
Translate an English .srt subtitle file into Mandarin Chinese using the
DeepL API.

Setup
-----
1. Get a DeepL API key (Free or Pro):
       https://www.deepl.com/pro-api

2. Install dependencies:
       pip install deepl srt

3. Set your API key:
       export DEEPL_API_KEY="..."

Usage
-----
    python translate_srt.py input.srt
    python translate_srt.py input.srt -o output.zh.srt
    python translate_srt.py input.srt --target ZH-HANS   # Simplified (default)
    python translate_srt.py input.srt --target ZH-HANT   # Traditional
"""

import argparse # Command-Line Argument Parser. Turn terminal input into structured data. 
import os # Let's get your program to talk to the OS: environment variables, file paths, etc. 
import re # Regular Expressions. Tools for pattern matching in text: find or replace based on patterns rather than exact strings. 
import sys # System or interpreter interface. Access to things tied to Python runtime itself 

import deepl
import srt

# DeepL occasionally appends a stray language label such as "简体中文（大陆）"
# ("Simplified Chinese (Mainland)") to a translated cue. Match the label with
# either full-width （）or half-width () parentheses, plus any surrounding
# whitespace, so we can strip it out of the final subtitles.
LANGUAGE_LABEL_RE = re.compile(r"\s*简体中文\s*[（(]\s*大陆\s*[)）]\s*") # Build a pattern that matches the stray. 

# How many cues to send to DeepL per request. DeepL accepts a list of strings
# and returns them in the same order, so batching just keeps the request count
# (and latency) down. DeepL recommends up to 50 texts per call.
BATCH_SIZE = 50


def translate_batch(translator, texts, target_lang):
    """Translate a list of subtitle strings, returning a list of the same length.

    DeepL preserves both order and count for list input, so the result stays
    aligned with the source cues without any extra bookkeeping.
    """
    results = translator.translate_text(
        texts,
        source_lang="EN",
        target_lang=target_lang,
        # Subtitles are short standalone lines; keep DeepL from collapsing the
        # line breaks we rely on for multi-line cues.
        split_sentences="nonewlines",
    )
    return [r.text for r in results]


def strip_language_label(text):
    """Remove a stray "简体中文（大陆）" language label from a translated cue."""
    return LANGUAGE_LABEL_RE.sub("", text).strip() # Use that pattern to delete the label from the translated text. 
  # LANGUAGE_LABEL_RE.sub("", text) find the lable pattern anywhere in text and substitue it with ""
  # .strip() remove any leftover whitespace from the start/end of the result
  
def translate_srt(input_path, output_path, api_key, target_lang, batch_size):
    # Read and parse the source subtitles.
    with open(input_path, "r", encoding="utf-8-sig") as f: # Where's the file for reading. The with auto closes when done. 
        subtitles = list(srt.parse(f.read())) # srt.parse() turn one whole big string into subtitle objects, each with an index, start time, end time, and content. 
        # After this line, subtitles is a list of objects, e.g. [Subtitle(index=1, start=..., content="Hello"), ...]
    if not subtitles:
        sys.exit(f"No subtitles found in {input_path!r}.") # Stop the program immediately and print an error.  It's a clean way to bail out when something's wrong. 

    translator = deepl.Translator(api_key)

    # Keep cues separate so timestamps stay perfectly aligned.
    texts = [sub.content for sub in subtitles]

    print(f"Translating {len(texts)} subtitle cues -> {target_lang} ...")
    translated = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]
        print(f"  cues {start + 1}-{start + len(batch)} of {len(texts)}")
        translated.extend(translate_batch(translator, batch, target_lang))

    if len(translated) != len(subtitles):
        sys.exit(
            f"Translation count mismatch: got {len(translated)} for "
            f"{len(subtitles)} cues. Aborting to avoid misaligned timing."
        )

    # Write the translated text back into each cue, preserving index + timing.
    # Strip any stray language label DeepL may have appended along the way.
    for sub, text in zip(subtitles, translated):
        sub.content = strip_language_label(text)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(srt.compose(subtitles))

    print(f"Saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Translate an English .srt file into Mandarin via DeepL."
    )
    parser.add_argument("input", help="Path to the English .srt file")
    parser.add_argument(
        "-o", "--output",
        help="Output path (default: <input> with .zh.srt suffix)",
    )
    parser.add_argument(
        "--target",
        default="ZH-HANS",
        help='DeepL target language code (default: "ZH-HANS" for Simplified '
             'Chinese; use "ZH-HANT" for Traditional Chinese)',
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help=f"Number of cues per API request (default: {BATCH_SIZE})",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("DEEPL_API_KEY"), #Reads the environment variable I exported. os.environ is a dictionary of all environment variables. 
        help="DeepL API key (defaults to the DEEPL_API_KEY environment variable)",
    )
    args = parser.parse_args()

    if not args.api_key: # argparse creates it automatically from the argument name you registered.
        sys.exit(
            "No API key found. Set DEEPL_API_KEY or pass --api-key.\n"
            "Get a key at https://www.deepl.com/pro-api"
        )

    if not os.path.isfile(args.input): #Checks whether the input file actually exists before trying to translate it 
        sys.exit(f"Input file not found: {args.input!r}")

    output_path = args.output
    if not output_path:
        base = args.input[:-4] if args.input.lower().endswith(".srt") else args.input
        output_path = f"{base}.zh.srt"

    translate_srt(
        args.input, output_path, args.api_key,
        args.target, args.batch_size,
    )


if __name__ == "__main__":
    main()
