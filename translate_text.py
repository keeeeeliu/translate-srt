#!/usr/bin/env python 3
"""
Translate a plain-text / Markdown file from English into Mandarin via DeepL

Usage:
    export DEEPL_API_KEY="..."
    python translate_text.py input.md
    python translate_text.py input.md -o output.zh.md
    python translate_text.py input.md --target ZH_HANS
"""

import argparse
import os
import re
import sys

import deepl

BATCH_SIZE = 50
LANGUAGE_LABEL_RE = re.compile(r"\s*简体中文\s*[（(]\s*大陆\s*[)）]\s*")

def translate_batch(translator, texts, target_lang):
    """Translate a list of string, returning a list of the same length."""
    results = translator.translate_text(
        texts,
        source_lang="EN",
        target_lang=target_lang,
        split_sentences="nonewlines",
    )
    return [r.text for r in results]

def strip_language_label(text):
    return LANGUAGE_LABEL_RE.sub("", text).strip()

def split_paragraphs(raw):
    """Split on blank lines into paragraphs.
    We keep each run of blank lines as a 'separator' so 
    the original spacing (single vs double blank lines) 
    is restored exactly on putput.
    """
    # Split but KEEP the separators (blank-line runs) via a capturing group
    parts = re.split(r"(\n\s*\n)", raw)
    paragraphs = parts[0::2] # the text chunks
    separators = parts[1::2]  # the blank-line runs between them
    return paragraphs, separators

def translate_file(input_path, output_path, api_key, target_lang, batch_size):
    with open(input_path, "r", encoding="utf-8-sig") as f:
        raw = f.read()

    paragraphs, separators = split_paragraphs(raw)

    # Only translate non-empty paragraphs; remember wehre the blanks were so 
    # we can put empty strings back in the right slots
    indices = [i for i, p in enumerate(paragraphs) if p.strip()]
    texts = [paragraphs[i] for i in indices]

    if not texts:
        sys.exit(f"No translatable text found in {input_path!r}.")

    translator = deepl.Translator(api_key)

    print(f"Translating {len(texts)} paragraphs -> {target_lang}...")
    translated = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start:start+batch_size]
        print(f"  paragraphs {start + 1}-{start+len(batch)} of {len(texts)}")
        translated.extend(translate_batch(translator, batch, target_lang))

    if len(translated) != len(texts):
        sys.exit(
            f"Translation count mistach: got {len(translated)} for "
            f"{len(texts)} paragraphs. Aborting."
        )
    

        # Put translated paragraphs back into their original positions
    for i, text in zip(indices, translated):
        paragraphs[i] = strip_language_label(text)

    # Re-weave paragraphs and the original separators back together
    out = "".join(
        p + (separators[i] if i < len(separators) else "")
        for i, p in enumerate(paragraphs)
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(out)
    
    print(f"Saved: {output_path}")

def main():
    parser = argparse.ArgumentParser(
        description="Translate an English text/Markdown file into Mandarin via DeepL."
    )

    parser.add_argument("input", help="Path to the English .txt/.md file")
    parser.add_argument("-o", "--output", help="Output path (default: <input>,zh.<ext)")
    parser.add_argument("--target", default="ZH-HANS",  help='DeepL target (default "ZH-HANS; use "ZH-HANT" for Traditional)')
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    parser.add_argument("--api-key", default=os.environ.get("DEEPL_API_KEY"))
    args = parser.parse_args()

    if not args.api_key:
        sys.exit("No API Key found. Set DEEPL_API_KEY or pass --api-key.")
    if not os.path.isfile(args.input):
        sys.exit(f"Input file not found: {args.input!r}")

    output_path = args.output
    if not output_path:
        root, ext = os.path.splitext(args.input)
        output_path = f"{root}.zh{ext or '.txt'}"

        translate_file(args.input, output_path, args.api_key, args.target, args.batch_size)
    
    



if __name__ == "__main__":
    main()