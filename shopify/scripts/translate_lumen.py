"""
LUMEN translation script using Claude Sonnet 4.5
- Refined Japanese translation with luxury fashion brand tone
- Batch processing for efficiency
- Prompt caching to reduce cost
"""

import csv
import os
import json
import sys
from anthropic import Anthropic

# Manually load .env (BOM-safe)
def load_env():
    with open('.env', 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip().lstrip('﻿')
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ[k.strip()] = v.strip()

load_env()
client = Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'].strip())

MODEL = 'claude-sonnet-4-5'

# LUMEN brand context (cached)
SYSTEM_PROMPT = """You are a professional Japanese translator specializing in luxury fashion brand content for the affluent Japanese market.

BRAND: Atelier de LUMEN (アトリエ・ド・ルメン)
- Korean luxury minimalist leather handbag brand
- Tone reference: The Row, Lemaire, Loewe, Margaret Howell
- Aesthetic: refined, understated, timeless, quiet luxury
- Target: discerning Japanese customers (30s-50s, fashion-aware)

TRANSLATION RULES:
1. Maintain refined, sophisticated Japanese register (品のある、上品な日本語)
2. Use natural Japanese expressions, NOT literal translations
3. Keep brand name "Atelier de LUMEN" or "LUMEN" in Latin script (do not transliterate)
4. Keep product line names in English (e.g., "ANNEAU FLAP BAG", "PAVE PETIT BAG", "ARC CROSSBODY BAG", "BON BALLON BAG")
5. Keep color names in English (e.g., "SOFT BLACK", "OAK BROWN", "HAY YELLOW")
6. Keep collaboration markers like "[LUMEN X IHNN]" exactly as is
7. For HTML content, preserve all tags exactly (<br>, <strong>, <p>, etc.)
8. For technical specs (sizes, materials), use clear standard Japanese vocabulary
9. Do NOT add explanatory text or notes — translate only

OUTPUT FORMAT:
Return ONLY a valid JSON array of translations in the same order as input. No markdown, no code blocks, no explanation.
Example: ["翻訳1", "翻訳2", "翻訳3"]

If a string contains HTML, preserve all HTML tags. Translate only the visible Japanese text."""

def translate_batch(items, item_type='generic'):
    """Translate a batch of strings. Returns list of translations in same order."""
    user_prompt = f"""Translate these {len(items)} {item_type} strings from English to refined Japanese for LUMEN luxury fashion brand.

Items to translate (numbered for clarity, but return as JSON array):
{json.dumps(items, ensure_ascii=False, indent=2)}

Return ONLY a JSON array of {len(items)} Japanese translations in the same order. No other text."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"}
            }
        ],
        messages=[{"role": "user", "content": user_prompt}]
    )

    text = response.content[0].text.strip()
    # Strip markdown code blocks if present
    if text.startswith('```'):
        text = text.split('\n', 1)[1]
        if text.endswith('```'):
            text = text.rsplit('\n', 1)[0].rsplit('```', 1)[0]
        if text.startswith('json'):
            text = text[4:].strip()

    translations = json.loads(text)
    if len(translations) != len(items):
        raise ValueError(f"Got {len(translations)} translations for {len(items)} items")

    usage = response.usage
    return translations, usage

def main():
    input_path = 'Atelier_de_LUMEN_translations_TITLES_FIXED.csv'
    output_path = 'Atelier_de_LUMEN_translations_PROFESSIONAL_JA.csv'

    if not os.path.exists(input_path):
        print(f"ERROR: {input_path} not found")
        sys.exit(1)

    with open(input_path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.reader(f)
        rows = list(reader)

    header = rows[0]
    data = rows[1:]
    print(f"Total rows: {len(data)}")

    # Identify rows that need translation (PRODUCT body_html with non-empty default content)
    # Step 2 priority: PRODUCT body_html
    targets = []
    for i, row in enumerate(data):
        if len(row) >= 8 and row[0] == 'PRODUCT' and row[2] == 'body_html' and row[3] == 'ja':
            default = row[6].strip()
            if default:  # only translate non-empty
                targets.append((i, default))

    print(f"PRODUCT body_html targets: {len(targets)}")

    if len(sys.argv) > 1 and sys.argv[1] == '--dry-run':
        print("Dry run mode. Showing first 3 targets:")
        for idx, content in targets[:3]:
            print(f"  Row {idx}: {content[:100]}...")
        return

    # Process in batches
    BATCH_SIZE = 5  # smaller batch for body_html (longer content)
    total_input_tokens = 0
    total_output_tokens = 0
    total_cache_read = 0
    total_cache_write = 0

    for batch_start in range(0, len(targets), BATCH_SIZE):
        batch = targets[batch_start:batch_start + BATCH_SIZE]
        items = [content for idx, content in batch]
        try:
            translations, usage = translate_batch(items, 'product description (HTML)')
            for (idx, _), trans in zip(batch, translations):
                data[idx][7] = trans

            total_input_tokens += usage.input_tokens
            total_output_tokens += usage.output_tokens
            total_cache_read += getattr(usage, 'cache_read_input_tokens', 0) or 0
            total_cache_write += getattr(usage, 'cache_creation_input_tokens', 0) or 0

            done = min(batch_start + BATCH_SIZE, len(targets))
            print(f"Progress: {done}/{len(targets)} | tokens used: in={usage.input_tokens}, out={usage.output_tokens}, cache_read={getattr(usage, 'cache_read_input_tokens', 0)}")
        except Exception as e:
            print(f"ERROR at batch {batch_start}: {e}")
            # Save partial progress
            with open(output_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(header)
                writer.writerows(data)
            print(f"Partial progress saved to {output_path}")
            raise

    # Final save
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(data)

    print(f"\nDone. Saved to {output_path}")
    print(f"Total tokens: input={total_input_tokens}, output={total_output_tokens}")
    print(f"Cache: read={total_cache_read}, written={total_cache_write}")

    # Cost estimate (Sonnet 4.5: $3/M in, $15/M out, $0.30/M cache read, $3.75/M cache write)
    cost = (total_input_tokens * 3 + total_output_tokens * 15 + total_cache_read * 0.30 + total_cache_write * 3.75) / 1_000_000
    print(f"Estimated cost: ${cost:.3f}")

if __name__ == '__main__':
    main()
