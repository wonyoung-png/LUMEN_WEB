"""
LUMEN Translation Automation
- Reads .env (Anthropic + Shopify credentials)
- Gets Shopify access token via client_credentials grant
- Fetches translatable resources via Shopify Admin GraphQL API
- Translates with Claude Sonnet 4.5 (luxury tone)
- Updates Shopify directly via translationsRegister mutation
- Fully automated end-to-end
"""

import os
import re
import sys
import csv
import json
import time
import requests
from anthropic import Anthropic

# ---------- Load .env ----------
def load_env(path='.env'):
    if not os.path.exists(path):
        print(f"ERROR: {path} not found")
        sys.exit(1)
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip().lstrip('﻿')
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ[k.strip()] = v.strip()

load_env()

REQUIRED = ['ANTHROPIC_API_KEY', 'SHOPIFY_CLIENT_ID', 'SHOPIFY_CLIENT_SECRET', 'SHOPIFY_STORE']
missing = [k for k in REQUIRED if not os.environ.get(k)]
if missing:
    print(f"ERROR: missing env vars: {missing}")
    sys.exit(1)

ANTHROPIC_KEY = os.environ['ANTHROPIC_API_KEY'].strip()
SHOP_CLIENT_ID = os.environ['SHOPIFY_CLIENT_ID'].strip()
SHOP_CLIENT_SECRET = os.environ['SHOPIFY_CLIENT_SECRET'].strip()
SHOP = os.environ['SHOPIFY_STORE'].strip().replace('.myshopify.com', '')

# ---------- Get Shopify access token ----------
def get_shopify_token():
    """Use client_credentials grant to get access token (24h validity)"""
    url = f"https://{SHOP}.myshopify.com/admin/oauth/access_token"
    data = {
        'grant_type': 'client_credentials',
        'client_id': SHOP_CLIENT_ID,
        'client_secret': SHOP_CLIENT_SECRET
    }
    r = requests.post(url, data=data, timeout=30)
    if r.status_code != 200:
        print(f"  [ERROR] HTTP {r.status_code}: {r.text}")
    r.raise_for_status()
    return r.json()['access_token']

# ---------- Shopify GraphQL ----------
GRAPHQL_URL = None
HEADERS = None

def gql(query, variables=None):
    r = requests.post(GRAPHQL_URL, headers=HEADERS,
                      json={'query': query, 'variables': variables or {}}, timeout=60)
    r.raise_for_status()
    data = r.json()
    if 'errors' in data:
        raise RuntimeError(f"GraphQL errors: {data['errors']}")
    return data['data']

# ---------- Anthropic Translation ----------
client = Anthropic(api_key=ANTHROPIC_KEY)
MODEL = 'claude-sonnet-4-5'

SYSTEM_PROMPT = """You are the LUMEN brand voice copywriter — translating Atelier de LUMEN product copy to Japanese for the intl.atlm.kr Shopify store. Follow `lumen-product-translation` skill v2.3 STRICTLY.

═══════════════════════════════════════════════════════════
v2.3 CRITICAL UPDATES (highest priority)
═══════════════════════════════════════════════════════════
1. MASTER INTRO — copy LITERALLY. No reordering, no particle changes, no period variations.
   Panier:    `バスケットから着想を得た、Panier [model]。緻密なステッチが特徴です。`
2. COLON: ALWAYS half-width `:` (NEVER full-width `：`)
3. MATERIAL COMPOSITION: single space separator
   ✅ `ポリエステル92% スパンデックス8%`  ❌ `ポリエステル92%スパンデックス8%`
4. SAME COLOR VARIATION = 100% identical body. Different material group = 1 line differs only.

═══════════════════════════════════════════════════════════
LUMEN VOICE (most critical — voice trumps everything else)
═══════════════════════════════════════════════════════════
Reference tone: The Row · Lemaire — extreme minimalism, restraint.
- Adjectives: ≤ 1 per sentence
- Don't TALK about craftsmanship; POINT to details
- Bullets: noun-ended (体言止め), single-breath read
- No 私たち/We — only point at objects
- Carry the voice of someone who knows how the bag was made — names details accurately, never claims artisanship

═══════════════════════════════════════════════════════════
FORBIDDEN WORDS (instant failure if any appear)
═══════════════════════════════════════════════════════════
Artisan overload (NEVER use): 職人 / 匠 / 丹念に / 心を込めて / 逸品 / 究極 / 卓越 / クラフトマンシップ / 仕立て上げた
Emotional inflation (NEVER use): 特別な / 美しい / エレガント / 魅力的な / 上品な / 素敵な / 抜群 / 充実
Translation stiffness (NEVER use): 〜することができます / 〜となっています / 〜である / 着用することが可能
Identity dilution: 風呂敷 (use ポジャギ); カウレザー (use 牛革); ライニング (use 裏地)
Bullet enders FORBIDDEN: 〜ます。 / 〜です。 / 〜実現しました / 〜演出します / 〜表現しました / 〜完成させます

═══════════════════════════════════════════════════════════
STANDARD VOCABULARY (use ONLY these)
═══════════════════════════════════════════════════════════
牛革 (NOT カウレザー / 牛皮)        裏地 (NOT ライニング)
ジップポケット (NOT ジッパーポケット)  ジッパー開閉 (for closure mechanism)
保存袋 (NOT ダストバッグ)            ハングタグ (NOT ハングタッグ)
ポジャギ (NOT 風呂敷)                Bojagi (English, capitalized)
型押しテクスチャー (NOT エンボス加工) 緻密な (NOT 精緻 / 精巧 / 精細)
ステッチ (NOT ステッチワーク)        ハードウェア (NOT 金具)
クラシック (NOT クラシカル)          ウエスタン (NOT ウェスタン)
アシンメトリック (NOT アシンメトリー) トゥ (NOT つま先)
着想を得た (NOT インスピレーションを得た) ※ Bojagi 시리즈만 후자 허용
ロゴ刻印 (NOT ロゴ入り)              ベルベットのような (NOT ベルベットのように)
カーフスキン / ヌバックレザー / スエード / マイクロファイバースエード

═══════════════════════════════════════════════════════════
PRODUCT NAMES — ALWAYS LATIN
═══════════════════════════════════════════════════════════
Panier Petit Bag (NEVER パニエプチバッグ)
Boston Small Bag (NEVER ボストンスモールバッグ)
Bojagi Sling Bag (NEVER ポジャギスリングバッグ)
Western Heeled Mules (NEVER ウエスタンヒールミュール)
LUMEN / Atelier de LUMEN / IHNN — Latin only
Artist names (Yeodong Yun etc) — Latin only, NEVER katakana

═══════════════════════════════════════════════════════════
SENTENCE STRUCTURE — INTRO PATTERNS
═══════════════════════════════════════════════════════════
Use one of these for intro:
A. [feature]が特徴の[Product Name]
B. [feature]を施した[Product Name]。
C. [motif]から着想を得た、[Product Name]。

❌ Avoid head-heavy: ...シルエットのProduct Name (acceptable but break with comma if long)

═══════════════════════════════════════════════════════════
BULLET FORMAT
═══════════════════════════════════════════════════════════
Start: <br> -  (with single space)
Ending: 体言止め (noun ending) — NEVER 〜ます。/〜です。
Length: ≤ 25 characters per bullet (JA)
Count: 4-6 bullets, max 7

❌ - フラップが内側に折り込まれ、すっきりとしたシルエットを実現しました。
✅ - フラップが内側に折り込まれた、クリーンなシルエット

═══════════════════════════════════════════════════════════
METAFIELD FORMAT (Product Info / Size)
═══════════════════════════════════════════════════════════
Header: <strong>製品情報</strong> (NEVER 商品詳細)
Header: <strong>サイズ</strong>
Multiplication: × (full-width, NEVER x)
Depth: マチ (for bags, NEVER 奥行)
Pocket count: ×1, ×2 (NEVER 1つ / 一つ)
Colon: ：or : — be consistent
Weight: g (lowercase)
Standard bag template:
<p><strong>製品情報</strong><br>- 牛革 / [composition]<br>- [carry type]<br>- マイクロファイバースエードの裏地<br>- [closure]<br>- メインポケット×1、内側ジップポケット×1、内側スリップポケット×N<br>- バッグ総重量:Ng<br><br><strong>サイズ</strong><br>幅Ncm × マチNcm × 高さNcm<br>(ハンドルドロップ:Ncm)</p>

═══════════════════════════════════════════════════════════
STORAGE/CARE INSTRUCTIONS (fixed format)
═══════════════════════════════════════════════════════════
Bags:    直射日光、湿気、高温を避けてください。品質を保つため、付属の保存袋で保管してください
Shoes:   直射日光と湿気を避けてください。品質を保つため、付属のシューズボックスで保管してください

═══════════════════════════════════════════════════════════
COLLECTION MASTER INTROS (use these exactly)
═══════════════════════════════════════════════════════════
Panier:    バスケットから着想を得た、Panier [model]。緻密なステッチが特徴です。
Bojagi:    ポジャギの結び目にインスピレーションを得た、Bojagi [model]。
Boston:    丸みを帯びたシルエットと立体的なテクスチャーが特徴のBoston [size] Bag。
Mules (Western): 甲を深く包み込むミドルヒールのWestern Heeled Mules。
Mules (Asym):    シャープなトゥラインと非対称カットが特徴のAsymmetric Edge Mules。
Anneau:    リング形状のディテールが特徴のAnneau Flap Bag。
Pave:      モザイク状のステッチが印象的なPave Petit Bag。
Arc:       アーチ型のシルエットが美しいArc Crossbody Bag。
Marron:    栗のシルエットから着想を得たMarron Demi Bag。
Curved:    曲線的なリップディテールのCurved Lip Case。
Pillow:    ふくらみのあるピロー型シルエットのPillow Card Wallet。
Lowe:      クラシックなデザートシルエットのLowe Desert Boots。
Comfort:   快適な履き心地を追求したComfort Loafer。
Woven:     複数のレザーをねじり編み込んだテクスチャーのWoven Leather Belt。

═══════════════════════════════════════════════════════════
COLOR VARIATION RULE — ABSOLUTE
═══════════════════════════════════════════════════════════
Same SKU different colors MUST have 100% identical body. Only color name changes.
Same model with different material (e.g., nubuck vs calfskin): only the material-description line differs; everything else identical.

═══════════════════════════════════════════════════════════
VERB ELEVATION
═══════════════════════════════════════════════════════════
Use: 表現 / 施す / 採用 / 仕立てる (sparingly) / 馴染む (体言)
Avoid: 作る / 使う / 出す / 演出します (use 演出 noun-end)

═══════════════════════════════════════════════════════════
SELF-VERIFICATION before output (5 questions)
═══════════════════════════════════════════════════════════
After translation, copy must answer all 5:
(1) Material? (e.g., 牛革 / ヌバックレザー)
(2) Structure? (e.g., トグル開閉)
(3) Detail? (e.g., 緻密なステッチ)
(4) Carry method? (e.g., ハンドキャリー / ショルダー)
(5) Use? (e.g., デイリー)
If you cannot answer any of these from your output → translation failed, rewrite.

The Row test: Could this copy live on The Row's website without feeling out of place?

═══════════════════════════════════════════════════════════
HTML PRESERVATION
═══════════════════════════════════════════════════════════
Preserve all <br>, <p>, <strong> tags exactly. Fix obvious source errors (missing -, typos like widly→widely, ts→its). No additional tags inserted.

═══════════════════════════════════════════════════════════
LEGACY ORIGINAL CONTEXT (kept for compatibility)
═══════════════════════════════════════════════════════════
You are a professional Japanese translator specializing in luxury fashion brand content for the affluent Japanese market.

BRAND: Atelier de LUMEN (Korean luxury minimalist leather handbag brand)
- Tone reference: The Row, Lemaire, Loewe, Margaret Howell
- Aesthetic: refined, understated, timeless, quiet luxury
- Target: discerning Japanese customers (30s-50s, fashion-aware)

TRANSLATION RULES:
1. Maintain refined, sophisticated Japanese register (品のある、上品な日本語)
2. Use natural Japanese expressions, NOT literal translations
3. Keep brand name "Atelier de LUMEN" or "LUMEN" in Latin script
4. Keep product line names in English (ANNEAU FLAP BAG, ARC CROSSBODY BAG, etc.)
5. Keep color names in English (SOFT BLACK, OAK BROWN, etc.)
6. Keep collaboration markers like "[LUMEN X IHNN]" exactly
7. For HTML content, preserve all tags exactly (<br>, <strong>, <p>, etc.)
8. Use clear standard Japanese for technical specs
9. Use "ポジャギ" (not "ボジャギ") for the Korean word 보자기
10. Verify all kanji are correct (no hallucinated characters)
11. Do NOT add explanatory notes - translate only
12. SENTENCE RHYTHM (critical for lookbook tone): Avoid head-heavy structures where a long modifier ends with the product name. Instead, break the modifier into an independent short sentence, OR lead with the product name as subject.
    BAD:  "○○○からインスピレーションを得たシルエットのBojagi Sling Bag"
    GOOD: "○○○から着想を得た、Bojagi Sling Bag。"
    GOOD: "Bojagi Sling Bag。○○○から着想を得たシルエット。"
13. VERB CHOICE — designer intent over factual statement: Prefer verbs that convey the designer's intent/craftsmanship ("表現しました", "実現しました", "仕上げました") over plain factual verbs ("作られています", "使用しています").
14. Final care/precaution lines MUST end with "ご注意ください" (customer courtesy and closure).
15. Use "着想を得た" or "インスパイアされた" instead of "インスピレーションを得た" (the latter sounds katakana-heavy and less refined).
16. PROPER NAMES — KEEP IN LATIN SCRIPT: All artist, designer, collaborator, brand, and product line names MUST stay in their original Latin/Roman script. Do NOT transliterate to katakana.
    Examples:
    - "Artist Yeodong Yun" → keep as "Artist Yeodong Yun" (NOT "アーティスト ユン・ヨドン")
    - "Yeodong Yun" → keep as "Yeodong Yun"
    - "LUMEN", "IHNN", "Atelier de LUMEN" → always Latin
    - Product line names like "ANNEAU", "BOJAGI", "PAVE", "ARC" → always Latin/uppercase as given
    Korean/Asian artist names in Latin romanization are TREATED AS PROPER NAMES and never transliterated to katakana.

OUTPUT: Return ONLY a valid JSON array of translations in same order as input. No markdown, no code blocks, no explanation."""

def translate_batch(items, item_type='generic'):
    user_prompt = f"""Translate these {len(items)} {item_type} strings from English to refined Japanese for LUMEN luxury fashion brand.

Items:
{json.dumps(items, ensure_ascii=False, indent=2)}

Return ONLY a JSON array of {len(items)} Japanese translations in the same order."""

    resp = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        system=[{
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"}
        }],
        messages=[{"role": "user", "content": user_prompt}]
    )
    text = resp.content[0].text.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1]
        if text.endswith('```'):
            text = text.rsplit('```', 1)[0]
        if text.startswith('json'):
            text = text[4:].strip()
    return json.loads(text), resp.usage

# ---------- Shopify Translation Register ----------
TRANSLATIONS_REMOVE = """
mutation translationsRemove($resourceId: ID!, $translationKeys: [String!]!, $locales: [String!]!) {
  translationsRemove(resourceId: $resourceId, translationKeys: $translationKeys, locales: $locales) {
    translations { key value }
    userErrors { field message }
  }
}
"""

TRANSLATIONS_REGISTER = """
mutation translationsRegister($resourceId: ID!, $translations: [TranslationInput!]!) {
  translationsRegister(resourceId: $resourceId, translations: $translations) {
    userErrors { field message }
    translations { key value }
  }
}
"""

def register_translation(resource_id, key, locale, value, translatable_content_digest):
    return gql(TRANSLATIONS_REGISTER, {
        'resourceId': resource_id,
        'translations': [{
            'key': key,
            'value': value,
            'locale': locale,
            'translatableContentDigest': translatable_content_digest
        }]
    })

# ---------- Workflow ----------
TRANSLATABLE_RESOURCES = """
query translatableResources($resourceType: TranslatableResourceType!, $first: Int!, $after: String) {
  translatableResources(resourceType: $resourceType, first: $first, after: $after) {
    edges {
      cursor
      node {
        resourceId
        translatableContent {
          key
          value
          digest
          locale
        }
        translations(locale: "ja") {
          key
          value
        }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""

def fetch_resources(resource_type, limit=None):
    """Fetch all translatable resources of a type."""
    out = []
    cursor = None
    while True:
        data = gql(TRANSLATABLE_RESOURCES, {
            'resourceType': resource_type,
            'first': 50,
            'after': cursor
        })
        for edge in data['translatableResources']['edges']:
            out.append(edge['node'])
            if limit and len(out) >= limit:
                return out
        info = data['translatableResources']['pageInfo']
        if not info['hasNextPage']:
            break
        cursor = info['endCursor']
    return out

def main():
    global GRAPHQL_URL, HEADERS
    print("Step 1: Getting Shopify access token...")
    token = get_shopify_token()
    print(f"  Token: {token[:15]}... (length {len(token)})")

    GRAPHQL_URL = f"https://{SHOP}.myshopify.com/admin/api/2025-01/graphql.json"
    HEADERS = {
        'X-Shopify-Access-Token': token,
        'Content-Type': 'application/json'
    }

    # Quick health check
    print("Step 2: Connection test...")
    shop = gql("{ shop { name primaryDomain { url } } }")
    print(f"  Connected to: {shop['shop']['name']} ({shop['shop']['primaryDomain']['url']})")

    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        print("Test mode: fetching 3 PRODUCT resources...")
        prods = fetch_resources('PRODUCT', limit=3)
        for p in prods:
            print(f"  Resource: {p['resourceId']}")
            for c in p['translatableContent']:
                if c['key'] in ('title', 'body_html'):
                    print(f"    {c['key']} (en): {c['value'][:60]}...")
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--list':
        # List all PRODUCT resources with title + JA translation status
        print("Fetching ALL PRODUCT resources...")
        prods = fetch_resources('PRODUCT')
        print(f"Total products: {len(prods)}\n")

        with_body = 0
        empty_body = 0
        ja_existing = 0
        ja_missing = 0

        rows = []
        for p in prods:
            title_en = ''
            body_en = ''
            for c in p['translatableContent']:
                if c['key'] == 'title':
                    title_en = c['value'] or ''
                elif c['key'] == 'body_html':
                    body_en = c['value'] or ''

            ja_title = ''
            ja_body = ''
            for t in (p.get('translations') or []):
                if t['key'] == 'title':
                    ja_title = t['value'] or ''
                elif t['key'] == 'body_html':
                    ja_body = t['value'] or ''

            has_body = bool(body_en.strip())
            has_ja_body = bool(ja_body.strip())
            if has_body:
                with_body += 1
            else:
                empty_body += 1
            if has_ja_body:
                ja_existing += 1
            else:
                ja_missing += 1

            rows.append({
                'id': p['resourceId'].split('/')[-1],
                'title': title_en[:60],
                'body_chars': len(body_en),
                'ja_title_chars': len(ja_title),
                'ja_body_chars': len(ja_body),
            })

        # Save report to UTF-8 file (avoid Windows cp949 console issues)
        out_path = 'product_translation_report.txt'
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(f"Total products: {len(prods)}\n")
            f.write(f"With body_html: {with_body}, empty body_html: {empty_body}\n")
            f.write(f"With JA body: {ja_existing}, missing JA body: {ja_missing}\n\n")
            f.write(f"{'#':>4} {'ID':>14} {'EN_body':>8} {'JA_body':>8}  Title\n")
            f.write("-" * 100 + "\n")
            for i, r in enumerate(rows, 1):
                f.write(f"{i:>4} {r['id']:>14} {r['body_chars']:>8} {r['ja_body_chars']:>8}  {r['title']}\n")

        print(f"Report saved to: {out_path}")
        print(f"With body_html: {with_body} | Empty body: {empty_body}")
        print(f"JA body exists: {ja_existing} | JA body missing: {ja_missing}")
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--phase-ihnn':
        dry_run = '--dry-run' in sys.argv
        preview = '--preview' in sys.argv
        run_phase_filter(
            label='IHNN',
            title_filter=lambda t: 'IHNN' in (t or '').upper(),
            field_keys=['body_html'],
            locale='ja',
            dry_run=dry_run,
            preview=preview,
        )
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--phase-products':
        dry_run = '--dry-run' in sys.argv
        preview = '--preview' in sys.argv
        limit = None
        for i, a in enumerate(sys.argv):
            if a == '--limit' and i+1 < len(sys.argv):
                limit = int(sys.argv[i+1])
        # Default: skip IHNN (already done in --phase-ihnn)
        run_phase_filter(
            label='PRODUCTS',
            title_filter=lambda t: 'IHNN' not in (t or '').upper(),
            field_keys=['body_html'],
            locale='ja',
            dry_run=dry_run,
            preview=preview,
            limit=limit,
        )
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--phase-metafields':
        dry_run = '--dry-run' in sys.argv
        preview = '--preview' in sys.argv
        limit = None
        for i, a in enumerate(sys.argv):
            if a == '--limit' and i+1 < len(sys.argv):
                limit = int(sys.argv[i+1])
        run_phase_metafields(locale='ja', dry_run=dry_run, preview=preview, limit=limit)
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--jp-update-batch':
        # --jp-update-batch [--filter ihnn|all] [--limit N] [--apply]
        apply = '--apply' in sys.argv
        filt = 'all'
        limit = None
        for i, a in enumerate(sys.argv):
            if a == '--filter' and i+1 < len(sys.argv):
                filt = sys.argv[i+1].lower()
            elif a == '--limit' and i+1 < len(sys.argv):
                limit = int(sys.argv[i+1])
        jp_update_batch(filt=filt, limit=limit, apply=apply)
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--jp-update':
        # --jp-update <handle> [--apply]
        if len(sys.argv) < 3:
            print("Usage: --jp-update <handle> [--apply]")
            return
        handle = sys.argv[2]
        apply = '--apply' in sys.argv
        jp_update(handle, apply=apply)
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--jp-revert':
        # --jp-revert <handle>
        if len(sys.argv) < 3:
            print("Usage: --jp-revert <handle>")
            return
        handle = sys.argv[2]
        jp_revert(handle)
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--delete-mo-entry':
        # --delete-mo-entry <type> <handle>
        if len(sys.argv) < 4:
            print("Usage: --delete-mo-entry <type> <handle>")
            return
        t = sys.argv[2]
        h = sys.argv[3]
        e = gql(METAOBJECT_BY_HANDLE_QUERY, {'handle': {'type': t, 'handle': h}})['metaobjectByHandle']
        if not e:
            print(f"Not found: {t}/{h}")
            return
        r = gql("""
        mutation del($id: ID!) {
          metaobjectDelete(id: $id) {
            deletedId
            userErrors { field message }
          }
        }
        """, {'id': e['id']})
        errs = r['metaobjectDelete']['userErrors']
        if errs:
            print(f"[ERROR] {errs}")
        else:
            print(f"[OK] Deleted {t}/{h} ({e['id']})")
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--copy-mo-entry':
        # --copy-mo-entry <src-handle-or-id> <type> <new-handle>
        if len(sys.argv) < 5:
            print("Usage: --copy-mo-entry <src-handle> <type> <new-handle>")
            return
        src = sys.argv[2]
        mtype = sys.argv[3]
        new_handle = sys.argv[4]
        copy_metaobject_entry(src, mtype, new_handle)
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--create-japan-mfdefs':
        create_japan_mfdefs()
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--translate-policy-entries':
        translate_policy_entries()
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--review-panier-plus':
        review_panier_plus()
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--bulk-set-japan-refs':
        apply = '--apply' in sys.argv
        bulk_set_japan_refs(apply=apply)
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--set-japan-refs-tray':
        set_japan_refs_tray()
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--theme-v4':
        theme_v4()
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--publish-mo-entry':
        # --publish-mo-entry <type> <handle>
        if len(sys.argv) < 4:
            print("Usage: --publish-mo-entry <type> <handle>")
            return
        publish_metaobject_entry(sys.argv[2], sys.argv[3])
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--check-mo-entry':
        # --check-mo-entry <type> <handle>
        if len(sys.argv) < 4:
            print("Usage: --check-mo-entry <type> <handle>")
            return
        t = sys.argv[2]
        h = sys.argv[3]
        e = gql(METAOBJECT_BY_HANDLE_QUERY, {'handle': {'type': t, 'handle': h}})['metaobjectByHandle']
        if not e:
            print(f"Not found: {t}/{h}")
            return
        print(f"Resource: {e['id']}")
        print(f"Type: {e['type']}, Handle: {e['handle']}")
        for f in e['fields']:
            v = (f.get('value') or '')[:300]
            print(f"  [{f['key']}] type={f['type']} value: {v}")
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--enable-mo-storefront':
        # --enable-mo-storefront <type>
        if len(sys.argv) < 3:
            print("Usage: --enable-mo-storefront <type>")
            return
        enable_metaobject_storefront_access(sys.argv[2])
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--create-warranty-def':
        create_warranty_def()
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--create-warranty-from-theme':
        create_warranty_from_theme()
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--prepare-theme-v2':
        prepare_theme_v2()
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--apply-buy-buttons-fix':
        apply_buy_buttons_fix()
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--apply-currency-persistence-fix':
        apply_currency_persistence_fix()
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--fix-theme-handles':
        fix_theme_handles()
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--apply-theme-v2':
        apply_theme_v2()
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--cafe24-auth-url':
        cafe24_auth_url()
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--cafe24-exchange-code':
        if len(sys.argv) < 3:
            print("Usage: --cafe24-exchange-code <code-or-full-url>")
            return
        arg = sys.argv[2]
        # Auto-extract code from URL if a full URL was passed
        if 'code=' in arg:
            arg = arg.split('code=')[1].split('&')[0]
            print(f"[INFO] Extracted code from URL: {arg}")
        cafe24_exchange_code(arg)
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--full-price-table':
        full_price_table()
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--price-compare-report':
        price_compare_report()
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--cafe24-export-prices':
        cafe24_export_prices()
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--export-shopify-prices':
        export_shopify_prices()
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--inspect-japan-pricelist':
        inspect_japan_pricelist()
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--inspect-catalogs':
        inspect_catalogs()
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--inspect-product-prices':
        handle = sys.argv[2] if len(sys.argv) > 2 else 'anneau-flap-bag-hay-yellow'
        inspect_product_prices(handle)
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--enable-presentment-jpy':
        enable_presentment_jpy()
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--enable-japan-jpy':
        enable_japan_jpy()
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--inspect-shop-currency':
        inspect_shop_currency()
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--inspect-markets':
        inspect_markets()
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--inspect-mo-defs':
        inspect_metaobject_definitions()
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--prepare-theme-mod':
        prepare_theme_mod()
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--apply-theme-mod':
        apply_theme_mod()
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--create-jp-details-mf':
        create_jp_details_metafield_definition()
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--remove-translation':
        # --remove-translation <resourceId> <key> [locale]
        if len(sys.argv) < 4:
            print("Usage: --remove-translation <resourceId-or-numeric> <key> [locale=ja]")
            return
        arg = sys.argv[2]
        if arg.startswith('gid://'):
            rid = arg
        elif arg.isdigit():
            # Default to Metafield type for numeric IDs
            rid = f'gid://shopify/Metafield/{arg}'
        else:
            rid = arg
        key = sys.argv[3]
        locale = sys.argv[4] if len(sys.argv) > 4 else 'ja'
        r = gql(TRANSLATIONS_REMOVE, {
            'resourceId': rid,
            'translationKeys': [key],
            'locales': [locale],
        })
        errs = r['translationsRemove']['userErrors']
        if errs:
            print(f"[ERROR] {errs}")
        else:
            removed = r['translationsRemove']['translations']
            print(f"[OK] Removed translation: resource={rid}, key={key}, locale={locale}")
            print(f"     Returned: {removed}")
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--set-jp-desc-from-file':
        # --set-jp-desc-from-file <handle> <filepath>
        if len(sys.argv) < 4:
            print("Usage: --set-jp-desc-from-file <handle> <filepath>")
            return
        handle = sys.argv[2]
        filepath = sys.argv[3]
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        p = gql(PRODUCT_BY_HANDLE, {'handle': handle})['productByHandle']
        if not p:
            print(f"Product not found: {handle}")
            return
        r = gql(METAFIELDS_SET, {
            'metafields': [{
                'ownerId': p['id'],
                'namespace': 'custom',
                'key': 'japan_product_decription',
                'type': 'multi_line_text_field',
                'value': content,
            }]
        })
        errs = r['metafieldsSet']['userErrors']
        if errs:
            print(f"[ERROR] {errs}")
        else:
            print(f"[OK] japan_product_decription set ({len(content)} chars) for {p['title']}")
            print(f"Verify: https://intl.atlm.kr/products/{handle}")
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--check-mf-translation':
        # --check-mf-translation <metafield-id-or-gid>
        if len(sys.argv) < 3:
            print("Usage: --check-mf-translation <metafieldId>")
            return
        arg = sys.argv[2]
        gid = arg if arg.startswith('gid://') else f'gid://shopify/Metafield/{arg}'
        r = gql(METAFIELD_TRANSLATABLE, {'id': gid})
        tr = r.get('translatableResource')
        if not tr:
            print(f"No translatable resource for {gid}")
            return
        print(f"Resource: {tr['resourceId']}")
        print(f"Translatable keys: {[c['key'] for c in tr['translatableContent']]}")
        for c in tr['translatableContent']:
            print(f"  [{c['key']}] EN ({len(c['value'] or '')} chars): {(c['value'] or '')[:120]}")
        print(f"\nJA translations:")
        if not tr.get('translations'):
            print("  (none)")
        for t in tr.get('translations') or []:
            print(f"  [{t['key']}] JA ({len(t['value'] or '')} chars): {(t['value'] or '')[:120]}")
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--test-jp-product':
        if len(sys.argv) < 3:
            print("Usage: --test-jp-product <handle> [--apply]")
            return
        handle = sys.argv[2]
        apply = '--apply' in sys.argv
        test_jp_product(handle, apply=apply)
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--inspect-theme':
        keyword = sys.argv[2] if len(sys.argv) > 2 else 'japan_product_decription'
        inspect_theme(keyword)
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--read-theme-file':
        filename = sys.argv[2] if len(sys.argv) > 2 else 'sections/main-product.liquid'
        read_theme_file(filename)
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--inspect':
        # --inspect <productId-or-handle>
        if len(sys.argv) < 3:
            print("Usage: --inspect <productId or handle>")
            return
        arg = sys.argv[2]
        if arg.startswith('gid://'):
            gid = arg
        elif arg.isdigit():
            gid = f'gid://shopify/Product/{arg}'
        else:
            # treat as handle
            r = gql(PRODUCT_BY_HANDLE, {'handle': arg})
            p = r.get('productByHandle')
            if not p:
                print(f"No product with handle: {arg}")
                return
            gid = p['id']
            print(f"Resolved handle '{arg}' -> {gid}")
        inspect_product(gid)
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--phase-metaobjects':
        dry_run = '--dry-run' in sys.argv
        preview = '--preview' in sys.argv
        limit = None
        for i, a in enumerate(sys.argv):
            if a == '--limit' and i+1 < len(sys.argv):
                limit = int(sys.argv[i+1])
        run_phase_metaobjects(locale='ja', dry_run=dry_run, preview=preview, limit=limit)
        return

    print("Run with --test, --list, or --phase-ihnn [--dry-run] to verify before full execution")


def run_phase_filter(label, title_filter, field_keys, locale='ja', dry_run=False, preview=False, limit=None):
    """Translate matching PRODUCTs and register via translationsRegister."""
    print(f"=== Phase: {label} ===")
    print("Fetching all PRODUCT resources...")
    prods = fetch_resources('PRODUCT')

    # Filter by title; capture existing JA translation for preview
    targets = []
    for p in prods:
        en_title = ''
        for c in p['translatableContent']:
            if c['key'] == 'title':
                en_title = c['value'] or ''
                break
        if not title_filter(en_title):
            continue
        ja_existing_map = {t['key']: t['value'] for t in (p.get('translations') or [])}
        for c in p['translatableContent']:
            if c['key'] in field_keys and (c['value'] or '').strip():
                targets.append({
                    'resource_id': p['resourceId'],
                    'key': c['key'],
                    'value': c['value'],
                    'digest': c['digest'],
                    'en_title': en_title,
                    'ja_old': ja_existing_map.get(c['key'], ''),
                })

    if limit:
        targets = targets[:limit]

    print(f"Targets: {len(targets)}")
    for t in targets[:20]:
        print(f"  - {t['en_title']} | {t['key']} ({len(t['value'])} chars)")
    if len(targets) > 20:
        print(f"  ... and {len(targets)-20} more")

    if dry_run:
        print("[dry-run] No translation. No registration.")
        return

    if not targets:
        print("Nothing to do.")
        return

    if preview:
        # Translate but DO NOT register; write before/after to file
        print(f"[PREVIEW] Translating {len(targets)} items (no Shopify registration)...")
        BATCH_SIZE = 5
        all_translations = []
        total_in = total_out = total_cr = total_cw = 0
        for batch_start in range(0, len(targets), BATCH_SIZE):
            batch = targets[batch_start:batch_start + BATCH_SIZE]
            items = [t['value'] for t in batch]
            translations, usage = translate_batch(items, 'product description (HTML)')
            all_translations.extend(translations)
            total_in += usage.input_tokens
            total_out += usage.output_tokens
            total_cr += getattr(usage, 'cache_read_input_tokens', 0) or 0
            total_cw += getattr(usage, 'cache_creation_input_tokens', 0) or 0
            print(f"  Progress: {min(batch_start+BATCH_SIZE,len(targets))}/{len(targets)}")

        out_path = f'preview_{label.lower()}.txt'
        with open(out_path, 'w', encoding='utf-8') as f:
            for i, (t, ja_new) in enumerate(zip(targets, all_translations), 1):
                f.write(f"=== {i}. {t['en_title']} ({t['key']}) ===\n\n")
                f.write(f"[ENGLISH]\n{t['value']}\n\n")
                f.write(f"[OLD JA (current)]\n{t['ja_old']}\n\n")
                f.write(f"[NEW JA (LUMEN tone)]\n{ja_new}\n\n")
                f.write("=" * 80 + "\n\n")
        cost = (total_in*3 + total_out*15 + total_cr*0.30 + total_cw*3.75) / 1_000_000
        print(f"\n[PREVIEW] Saved to: {out_path}")
        print(f"Tokens: in={total_in} out={total_out} cache_read={total_cr} cache_write={total_cw}")
        print(f"Estimated cost: ${cost:.3f}")
        print("Review the file. If OK, run without --preview to register to Shopify.")
        return

    # Translate in batches of 5 (HTML content is long)
    BATCH_SIZE = 5
    total_in = total_out = total_cr = total_cw = 0
    succeeded = 0
    failed = []

    for batch_start in range(0, len(targets), BATCH_SIZE):
        batch = targets[batch_start:batch_start + BATCH_SIZE]
        items = [t['value'] for t in batch]
        try:
            translations, usage = translate_batch(items, 'product description (HTML)')
        except Exception as e:
            print(f"  [batch {batch_start}] translate_batch failed: {e}")
            failed.extend(batch)
            continue

        total_in += usage.input_tokens
        total_out += usage.output_tokens
        total_cr += getattr(usage, 'cache_read_input_tokens', 0) or 0
        total_cw += getattr(usage, 'cache_creation_input_tokens', 0) or 0

        for t, ja_value in zip(batch, translations):
            try:
                res = register_translation(
                    resource_id=t['resource_id'],
                    key=t['key'],
                    locale=locale,
                    value=ja_value,
                    translatable_content_digest=t['digest'],
                )
                errs = res['translationsRegister']['userErrors']
                if errs:
                    print(f"  [WARN] {t['en_title']} {t['key']}: {errs}")
                    failed.append(t)
                else:
                    succeeded += 1
            except Exception as e:
                print(f"  [ERROR] {t['en_title']} {t['key']}: {e}")
                failed.append(t)

        done = min(batch_start + BATCH_SIZE, len(targets))
        print(f"  Progress: {done}/{len(targets)} | tokens in={usage.input_tokens} out={usage.output_tokens} cache_read={getattr(usage,'cache_read_input_tokens',0)}")

    cost = (total_in*3 + total_out*15 + total_cr*0.30 + total_cw*3.75) / 1_000_000
    print(f"\n=== Done: {label} ===")
    print(f"Succeeded: {succeeded}/{len(targets)} | Failed: {len(failed)}")
    print(f"Tokens: in={total_in} out={total_out} cache_read={total_cr} cache_write={total_cw}")
    print(f"Estimated cost: ${cost:.3f}")
    if failed:
        with open(f'failed_{label.lower()}.json', 'w', encoding='utf-8') as f:
            json.dump([{'id': x['resource_id'], 'key': x['key'], 'title': x['en_title']} for x in failed],
                      f, ensure_ascii=False, indent=2)
        print(f"Failed items saved to failed_{label.lower()}.json")

def is_translatable_metafield_value(v):
    """Heuristic filter: skip JSON/CSS/code/color-name/short metafield values."""
    if not v:
        return False
    s = v.strip()
    if len(s) < 30:
        return False  # too short - likely color name, label, or empty
    # Skip JSON/array/code blobs
    if s.startswith(('{', '[', '/*', '<!--', '<style', '<script')):
        return False
    # Skip if mostly looks like JSON (contains many quoted keys)
    if s.count('":"') > 5 and '{' in s[:100]:
        return False
    # Skip pure URLs
    if s.startswith(('http://', 'https://')) and ' ' not in s:
        return False
    return True


COLOR_NAME_PATTERN = re.compile(r'^[A-Z][A-Z\s\-]{1,30}$')


def run_phase_metafields(locale='ja', dry_run=False, preview=False, limit=None):
    """Translate METAFIELD value fields (PRODUCT DETAILS content)."""
    label = 'METAFIELDS'
    print(f"=== Phase: {label} ===")
    print("Fetching all METAFIELD resources...")
    metas = fetch_resources('METAFIELD')
    print(f"Total METAFIELD resources: {len(metas)}")

    targets = []
    skipped_short = skipped_json = skipped_color = skipped_other = 0
    for m in metas:
        ja_existing_map = {t['key']: t['value'] for t in (m.get('translations') or [])}
        for c in m['translatableContent']:
            if c['key'] != 'value':
                continue
            v = c['value'] or ''
            s = v.strip()
            if not s:
                continue
            if len(s) < 30:
                if COLOR_NAME_PATTERN.match(s):
                    skipped_color += 1
                else:
                    skipped_short += 1
                continue
            if not is_translatable_metafield_value(s):
                skipped_json += 1
                continue
            targets.append({
                'resource_id': m['resourceId'],
                'key': c['key'],
                'value': v,
                'digest': c['digest'],
                'en_title': m['resourceId'].split('/')[-1],
                'ja_old': ja_existing_map.get(c['key'], ''),
            })

    print(f"Skipped: short={skipped_short}, color={skipped_color}, json/code={skipped_json}")
    print(f"Translatable targets: {len(targets)}")

    if limit:
        targets = targets[:limit]

    print(f"Targets: {len(targets)} metafield values")
    if dry_run:
        for t in targets[:30]:
            v = t['value'].replace('\n', ' ')[:80]
            print(f"  - {t['resource_id']} | {len(t['value'])} chars | {v}...")
        print("[dry-run] No translation. No registration.")
        return

    if not targets:
        print("Nothing to do.")
        return

    BATCH_SIZE = 5
    total_in = total_out = total_cr = total_cw = 0
    succeeded = 0
    failed = []
    all_translations = []

    for batch_start in range(0, len(targets), BATCH_SIZE):
        batch = targets[batch_start:batch_start + BATCH_SIZE]
        items = [t['value'] for t in batch]
        try:
            translations, usage = translate_batch(items, 'product metafield (HTML/text)')
        except Exception as e:
            print(f"  [batch {batch_start}] failed: {e}")
            failed.extend(batch)
            continue

        all_translations.extend(translations)
        total_in += usage.input_tokens
        total_out += usage.output_tokens
        total_cr += getattr(usage, 'cache_read_input_tokens', 0) or 0
        total_cw += getattr(usage, 'cache_creation_input_tokens', 0) or 0

        if not preview:
            for t, ja_value in zip(batch, translations):
                try:
                    res = register_translation(
                        resource_id=t['resource_id'],
                        key=t['key'],
                        locale=locale,
                        value=ja_value,
                        translatable_content_digest=t['digest'],
                    )
                    errs = res['translationsRegister']['userErrors']
                    if errs:
                        print(f"  [WARN] {t['resource_id']}: {errs}")
                        failed.append(t)
                    else:
                        succeeded += 1
                except Exception as e:
                    print(f"  [ERROR] {t['resource_id']}: {e}")
                    failed.append(t)

        done = min(batch_start + BATCH_SIZE, len(targets))
        print(f"  Progress: {done}/{len(targets)}")

    cost = (total_in*3 + total_out*15 + total_cr*0.30 + total_cw*3.75) / 1_000_000

    if preview:
        out_path = f'preview_{label.lower()}.txt'
        with open(out_path, 'w', encoding='utf-8') as f:
            for i, (t, ja_new) in enumerate(zip(targets, all_translations), 1):
                f.write(f"=== {i}. {t['resource_id']} ===\n\n")
                f.write(f"[ENGLISH]\n{t['value']}\n\n")
                f.write(f"[OLD JA]\n{t['ja_old']}\n\n")
                f.write(f"[NEW JA (LUMEN tone)]\n{ja_new}\n\n")
                f.write("=" * 80 + "\n\n")
        print(f"\n[PREVIEW] Saved to: {out_path}")

    print(f"\n=== Done: {label} ===")
    print(f"Succeeded: {succeeded}/{len(targets)} | Failed: {len(failed)}")
    print(f"Tokens: in={total_in} out={total_out} cache_read={total_cr} cache_write={total_cw}")
    print(f"Estimated cost: ${cost:.3f}")


THEMES_QUERY = """
{
  themes(first: 20) {
    nodes {
      id
      name
      role
    }
  }
}
"""

THEME_FILES_QUERY = """
query themeFiles($id: ID!, $after: String) {
  theme(id: $id) {
    id
    name
    files(first: 100, after: $after) {
      nodes {
        filename
        body {
          ... on OnlineStoreThemeFileBodyText { content }
          ... on OnlineStoreThemeFileBodyBase64 { contentBase64 }
        }
      }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""


PRODUCT_BY_HANDLE = """
query byHandle($handle: String!) {
  productByHandle(handle: $handle) {
    id
    title
    handle
    descriptionHtml
    metafields(first: 30) {
      edges { node { id namespace key type value } }
    }
  }
}
"""

METAFIELD_TRANSLATABLE = """
query mf($id: ID!) {
  translatableResource(resourceId: $id) {
    resourceId
    translatableContent { key value digest type }
    translations(locale: "ja") { key value }
  }
}
"""

PRODUCT_TRANSLATABLE = """
query pr($id: ID!) {
  translatableResource(resourceId: $id) {
    resourceId
    translatableContent { key value digest type }
    translations(locale: "ja") { key value }
  }
}
"""

METAFIELDS_SET = """
mutation set($metafields: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $metafields) {
    metafields { id namespace key value }
    userErrors { field message }
  }
}
"""


def test_jp_product(handle, apply=False):
    print(f"=== Test JP Product: {handle} ===")
    p = gql(PRODUCT_BY_HANDLE, {'handle': handle})['productByHandle']
    if not p:
        print(f"Product not found by handle: {handle}")
        return
    print(f"Found: {p['title']} ({p['id']})")

    # Find metafields we care about
    mfs = {(e['node']['namespace'], e['node']['key']): e['node'] for e in p['metafields']['edges']}
    japan_mf = mfs.get(('custom', 'japan_product_decription'))
    details_mf = mfs.get(('custom', 'product_details'))

    body_en = p.get('descriptionHtml') or ''
    details_en = (details_mf or {}).get('value') or ''

    print(f"\n[body_html] {len(body_en)} chars")
    print(f"[product_details metafield] {'present' if details_mf else 'MISSING'} ({len(details_en)} chars)")
    print(f"[japan_product_decription metafield] {'present' if japan_mf else 'MISSING'}")

    if not body_en and not details_en:
        print("Nothing to translate.")
        return

    # Translate both
    items = []
    labels = []
    if body_en:
        items.append(body_en)
        labels.append('body')
    if details_en:
        items.append(details_en)
        labels.append('details')

    print(f"\nTranslating {len(items)} items with LUMEN tone...")
    translations, usage = translate_batch(items, 'product description (HTML/text)')
    cost = (usage.input_tokens*3 + usage.output_tokens*15 + (getattr(usage,'cache_read_input_tokens',0) or 0)*0.30 + (getattr(usage,'cache_creation_input_tokens',0) or 0)*3.75) / 1_000_000
    print(f"Cost: ${cost:.4f}")

    body_ja = ''
    details_ja = ''
    for label, t in zip(labels, translations):
        if label == 'body':
            body_ja = t
        elif label == 'details':
            details_ja = t

    out = f'test_jp_{handle}.txt'
    with open(out, 'w', encoding='utf-8') as f:
        f.write(f"Product: {p['title']} ({p['id']})\nHandle: {handle}\n\n")
        if body_en:
            f.write("=== BODY (descriptionHtml) ===\n")
            f.write(f"[ENGLISH]\n{body_en}\n\n")
            f.write(f"[NEW JA — to be written to japan_product_decription metafield]\n{body_ja}\n\n")
        if details_en:
            f.write("=== PRODUCT DETAILS (metafield custom.product_details) ===\n")
            f.write(f"[ENGLISH]\n{details_en}\n\n")
            f.write(f"[NEW JA — to be registered as JA translation of product_details]\n{details_ja}\n\n")
    print(f"Saved preview: {out}")

    if not apply:
        print("\n[PREVIEW ONLY] Run again with --apply to write to Shopify.")
        return

    # Apply to Shopify
    print("\nApplying...")
    # 1. Update japan_product_decription metafield directly
    if body_ja and japan_mf:
        r = gql(METAFIELDS_SET, {
            'metafields': [{
                'ownerId': p['id'],
                'namespace': 'custom',
                'key': 'japan_product_decription',
                'type': 'multi_line_text_field',
                'value': body_ja,
            }]
        })
        errs = r['metafieldsSet']['userErrors']
        if errs:
            print(f"  [ERROR japan_product_decription] {errs}")
        else:
            print(f"  [OK] japan_product_decription updated")

    # 2. Register translation for product_details metafield (locale=ja)
    if details_ja and details_mf:
        # Need digest from translatableResource
        try:
            tr = gql(METAFIELD_TRANSLATABLE, {'id': details_mf['id']})
            digest = None
            for c in (tr['translatableResource'] or {}).get('translatableContent') or []:
                if c['key'] == 'value':
                    digest = c['digest']
                    break
            if digest:
                rr = register_translation(
                    resource_id=details_mf['id'],
                    key='value',
                    locale='ja',
                    value=details_ja,
                    translatable_content_digest=digest,
                )
                errs = rr['translationsRegister']['userErrors']
                if errs:
                    print(f"  [WARN product_details translation] {errs}")
                else:
                    print(f"  [OK] product_details JA translation registered")
            else:
                print(f"  [SKIP] product_details has no translatable digest")
        except Exception as e:
            print(f"  [ERROR product_details] {e}")

    print(f"\nVerify at: https://intl.atlm.kr/products/{handle}")
    print("Open in incognito with Japan/Japanese locale to confirm.")


THEME_FILES_UPSERT = """
mutation upsert($themeId: ID!, $files: [OnlineStoreThemeFilesUpsertFileInput!]!) {
  themeFilesUpsert(themeId: $themeId, files: $files) {
    upsertedThemeFiles { filename }
    userErrors { field message }
  }
}
"""

METAFIELD_DEF_CREATE = """
mutation createDef($definition: MetafieldDefinitionInput!) {
  metafieldDefinitionCreate(definition: $definition) {
    createdDefinition { id name namespace key type { name } }
    userErrors { field message code }
  }
}
"""


def jp_update(handle, apply=False):
    """Translate body + details to LUMEN JA, write to japan_product_decription + japan_product_details metafields."""
    print(f"=== JP Update: {handle} ===")
    p = gql(PRODUCT_BY_HANDLE, {'handle': handle})['productByHandle']
    if not p:
        print(f"Product not found: {handle}")
        return

    print(f"Product: {p['title']} ({p['id']})")

    mfs = {(e['node']['namespace'], e['node']['key']): e['node'] for e in p['metafields']['edges']}
    body_en = p.get('descriptionHtml') or ''
    details_mf = mfs.get(('custom', 'product_details'))
    details_en = (details_mf or {}).get('value') or ''
    japan_desc_mf = mfs.get(('custom', 'japan_product_decription'))
    japan_details_mf = mfs.get(('custom', 'japan_product_details'))

    print(f"  body_html (EN): {len(body_en)} chars")
    print(f"  product_details (EN): {len(details_en)} chars")
    print(f"  japan_product_decription: {'present' if japan_desc_mf else 'will create'}")
    print(f"  japan_product_details: {'present' if japan_details_mf else 'will create'}")

    items = []
    labels = []
    if body_en.strip():
        items.append(body_en)
        labels.append('body')
    if details_en.strip():
        items.append(details_en)
        labels.append('details')

    if not items:
        print("Nothing to translate.")
        return

    print(f"\nTranslating {len(items)} items with LUMEN tone...")
    translations, usage = translate_batch(items, 'product description and details (HTML)')
    cost = (usage.input_tokens*3 + usage.output_tokens*15 + (getattr(usage,'cache_read_input_tokens',0) or 0)*0.30 + (getattr(usage,'cache_creation_input_tokens',0) or 0)*3.75) / 1_000_000
    print(f"Cost: ${cost:.4f}")

    body_ja = ''
    details_ja = ''
    for label, t in zip(labels, translations):
        if label == 'body':
            body_ja = t
        elif label == 'details':
            details_ja = t

    # Save preview + backup of current state
    preview_path = f'jp_preview_{handle}.txt'
    with open(preview_path, 'w', encoding='utf-8') as f:
        f.write(f"Product: {p['title']} ({p['id']})\nHandle: {handle}\n\n")
        if body_en:
            f.write("=== japan_product_decription ===\n")
            f.write(f"[ENGLISH SOURCE]\n{body_en}\n\n")
            f.write(f"[CURRENT JA in metafield]\n{(japan_desc_mf or {}).get('value') or '(none)'}\n\n")
            f.write(f"[NEW LUMEN JA — to be written]\n{body_ja}\n\n")
        if details_en:
            f.write("=== japan_product_details ===\n")
            f.write(f"[ENGLISH SOURCE]\n{details_en}\n\n")
            f.write(f"[CURRENT JA in metafield]\n{(japan_details_mf or {}).get('value') or '(none, will create)'}\n\n")
            f.write(f"[NEW LUMEN JA — to be written]\n{details_ja}\n\n")
    print(f"Saved preview: {preview_path}")

    backup_path = f'jp_backup_{handle}.json'
    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump({
            'handle': handle,
            'product_id': p['id'],
            'japan_product_decription': (japan_desc_mf or {}).get('value') or '',
            'japan_product_details': (japan_details_mf or {}).get('value') or '',
            'had_japan_decription': bool(japan_desc_mf),
            'had_japan_details': bool(japan_details_mf),
        }, f, ensure_ascii=False, indent=2)
    print(f"Saved backup: {backup_path}")

    if not apply:
        print("\n[PREVIEW ONLY] Run again with --apply to write to Shopify.")
        return

    print("\nApplying...")
    metafield_inputs = []
    if body_ja:
        metafield_inputs.append({
            'ownerId': p['id'],
            'namespace': 'custom',
            'key': 'japan_product_decription',
            'type': 'multi_line_text_field',
            'value': body_ja,
        })
    if details_ja:
        metafield_inputs.append({
            'ownerId': p['id'],
            'namespace': 'custom',
            'key': 'japan_product_details',
            'type': 'multi_line_text_field',
            'value': details_ja,
        })

    r = gql(METAFIELDS_SET, {'metafields': metafield_inputs})
    errs = r['metafieldsSet']['userErrors']
    if errs:
        print(f"[ERROR] {errs}")
    else:
        for m in r['metafieldsSet']['metafields']:
            print(f"  [OK] {m['namespace']}.{m['key']} updated ({len(m['value'])} chars)")
    print(f"\nVerify: https://intl.atlm.kr/products/{handle}")
    print(f"Revert: python lumen_auto_translate.py --jp-revert {handle}")


METAOBJECT_DEFINITIONS_QUERY = """
{
  metaobjectDefinitions(first: 50) {
    nodes {
      id
      name
      type
      fieldDefinitions { key name type { name } required }
    }
  }
}
"""


METAOBJECT_BY_TYPE_QUERY = """
query mo($type: String!) {
  metaobjects(type: $type, first: 30) {
    nodes {
      id
      handle
      type
      fields { key value type }
    }
  }
}
"""


METAOBJECT_BY_HANDLE_QUERY = """
query mo($handle: MetaobjectHandleInput!) {
  metaobjectByHandle(handle: $handle) {
    id
    handle
    type
    fields { key value type }
  }
}
"""

METAOBJECT_CREATE = """
mutation create($metaobject: MetaobjectCreateInput!) {
  metaobjectCreate(metaobject: $metaobject) {
    metaobject { id handle type fields { key value } }
    userErrors { field message code }
  }
}
"""

METAOBJECT_DEF_CREATE = """
mutation defCreate($definition: MetaobjectDefinitionCreateInput!) {
  metaobjectDefinitionCreate(definition: $definition) {
    metaobjectDefinition { id type name }
    userErrors { field message code }
  }
}
"""


def copy_metaobject_entry(src_handle, mtype, new_handle):
    """Fetch entry by handle, create new entry with same fields under new handle."""
    print(f"Fetching {mtype}/{src_handle}...")
    src = gql(METAOBJECT_BY_HANDLE_QUERY, {'handle': {'type': mtype, 'handle': src_handle}})['metaobjectByHandle']
    if not src:
        print(f"Source not found: {mtype}/{src_handle}")
        return
    print(f"Source: {src['id']} with {len(src['fields'])} fields")
    fields_input = []
    for f in src['fields']:
        # Skip empty fields
        if f.get('value') is None:
            continue
        fields_input.append({'key': f['key'], 'value': f['value']})

    print(f"Creating {mtype}/{new_handle}...")
    r = gql(METAOBJECT_CREATE, {
        'metaobject': {
            'type': mtype,
            'handle': new_handle,
            'fields': fields_input,
        }
    })
    errs = r['metaobjectCreate']['userErrors']
    if errs:
        already = any('TAKEN' in (e.get('code') or '') for e in errs)
        if already:
            print(f"[OK] Already exists: {mtype}/{new_handle}")
        else:
            print(f"[ERROR] {errs}")
    else:
        m = r['metaobjectCreate']['metaobject']
        print(f"[OK] Created {m['type']}/{m['handle']} -> {m['id']}")


METAOBJECT_DEF_BY_TYPE = """
query def($type: String!) {
  metaobjectDefinitionByType(type: $type) {
    id
    name
    type
    access { storefront }
  }
}
"""

METAOBJECT_DEF_UPDATE = """
mutation update($id: ID!, $definition: MetaobjectDefinitionUpdateInput!) {
  metaobjectDefinitionUpdate(id: $id, definition: $definition) {
    metaobjectDefinition { id type access { storefront } }
    userErrors { field message code }
  }
}
"""


METAOBJECT_UPDATE = """
mutation update($id: ID!, $metaobject: MetaobjectUpdateInput!) {
  metaobjectUpdate(id: $id, metaobject: $metaobject) {
    metaobject { id handle capabilities { publishable { status } } }
    userErrors { field message code }
  }
}
"""

METAOBJECT_FULL_QUERY = """
query mo($handle: MetaobjectHandleInput!) {
  metaobjectByHandle(handle: $handle) {
    id
    handle
    type
    capabilities { publishable { status } }
  }
}
"""


def create_japan_mfdefs():
    """Create japan_payment_delivery and japan_exchange_refund metafield defs (metaobject_reference)."""
    # Need metaobject definition IDs
    def_ids = {}
    for mtype in ('payment_delivery', 'exchange_refund', 'warranty'):
        d = gql(METAOBJECT_DEF_BY_TYPE, {'type': mtype})['metaobjectDefinitionByType']
        if d:
            def_ids[mtype] = d['id']

    targets = [
        ('japan_payment_delivery', 'JAPAN Payment & Delivery', 'payment_delivery'),
        ('japan_exchange_refund', 'JAPAN Exchange & Refund', 'exchange_refund'),
        ('japan_warranty', 'JAPAN Warranty', 'warranty'),
    ]
    for key, name, mtype in targets:
        if mtype not in def_ids:
            print(f"[SKIP] No def for {mtype}")
            continue
        print(f"\nCreating {key} (metaobject_reference -> {mtype} {def_ids[mtype]})...")
        r = gql(METAFIELD_DEF_CREATE, {
            'definition': {
                'name': name,
                'namespace': 'custom',
                'key': key,
                'type': 'metaobject_reference',
                'ownerType': 'PRODUCT',
                'description': f'Japan market reference to {mtype} metaobject.',
                'access': {'storefront': 'PUBLIC_READ'},
                'validations': [{'name': 'metaobject_definition_id', 'value': def_ids[mtype]}],
            }
        })
        errs = r['metafieldDefinitionCreate']['userErrors']
        if errs:
            already = any('TAKEN' in (e.get('code') or '') for e in errs)
            if already:
                print(f"[OK] Already exists: custom.{key}")
            else:
                print(f"[ERROR] {errs}")
        else:
            d = r['metafieldDefinitionCreate']['createdDefinition']
            print(f"[OK] Created: {d['name']} (custom.{d['key']}) id={d['id']}")


EXTRA_HANDLES_FOR_REVIEW = [
    'anneau-flap-bag-hay-yellow',
    'pave-petit-bag-soft-black',
    'arc-crossbody-bag-soft-black',
    'marron-demi-bag-soft-black',
    'curved-lip-case-soft-black',
    'pillow-card-wallet-soft-black',
    'lowe-desert-boots-soft-black',
    'comfort-loafer-soft-black',
    'lumen-x-yeodong-yun-necklace-i',
    'lumen-x-yeodong-yun-ring-i',
]


POLICY_TRANSLATION_PROMPT = """You are the LUMEN brand voice copywriter — translating Atelier de LUMEN policy content (Payment & Delivery / Exchange & Refund / Warranty) to Japanese for intl.atlm.kr Japan market.

Apply `lumen-product-translation` skill v2.2 voice principles, ADAPTED for policy/legal text.

═══════════════════════════════════════════════════════════
TONE — Policy/Legal Adaptation of LUMEN VOICE
═══════════════════════════════════════════════════════════
Reference: The Row · Lemaire support pages — refined, restrained, legally clear.
- Polite Japanese (です・ます体 ALLOWED here — this is policy, not product copy)
- Concise sentences, no decorative adjectives
- Information-first; no emotional inflation
- No 私たち/We — speak as the brand without self-reference where possible
- Use refined verbs (申し受けます / お受けいたします / ご了承ください) — never casual

═══════════════════════════════════════════════════════════
FORBIDDEN (LUMEN guide §-1.3, applies even to policy)
═══════════════════════════════════════════════════════════
Artisan overload: 職人 / 匠 / 丹念に / 心を込めて / 逸品 / 究極 / 卓越 / クラフトマンシップ
Emotional inflation: 特別な / 美しい / エレガント / 魅力的な / 上品な (avoid in policy)
Translation stiffness: 〜することができます (use 〜可能 / 〜いたします)
Identity dilution: 風呂敷 / カウレザー / ライニング / ダストバッグ

═══════════════════════════════════════════════════════════
PROPER NAMES — Latin Script (NEVER katakana)
═══════════════════════════════════════════════════════════
LUMEN / Atelier de LUMEN — Latin only
HANJIN Express / FEDEX — Latin (NOT ハンジンエクスプレス / フェデックス)
Brand collaborator names (Yeodong Yun etc) — Latin

═══════════════════════════════════════════════════════════
STANDARD VOCABULARY
═══════════════════════════════════════════════════════════
Country names — standard Japanese: 日本 / シンガポール / 香港 / 台湾 / アメリカ合衆国 / イギリス etc
Numbers — keep numerals (1, 2, 3 — NOT 一, 二, 三)
Currency — JPY / 円 (use as appropriate)
Business days — 営業日
Shipping — 配送 (NOT 出荷 in customer-facing context)
Customs/duty — 関税 (NOT カスタム / デューティ)
Refund — 返金 (NOT リファンド)
Exchange — 交換
Return — 返品
Warranty — 保証

═══════════════════════════════════════════════════════════
JSON PRESERVATION
═══════════════════════════════════════════════════════════
Input is Shopify rich_text_field JSON: {"type":"root","children":[...]}
- Preserve EXACT structure (root/paragraph/list/text nodes)
- Only translate "value" fields of text nodes
- Preserve "bold" marks on text nodes
- Preserve URL fields in link nodes
- Output must be parseable JSON

═══════════════════════════════════════════════════════════
SELF-CHECK before output
═══════════════════════════════════════════════════════════
1. Brand/courier names in Latin? (LUMEN / HANJIN Express)
2. No artisan/emotional inflation words?
3. Polite です・ます but not stiff translation-ese?
4. JSON structure intact and parseable?
5. All numerical/date data preserved?

OUTPUT: Return ONLY the translated JSON (parseable). No markdown, no code blocks, no comments before/after."""


def translate_policy_entries():
    """Translate English Common entries to Japanese, save to *-japan entries. Also generate gap report."""
    print("=== Translating Policy Entries to Japanese ===")
    items = [
        ('payment_delivery', '2603128-common', 'payment-japan'),
        ('exchange_refund', '260328-common', 'exchange-japan'),
        ('warranty', 'warranty-common', 'warranty-japan'),
    ]

    out_path = 'review_policy_translations.txt'
    f = open(out_path, 'w', encoding='utf-8')
    f.write("=== POLICY TRANSLATIONS REVIEW ===\n\n")
    f.write("아래 일본어 번역본을 검토 후 Admin에서 수정하시거나, 그대로 적용을 알려주세요.\n\n")

    total_in = total_out = 0

    for mtype, common_handle, japan_handle in items:
        print(f"\nProcessing {mtype}/{common_handle} -> {japan_handle}...")
        # Get common entry full body
        common = gql(METAOBJECT_BY_HANDLE_QUERY, {'handle': {'type': mtype, 'handle': common_handle}})['metaobjectByHandle']
        if not common:
            print(f"[SKIP] Common not found")
            continue
        body_en = ''
        for fld in common['fields']:
            if fld['key'] == 'body':
                body_en = fld['value'] or ''
                break
        if not body_en:
            print(f"[SKIP] No body field")
            continue

        # Translate via Anthropic with policy-specific system prompt
        resp = client.messages.create(
            model=MODEL,
            max_tokens=8000,
            system=[{
                "type": "text",
                "text": POLICY_TRANSLATION_PROMPT,
                "cache_control": {"type": "ephemeral"}
            }],
            messages=[{"role": "user", "content": f"Translate this Shopify rich_text JSON to Japanese:\n\n{body_en}"}]
        )
        body_ja = resp.content[0].text.strip()
        if body_ja.startswith('```'):
            body_ja = body_ja.split('\n', 1)[1]
            if body_ja.endswith('```'):
                body_ja = body_ja.rsplit('```', 1)[0]
            if body_ja.startswith('json'):
                body_ja = body_ja[4:].strip()
            body_ja = body_ja.strip()

        # Validate JSON
        try:
            json.loads(body_ja)
        except Exception as e:
            print(f"[ERROR] {mtype} JSON parse failed: {e}")
            f.write(f"\n=== {mtype.upper()} — JSON PARSE ERROR ===\n{body_ja[:500]}\n\n")
            continue

        total_in += resp.usage.input_tokens
        total_out += resp.usage.output_tokens

        # Update japan entry
        japan = gql(METAOBJECT_BY_HANDLE_QUERY, {'handle': {'type': mtype, 'handle': japan_handle}})['metaobjectByHandle']
        if not japan:
            print(f"[SKIP] Japan entry not found, creating...")
            r = gql(METAOBJECT_CREATE, {
                'metaobject': {
                    'type': mtype,
                    'handle': japan_handle,
                    'fields': [{'key': 'body', 'value': body_ja}],
                }
            })
            errs = r['metaobjectCreate']['userErrors']
            if errs:
                print(f"[ERROR] {errs}")
                continue
        else:
            r = gql(METAOBJECT_UPDATE, {
                'id': japan['id'],
                'metaobject': {
                    'fields': [{'key': 'body', 'value': body_ja}],
                }
            })
            errs = r['metaobjectUpdate']['userErrors']
            if errs:
                print(f"[ERROR] {errs}")
                continue
        print(f"[OK] {mtype}/{japan_handle} updated ({len(body_ja)} chars)")

        # Write to review file
        f.write(f"\n=== {mtype.upper()} ({japan_handle}) ===\n\n")
        f.write("--- ENGLISH (source) ---\n")
        f.write(body_en[:3000])
        f.write("\n\n--- 日本語 (LUMEN tone, applied to entry) ---\n")
        f.write(body_ja[:3000])
        f.write("\n\n" + "=" * 80 + "\n")

    f.write("\n\n" + "=" * 80 + "\n")
    f.write("=== 일본 시장 보완 권장 사항 ===\n\n")
    f.write("""
[PAYMENT & DELIVERY]
- 일본 국내 배송 파트너 사용 여부 (HANJIN 외에 야마토/사가와 등 대안)
- 일본 소비세 (10%) 처리 명시: 가격 포함? 결제 시 별도?
- DDP/DAP 명시 — 현재는 DAP (관세는 고객). 일본은 ¥16,666 이상 주문에서 관세 발생 가능. 명확한 안내 권장.
- 출고 후 배송 일수 일본 평균 (예: 2-4 영업일) 명기 권장
- 오키나와/낙도 추가 일수 안내 (필요 시)

[EXCHANGE & REFUND]
- 특정상거래법(特定商取引法)에 따른 표기 의무 항목 (일본 e-commerce 법적 요구)
  - 사업자명, 책임자, 소재지, 연락처
  - 반품 가능 기간 명시
  - 환불 방법 및 시기
- 8일 cooling-off 정책 (방문판매가 아니므로 강제는 아니나 표기 권장)
- 일본 내 반품 회수처 주소 (한국 본사로 보내면 국제 반송비 부담)

[WARRANTY]
- 일본 내 공식 수리 접수처 (한국 발송 시 국제 운임 + 통관 부담)
- 일본 공식 스톡리스트가 있다면 별도 페이지 또는 일본 전용 안내
- 일본 PSE/JIS 등 인증 (해당 카테고리에 적용 시)

[기타 — 일본 e-commerce 일반 권장]
- 결제 수단: JPY 결제, JCB 카드 지원, Konbini 결제, PayPay 등 일본 전용 결제 방법 안내
- 사이즈 표기: 일본 표준 (예: 신발 cm, 옷 사이즈 매핑표)
- 고객 응대 이메일/문의 채널 일본어 운영 여부

위 항목 중 추가/수정 원하는 것 알려주시면 entries에 반영합니다.
""")
    f.close()
    cost = (total_in*3 + total_out*15) / 1_000_000
    print(f"\nSaved: {out_path}")
    print(f"Tokens: in={total_in}, out={total_out}")
    print(f"Estimated cost: ${cost:.3f}")


def review_panier_plus():
    """Translate body+details for all PANIER products + curated extras. Save to review file."""
    print("Fetching all PRODUCT translatable resources...")
    prods = fetch_resources('PRODUCT')

    # Collect PANIER products + extras
    panier_targets = []
    title_to_handle = {}
    for p in prods:
        en_title = ''
        for c in p['translatableContent']:
            if c['key'] == 'title':
                en_title = c['value'] or ''
            if c['key'] == 'handle':
                title_to_handle[p['resourceId']] = c['value']
        if 'PANIER' in en_title.upper() or 'PANIER' in en_title:
            panier_targets.append({'gid': p['resourceId'], 'title': en_title, 'handle': title_to_handle.get(p['resourceId'], '')})

    # Resolve panier handles via lookup
    print(f"PANIER products: {len(panier_targets)}")
    extras_handles = EXTRA_HANDLES_FOR_REVIEW
    print(f"Extra handles to add: {len(extras_handles)}")

    # Build full list of handles to process
    all_handles = []
    for t in panier_targets:
        if t.get('handle'):
            all_handles.append(t['handle'])
    seen = set(all_handles)
    for h in extras_handles:
        if h not in seen:
            all_handles.append(h)

    print(f"\nTotal handles to translate: {len(all_handles)}")

    # For each handle, fetch product + product_details metafield, translate body+details
    out_path = 'review_panier_plus.txt'
    total_in = total_out = total_cr = total_cw = 0
    f = open(out_path, 'w', encoding='utf-8')

    for idx, handle in enumerate(all_handles, 1):
        try:
            p = gql(PRODUCT_BY_HANDLE, {'handle': handle})['productByHandle']
        except Exception as e:
            print(f"[{idx}] {handle} -> ERROR: {e}")
            continue
        if not p:
            print(f"[{idx}] {handle} -> NOT FOUND")
            continue

        body_en = p.get('descriptionHtml') or ''
        details_en = ''
        for e in p['metafields']['edges']:
            n = e['node']
            if n['namespace'] == 'custom' and n['key'] == 'product_details':
                details_en = n.get('value') or ''
                break

        items = []
        labels = []
        if body_en.strip():
            items.append(body_en)
            labels.append('body')
        if details_en.strip():
            items.append(details_en)
            labels.append('details')

        if not items:
            print(f"[{idx}] {p['title']} -> nothing to translate")
            continue

        try:
            translations, usage = translate_batch(items, 'product description and details (HTML)')
            total_in += usage.input_tokens
            total_out += usage.output_tokens
            total_cr += getattr(usage, 'cache_read_input_tokens', 0) or 0
            total_cw += getattr(usage, 'cache_creation_input_tokens', 0) or 0
        except Exception as e:
            print(f"[{idx}] {p['title']} -> translate ERROR: {e}")
            continue

        body_ja = ''
        details_ja = ''
        for label, t in zip(labels, translations):
            if label == 'body':
                body_ja = t
            elif label == 'details':
                details_ja = t

        f.write(f"=== [{idx}/{len(all_handles)}] {p['title']} ({handle}) ===\n\n")
        if body_en:
            f.write("--- BODY (descriptionHtml) ---\n\n")
            f.write(f"[ENGLISH]\n{body_en}\n\n")
            f.write(f"[NEW LUMEN JA]\n{body_ja}\n\n")
        if details_en:
            f.write("--- PRODUCT DETAILS (metafield) ---\n\n")
            f.write(f"[ENGLISH]\n{details_en}\n\n")
            f.write(f"[NEW LUMEN JA]\n{details_ja}\n\n")
        f.write("=" * 80 + "\n\n")
        f.flush()
        print(f"[{idx}/{len(all_handles)}] {p['title'][:50]} done")

    f.close()
    cost = (total_in*3 + total_out*15 + total_cr*0.30 + total_cw*3.75) / 1_000_000
    print(f"\nSaved: {out_path}")
    print(f"Tokens: in={total_in} out={total_out} cache_read={total_cr} cache_write={total_cw}")
    print(f"Estimated cost: ${cost:.3f}")


def bulk_set_japan_refs(apply=False):
    """Set japan_payment_delivery + japan_exchange_refund + japan_warranty on ALL products."""
    print("Fetching all products...")
    prods = fetch_resources('PRODUCT')
    print(f"Total products: {len(prods)}")

    # Get Japan entries (resolve once)
    pj = gql(METAOBJECT_BY_HANDLE_QUERY, {'handle': {'type': 'payment_delivery', 'handle': 'payment-japan'}})['metaobjectByHandle']
    ej = gql(METAOBJECT_BY_HANDLE_QUERY, {'handle': {'type': 'exchange_refund', 'handle': 'exchange-japan'}})['metaobjectByHandle']
    wj = gql(METAOBJECT_BY_HANDLE_QUERY, {'handle': {'type': 'warranty', 'handle': 'warranty-japan'}})['metaobjectByHandle']
    print(f"payment-japan: {pj['id'] if pj else 'MISSING'}")
    print(f"exchange-japan: {ej['id'] if ej else 'MISSING'}")
    print(f"warranty-japan: {wj['id'] if wj else 'MISSING'}")

    if not (pj and ej and wj):
        print("[ABORT] Missing Japan entry.")
        return

    if not apply:
        print(f"\n[DRY-RUN] Would set 3 metafields on {len(prods)} products. Add --apply.")
        return

    succeeded = 0
    failed = []
    BATCH = 10
    all_metafields = []
    product_ids = []
    for p in prods:
        pid = p['resourceId']
        product_ids.append(pid)
        all_metafields.extend([
            {'ownerId': pid, 'namespace': 'custom', 'key': 'japan_payment_delivery', 'type': 'metaobject_reference', 'value': pj['id']},
            {'ownerId': pid, 'namespace': 'custom', 'key': 'japan_exchange_refund', 'type': 'metaobject_reference', 'value': ej['id']},
            {'ownerId': pid, 'namespace': 'custom', 'key': 'japan_warranty', 'type': 'metaobject_reference', 'value': wj['id']},
        ])

    # metafieldsSet supports batches up to 25 metafields per call
    for i in range(0, len(all_metafields), 25):
        chunk = all_metafields[i:i+25]
        try:
            r = gql(METAFIELDS_SET, {'metafields': chunk})
            errs = r['metafieldsSet']['userErrors']
            if errs:
                print(f"  [WARN batch {i//25}] {errs}")
                failed.extend(chunk)
            else:
                succeeded += len(chunk)
        except Exception as e:
            print(f"  [ERROR batch {i//25}] {e}")
            failed.extend(chunk)
        if i % 100 == 0:
            print(f"  Progress: {min(i+25, len(all_metafields))}/{len(all_metafields)} metafields set")

    print(f"\n=== Done ===")
    print(f"Set: {succeeded}/{len(all_metafields)} metafields | Failed: {len(failed)}")
    if failed:
        print(f"({len(failed)//3} products may have failed)")


def set_japan_refs_tray():
    """Set custom.japan_* metafields on TRAY II to point to Japan entries."""
    handle = 'lumen-yeodong-yun-tray-ii'
    p = gql(PRODUCT_BY_HANDLE, {'handle': handle})['productByHandle']
    if not p:
        print("Product not found.")
        return
    # Get Japan entries
    pj = gql(METAOBJECT_BY_HANDLE_QUERY, {'handle': {'type': 'payment_delivery', 'handle': 'payment-japan'}})['metaobjectByHandle']
    ej = gql(METAOBJECT_BY_HANDLE_QUERY, {'handle': {'type': 'exchange_refund', 'handle': 'exchange-japan'}})['metaobjectByHandle']
    wj = gql(METAOBJECT_BY_HANDLE_QUERY, {'handle': {'type': 'warranty', 'handle': 'warranty-japan'}})['metaobjectByHandle']

    metafields = []
    if pj:
        metafields.append({
            'ownerId': p['id'],
            'namespace': 'custom',
            'key': 'japan_payment_delivery',
            'type': 'metaobject_reference',
            'value': pj['id'],
        })
    if ej:
        metafields.append({
            'ownerId': p['id'],
            'namespace': 'custom',
            'key': 'japan_exchange_refund',
            'type': 'metaobject_reference',
            'value': ej['id'],
        })
    if wj:
        metafields.append({
            'ownerId': p['id'],
            'namespace': 'custom',
            'key': 'japan_warranty',
            'type': 'metaobject_reference',
            'value': wj['id'],
        })

    print(f"Setting {len(metafields)} metafields on {p['title']}...")
    r = gql(METAFIELDS_SET, {'metafields': metafields})
    errs = r['metafieldsSet']['userErrors']
    if errs:
        print(f"[ERROR] {errs}")
    else:
        for m in r['metafieldsSet']['metafields']:
            print(f"  [OK] {m['namespace']}.{m['key']} -> {m['value']}")


def theme_v4():
    """Update theme: use product.metafields.custom.japan_* for Japan branch."""
    main = get_main_theme()
    if not main:
        print("No theme.")
        return
    filename = 'snippets/info-drawers.liquid'
    content = fetch_theme_file_content(main['id'], filename)
    if not content:
        print("File not found.")
        return
    backup_path = f'theme_v4_BEFORE_{filename.replace("/", "_")}.txt'
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Saved BEFORE: {backup_path}")

    # Only PAYMENT/EXCHANGE switch to product metafield path. WARRANTY stays as shop.metaobjects (works).
    new_content = content
    new_content = new_content.replace(
        "shop.metaobjects.payment_delivery['payment-japan']",
        "product.metafields.custom.japan_payment_delivery.value"
    )
    new_content = new_content.replace(
        "shop.metaobjects.exchange_refund['exchange-japan']",
        "product.metafields.custom.japan_exchange_refund.value"
    )

    if new_content == content:
        print("[WARN] No replacements made.")
        return

    proposed_path = f'theme_v4_PROPOSED_{filename.replace("/", "_")}.txt'
    with open(proposed_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Saved PROPOSED v4: {proposed_path}")

    # Apply
    r = gql(THEME_FILES_UPSERT, {
        'themeId': main['id'],
        'files': [{'filename': filename, 'body': {'type': 'TEXT', 'value': new_content}}]
    })
    errs = r['themeFilesUpsert']['userErrors']
    if errs:
        print(f"[ERROR] {errs}")
    else:
        print(f"[OK] Theme v4 applied (product metafield path).")


def publish_metaobject_entry(mtype, handle):
    """Set entry capabilities.publishable.status = ACTIVE."""
    print(f"Looking up {mtype}/{handle}...")
    e = gql(METAOBJECT_FULL_QUERY, {'handle': {'type': mtype, 'handle': handle}})['metaobjectByHandle']
    if not e:
        print(f"Not found.")
        return
    cur_status = (e.get('capabilities') or {}).get('publishable', {}).get('status')
    print(f"Current status: {cur_status}")
    if cur_status == 'ACTIVE':
        print("[OK] Already ACTIVE.")
        return
    print("Setting to ACTIVE...")
    r = gql(METAOBJECT_UPDATE, {
        'id': e['id'],
        'metaobject': {
            'capabilities': {
                'publishable': {'status': 'ACTIVE'}
            }
        }
    })
    errs = r['metaobjectUpdate']['userErrors']
    if errs:
        print(f"[ERROR] {errs}")
    else:
        m = r['metaobjectUpdate']['metaobject']
        new_status = (m.get('capabilities') or {}).get('publishable', {}).get('status')
        print(f"[OK] {m['handle']} status = {new_status}")


def enable_metaobject_storefront_access(mtype):
    """Enable storefront PUBLIC_READ on a metaobject definition."""
    print(f"Looking up definition: {mtype}")
    d = gql(METAOBJECT_DEF_BY_TYPE, {'type': mtype})['metaobjectDefinitionByType']
    if not d:
        print(f"Not found: {mtype}")
        return
    print(f"Found: {d['name']} ({d['id']}) — current storefront access: {d['access']['storefront']}")
    if d['access']['storefront'] == 'PUBLIC_READ':
        print("[OK] Already PUBLIC_READ.")
        return
    print("Updating to PUBLIC_READ...")
    r = gql(METAOBJECT_DEF_UPDATE, {
        'id': d['id'],
        'definition': {
            'access': {'storefront': 'PUBLIC_READ'},
        }
    })
    errs = r['metaobjectDefinitionUpdate']['userErrors']
    if errs:
        print(f"[ERROR] {errs}")
    else:
        u = r['metaobjectDefinitionUpdate']['metaobjectDefinition']
        print(f"[OK] {u['type']} storefront access = {u['access']['storefront']}")


def create_warranty_def():
    print("Creating metaobject definition: warranty")
    r = gql(METAOBJECT_DEF_CREATE, {
        'definition': {
            'name': 'Warranty',
            'type': 'warranty',
            'description': 'Product warranty policy. One Common entry + Japan entry. Theme branches by market.',
            'fieldDefinitions': [
                {'key': 'date', 'name': 'date', 'type': 'date'},
                {'key': 'title', 'name': 'title', 'type': 'single_line_text_field'},
                {'key': 'body', 'name': 'body', 'type': 'rich_text_field'},
            ],
            'access': {'storefront': 'PUBLIC_READ'},
        }
    })
    errs = r['metaobjectDefinitionCreate']['userErrors']
    if errs:
        already = any('TAKEN' in (e.get('code') or '') for e in errs)
        if already:
            print(f"[OK] Already exists: warranty")
        else:
            print(f"[ERROR] {errs}")
    else:
        d = r['metaobjectDefinitionCreate']['metaobjectDefinition']
        print(f"[OK] Created definition: {d['name']} ({d['type']}) -> {d['id']}")


def html_to_rich_text(html_text):
    """Convert HTML (with <br>, <strong>, <a>) to Shopify rich_text_field JSON.
    Best-effort: preserves paragraph structure, bold, links. Other tags stripped."""
    import html as html_mod

    # Normalize line breaks: <br/> <br /> <br> -> \n
    s = re.sub(r'<br\s*/?>', '\n', html_text)
    # Split paragraphs by double newlines
    paragraphs = re.split(r'\n\s*\n', s)

    def parse_inline(t):
        children = []
        # Tokenize: text | <strong>...</strong> | <a href="...">...</a>
        pattern = re.compile(r'(<strong>.*?</strong>|<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>)', re.DOTALL)
        pos = 0
        for m in pattern.finditer(t):
            if m.start() > pos:
                txt = html_mod.unescape(re.sub(r'<[^>]+>', '', t[pos:m.start()]))
                if txt:
                    children.append({'type': 'text', 'value': txt})
            tag = m.group(0)
            if tag.startswith('<strong>'):
                inner = re.sub(r'<[^>]+>', '', tag[len('<strong>'):-len('</strong>')])
                inner = html_mod.unescape(inner)
                if inner:
                    children.append({'type': 'text', 'value': inner, 'bold': True})
            elif tag.startswith('<a'):
                url = m.group(2)
                label = re.sub(r'<[^>]+>', '', m.group(3))
                label = html_mod.unescape(label)
                children.append({
                    'type': 'link',
                    'url': url,
                    'children': [{'type': 'text', 'value': label}]
                })
            pos = m.end()
        if pos < len(t):
            txt = html_mod.unescape(re.sub(r'<[^>]+>', '', t[pos:]))
            if txt:
                children.append({'type': 'text', 'value': txt})
        return children

    para_nodes = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        children = parse_inline(p)
        if children:
            para_nodes.append({'type': 'paragraph', 'children': children})

    return json.dumps({'type': 'root', 'children': para_nodes}, ensure_ascii=False)


def create_warranty_from_theme():
    """Extract hardcoded warranty HTML from info-drawers.liquid, create warranty-common entry."""
    main = get_main_theme()
    if not main:
        print("No theme.")
        return
    # Use BEFORE backup if exists, else fetch
    backup_path = 'theme_BEFORE_snippets_info-drawers.liquid.txt'
    if os.path.exists(backup_path):
        with open(backup_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"Reading hardcoded warranty from backup: {backup_path}")
    else:
        content = fetch_theme_file_content(main['id'], 'snippets/info-drawers.liquid')
        print("Reading hardcoded warranty from live theme.")

    # Extract pane 4 inner HTML between <div class="metafield-rich_text_field"> ... </div>
    m = re.search(r'<div class="info-drawer-pane" data-pane="4">\s*(.*?)</div>\s*\n\s*</div>\s*\n\s*<script>', content, re.DOTALL)
    if not m:
        # Try simpler pattern for pane 4 content
        m = re.search(r'<div class="info-drawer-pane" data-pane="4">(.*?)</div>\s*</div>\s*<script>', content, re.DOTALL)
    if not m:
        # Fallback: find pane 4 start, take until next outer </div>
        idx = content.find('data-pane="4"')
        if idx == -1:
            print("[ERROR] Could not locate pane 4.")
            return
        # find first <p> ... last </p> in this region
        sub = content[idx:idx+3000]
        m_start = sub.find('<p>')
        m_end = sub.rfind('</p>')
        if m_start == -1 or m_end == -1:
            print("[ERROR] Could not locate <p>..</p> in pane 4.")
            return
        warranty_html = sub[m_start:m_end + len('</p>')]
    else:
        # remove outer wrapping div
        inner = m.group(1)
        # extract just the <p>...</p>
        m2 = re.search(r'<p>(.*?)</p>', inner, re.DOTALL)
        if not m2:
            warranty_html = inner.strip()
        else:
            warranty_html = m2.group(1).strip()

    print(f"Extracted warranty HTML: {len(warranty_html)} chars")
    rich_text_json = html_to_rich_text(warranty_html)

    out_path = 'warranty_extracted.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(rich_text_json)
    print(f"Saved rich_text JSON: {out_path}")

    # Create warranty/warranty-common entry
    print("Creating warranty/warranty-common...")
    r = gql(METAOBJECT_CREATE, {
        'metaobject': {
            'type': 'warranty',
            'handle': 'warranty-common',
            'fields': [
                {'key': 'title', 'value': 'WARRANTY'},
                {'key': 'body', 'value': rich_text_json},
            ],
        }
    })
    errs = r['metaobjectCreate']['userErrors']
    if errs:
        already = any('TAKEN' in (e.get('code') or '') for e in errs)
        if already:
            print(f"[OK] Already exists: warranty/warranty-common")
        else:
            print(f"[ERROR] {errs}")
    else:
        m = r['metaobjectCreate']['metaobject']
        print(f"[OK] Created warranty/warranty-common -> {m['id']}")


def prepare_theme_v2():
    """Prepare info-drawers.liquid v2: 4 panes with Japan branches; pane 4 uses metaobject."""
    main = get_main_theme()
    if not main:
        print("No theme.")
        return
    filename = 'snippets/info-drawers.liquid'
    content = fetch_theme_file_content(main['id'], filename)
    if content is None:
        print(f"File not found: {filename}")
        return

    backup_path = f'theme_v2_BEFORE_{filename.replace("/", "_")}.txt'
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Saved BEFORE: {backup_path}")

    proposed = content

    # ===== PANE 2: PAYMENT & DELIVERY =====
    pane2_old = (
        '{%- assign payment_obj = product.metafields.custom.payment_delivery.value -%}\n'
        '    {%- if payment_obj -%}\n'
        '      {{ payment_obj.body | metafield_tag }}\n'
        '    {%- endif -%}'
    )
    pane2_new = (
        "{%- if localization.market.handle == 'japan' -%}\n"
        "      {%- assign payment_obj = shop.metaobjects.payment_delivery['2603128-japan'] -%}\n"
        "    {%- else -%}\n"
        "      {%- assign payment_obj = product.metafields.custom.payment_delivery.value -%}\n"
        "    {%- endif -%}\n"
        "    {%- if payment_obj -%}\n"
        "      {{ payment_obj.body | metafield_tag }}\n"
        "    {%- endif -%}"
    )
    if pane2_old not in proposed:
        print("[WARN] pane 2 exact pattern not found; trying flexible match.")
        pane2_old_flex = re.compile(
            r'\{%-\s*assign\s+payment_obj\s*=\s*product\.metafields\.custom\.payment_delivery\.value\s*-%}\s*\n'
            r'\s*\{%-\s*if\s+payment_obj\s*-%}\s*\n'
            r'\s*\{\{\s*payment_obj\.body\s*\|\s*metafield_tag\s*\}\}\s*\n'
            r'\s*\{%-\s*endif\s*-%}'
        )
        proposed = pane2_old_flex.sub(pane2_new, proposed, count=1)
    else:
        proposed = proposed.replace(pane2_old, pane2_new, 1)

    # ===== PANE 3: EXCHANGE & REFUND =====
    pane3_old = (
        '{%- assign exchange_obj = product.metafields.custom.exchange_refund.value -%}\n'
        '    {%- if exchange_obj -%}\n'
        '      {{ exchange_obj.body | metafield_tag }}\n'
        '    {%- endif -%}'
    )
    pane3_new = (
        "{%- if localization.market.handle == 'japan' -%}\n"
        "      {%- assign exchange_obj = shop.metaobjects.exchange_refund['260328-japan'] -%}\n"
        "    {%- else -%}\n"
        "      {%- assign exchange_obj = product.metafields.custom.exchange_refund.value -%}\n"
        "    {%- endif -%}\n"
        "    {%- if exchange_obj -%}\n"
        "      {{ exchange_obj.body | metafield_tag }}\n"
        "    {%- endif -%}"
    )
    if pane3_old not in proposed:
        pane3_old_flex = re.compile(
            r'\{%-\s*assign\s+exchange_obj\s*=\s*product\.metafields\.custom\.exchange_refund\.value\s*-%}\s*\n'
            r'\s*\{%-\s*if\s+exchange_obj\s*-%}\s*\n'
            r'\s*\{\{\s*exchange_obj\.body\s*\|\s*metafield_tag\s*\}\}\s*\n'
            r'\s*\{%-\s*endif\s*-%}'
        )
        proposed = pane3_old_flex.sub(pane3_new, proposed, count=1)
    else:
        proposed = proposed.replace(pane3_old, pane3_new, 1)

    # ===== PANE 4: WARRANTY (replace hardcoded HTML with metaobject reference + Japan branch) =====
    # Find the hardcoded pane 4 content and replace with metaobject pattern
    pane4_pattern = re.compile(
        r'(<div class="info-drawer-pane" data-pane="4">\s*\n)'
        r'\s*<div class="metafield-rich_text_field">\s*\n'
        r'(.*?)'
        r'\s*</div>\s*\n'
        r'(\s*</div>\s*\n)',
        re.DOTALL
    )
    new_pane4 = (
        r'\1'
        "    {%- if localization.market.handle == 'japan' -%}\n"
        "      {%- assign warranty_obj = shop.metaobjects.warranty['warranty-japan'] -%}\n"
        "    {%- else -%}\n"
        "      {%- assign warranty_obj = shop.metaobjects.warranty['warranty-common'] -%}\n"
        "    {%- endif -%}\n"
        "    {%- if warranty_obj -%}\n"
        "      <div class=\"metafield-rich_text_field\">\n"
        "        {{ warranty_obj.body | metafield_tag }}\n"
        "      </div>\n"
        "    {%- endif -%}\n"
        r'\3'
    )
    proposed_new = pane4_pattern.sub(new_pane4, proposed, count=1)
    if proposed_new == proposed:
        print("[WARN] pane 4 pattern not matched; warranty hardcoded text remains.")
    else:
        proposed = proposed_new

    proposed_path = f'theme_v2_PROPOSED_{filename.replace("/", "_")}.txt'
    with open(proposed_path, 'w', encoding='utf-8') as f:
        f.write(proposed)
    print(f"Saved PROPOSED v2: {proposed_path} ({len(proposed)} chars)")

    # Also save a focused diff
    diff_path = f'theme_v2_DIFF_{filename.replace("/", "_")}.txt'
    with open(diff_path, 'w', encoding='utf-8') as f:
        f.write("=== Search and show context for: payment_delivery ===\n")
        for source_label, source in [('BEFORE', content), ('AFTER', proposed)]:
            f.write(f"\n--- {source_label} ---\n")
            lines = source.split('\n')
            for i, line in enumerate(lines, 1):
                if any(k in line for k in ('payment_delivery', 'exchange_refund', 'warranty', 'data-pane="2"', 'data-pane="3"', 'data-pane="4"', 'metafield-rich_text_field')):
                    start = max(0, i - 2)
                    end = min(len(lines), i + 2)
                    for j in range(start, end):
                        f.write(f"  L{j+1}: {lines[j]}\n")
                    f.write("\n")
    print(f"Saved DIFF: {diff_path}")
    print("Review theme_v2_DIFF_*.txt then run --apply-theme-v2.")


def apply_buy_buttons_fix():
    """Apply local theme_PROPOSED_buy_buttons.liquid.txt to live theme snippets/buy-buttons.liquid."""
    main = get_main_theme()
    if not main:
        print("No theme.")
        return
    filename = 'snippets/buy-buttons.liquid'
    src_path = 'theme_PROPOSED_buy_buttons.liquid.txt'
    if not os.path.exists(src_path):
        print(f"Source missing: {src_path}")
        return
    # Backup current first
    current = fetch_theme_file_content(main['id'], filename)
    backup_path = f'theme_BACKUP_buy_buttons_{int(time.time())}.txt'
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(current or '')
    print(f"Backup saved: {backup_path} ({len(current or '')} chars)")
    with open(src_path, 'r', encoding='utf-8') as f:
        new_content = f.read()
    print(f"Applying {len(new_content)} chars to {filename}...")
    r = gql(THEME_FILES_UPSERT, {
        'themeId': main['id'],
        'files': [{'filename': filename, 'body': {'type': 'TEXT', 'value': new_content}}]
    })
    errs = r['themeFilesUpsert']['userErrors']
    if errs:
        print(f"[ERROR] {errs}")
    else:
        print(f"[OK] {filename} updated.")
        print(f"Revert: copy {backup_path} to {src_path} and run --apply-buy-buttons-fix again.")


def apply_currency_persistence_fix():
    """Fix currency persistence: extend CACHE_TTL to 365 days + add retry logic to triggerBucksCurrency.

    Symptom: After user sets currency (e.g. JPY) and revisits, currency reverts to USD.
    Root cause: triggerBucksCurrency() called once without retry; if BUCKS widget not yet
    loaded, click silently fails and Shopify Markets default (USD) is shown.

    Fix:
      1) CACHE_TTL: 7 days -> 365 days (1 year)
      2) triggerBucksCurrency(): add 20-retry x 200ms loop (same as Case 1 URL param)
      3) Case 4 (cached): wait for DOMContentLoaded + 300ms before calling
    """
    main = get_main_theme()
    if not main:
        print("No theme.")
        return
    filename = 'snippets/lumen-country-selector-js.liquid'
    current = fetch_theme_file_content(main['id'], filename)
    if not current:
        print(f"[ERROR] {filename} not found in theme.")
        return

    backup_path = f'theme_BACKUP_country_selector_js_{int(time.time())}.txt'
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(current)
    print(f"Backup saved: {backup_path} ({len(current)} chars)")

    new_content = current
    changes = []

    # ---------- Fix 1: CACHE_TTL 7 days -> 365 days ----------
    old_ttl = '  var CACHE_TTL = 7 * 24 * 60 * 60 * 1000;'
    new_ttl = '  var CACHE_TTL = 365 * 24 * 60 * 60 * 1000;'
    if old_ttl in new_content:
        new_content = new_content.replace(old_ttl, new_ttl)
        changes.append('CACHE_TTL: 7 days -> 365 days')
    else:
        print(f"[WARN] CACHE_TTL pattern not found - may already be patched")

    # ---------- Fix 2: triggerBucksCurrency add retry ----------
    old_trigger = """  function triggerBucksCurrency(code) {
    // BUCKS는 <li class="converterTriggers" id="{CODE}"> 클릭으로 작동
    // select change 이벤트나 JS API는 Markets 환경에서 무효
    var li = document.querySelector('.buckscc-select-options li[id="' + code + '"]')
          || document.querySelector('.buckscc-select-options li[rel="' + code + '"]');
    if (li) {
      li.click();
      return;
    }
    // fallback: li가 없으면 (BUCKS에 해당 통화가 미등록) USD로
    var usdLi = document.querySelector('.buckscc-select-options li[id="USD"]');
    if (usdLi) usdLi.click();
  }"""
    new_trigger = """  function triggerBucksCurrency(code, attempts) {
    // BUCKS는 <li class="converterTriggers" id="{CODE}"> 클릭으로 작동
    // select change 이벤트나 JS API는 Markets 환경에서 무효
    // BUCKS 미로딩 시 retry (최대 20회 x 200ms = 4초) - 통화 영구 적용 보장
    attempts = attempts || 0;
    var li = document.querySelector('.buckscc-select-options li[id="' + code + '"]')
          || document.querySelector('.buckscc-select-options li[rel="' + code + '"]');
    if (li) {
      li.click();
      return;
    }
    if (attempts < 20) {
      setTimeout(function() { triggerBucksCurrency(code, attempts + 1); }, 200);
      return;
    }
    // fallback: 20회 retry 후에도 li 없으면 (BUCKS에 해당 통화가 미등록) USD로
    var usdLi = document.querySelector('.buckscc-select-options li[id="USD"]');
    if (usdLi) usdLi.click();
  }"""
    if old_trigger in new_content:
        new_content = new_content.replace(old_trigger, new_trigger)
        changes.append('triggerBucksCurrency: add 20-retry x 200ms loop')
    else:
        print(f"[WARN] triggerBucksCurrency pattern not found - may already be patched")

    # ---------- Fix 3: Case 4 - wait for DOMContentLoaded before BUCKS call ----------
    old_case4 = """    // ── Case 4: 모든 해외 캐시 (JP 포함) ──
    // JP: ?country=JP로 이미 진입했다면 Case 1에서 처리됨
    //     직접 접속이면 BUCKS로 JPY 적용 후 모달 스킵
    // 그 외: BUCKS로 해당 통화 적용 후 모달 스킵
    triggerBucksCurrency(cached.currencyCode || 'USD');
    return false;"""
    new_case4 = """    // ── Case 4: 모든 해외 캐시 (JP 포함) ──
    // JP: ?country=JP로 이미 진입했다면 Case 1에서 처리됨
    //     직접 접속이면 BUCKS로 JPY 적용 후 모달 스킵
    // 그 외: BUCKS로 해당 통화 적용 후 모달 스킵
    // DOM + BUCKS 위젯 초기화 대기 (retry는 triggerBucksCurrency 내장)
    var cachedCur = cached.currencyCode || 'USD';
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function() {
        setTimeout(function() { triggerBucksCurrency(cachedCur); }, 300);
      });
    } else {
      setTimeout(function() { triggerBucksCurrency(cachedCur); }, 300);
    }
    return false;"""
    if old_case4 in new_content:
        new_content = new_content.replace(old_case4, new_case4)
        changes.append('Case 4: wait for DOMContentLoaded before triggerBucksCurrency')
    else:
        print(f"[WARN] Case 4 pattern not found - may already be patched")

    if not changes:
        print("[ERROR] No changes made - all patterns may already be patched or theme has been modified.")
        return

    proposed_path = f'theme_PROPOSED_country_selector_js_{int(time.time())}.txt'
    with open(proposed_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Saved PROPOSED: {proposed_path} ({len(new_content)} chars)")
    print(f"Changes applied:")
    for c in changes:
        print(f"  - {c}")

    print(f"Applying to live theme...")
    r = gql(THEME_FILES_UPSERT, {
        'themeId': main['id'],
        'files': [{'filename': filename, 'body': {'type': 'TEXT', 'value': new_content}}]
    })
    errs = r['themeFilesUpsert']['userErrors']
    if errs:
        print(f"[ERROR] {errs}")
    else:
        print(f"[OK] {filename} updated.")
        print(f"     Backup: {backup_path}")
        print(f"     Revert: copy backup content and re-upsert via API.")


def fix_theme_handles():
    """Replace numeric-prefix handles with letter-prefix in info-drawers.liquid."""
    main = get_main_theme()
    if not main:
        print("No theme.")
        return
    filename = 'snippets/info-drawers.liquid'
    content = fetch_theme_file_content(main['id'], filename)
    if not content:
        print("File not found.")
        return
    backup_path = f'theme_v3_BEFORE_{filename.replace("/", "_")}.txt'
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Saved BEFORE: {backup_path}")

    new_content = content
    new_content = new_content.replace("'2603128-japan'", "'payment-japan'")
    new_content = new_content.replace("'260328-japan'", "'exchange-japan'")

    if new_content == content:
        print("[WARN] No replacements made.")
        return

    proposed_path = f'theme_v3_PROPOSED_{filename.replace("/", "_")}.txt'
    with open(proposed_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Saved PROPOSED: {proposed_path}")

    print(f"Applying {len(new_content)} chars to {filename}...")
    r = gql(THEME_FILES_UPSERT, {
        'themeId': main['id'],
        'files': [{
            'filename': filename,
            'body': {'type': 'TEXT', 'value': new_content},
        }]
    })
    errs = r['themeFilesUpsert']['userErrors']
    if errs:
        print(f"[ERROR] {errs}")
    else:
        print(f"[OK] Theme handles updated to letter-prefix.")


def apply_theme_v2():
    main = get_main_theme()
    if not main:
        print("No theme.")
        return
    filename = 'snippets/info-drawers.liquid'
    proposed_path = f'theme_v2_PROPOSED_{filename.replace("/", "_")}.txt'
    if not os.path.exists(proposed_path):
        print(f"Proposed file missing: {proposed_path}. Run --prepare-theme-v2 first.")
        return
    with open(proposed_path, 'r', encoding='utf-8') as f:
        new_content = f.read()
    print(f"Applying {len(new_content)} chars to {filename}...")
    r = gql(THEME_FILES_UPSERT, {
        'themeId': main['id'],
        'files': [{
            'filename': filename,
            'body': {'type': 'TEXT', 'value': new_content},
        }]
    })
    errs = r['themeFilesUpsert']['userErrors']
    if errs:
        print(f"[ERROR] {errs}")
    else:
        print(f"[OK] Theme v2 applied")


def cafe24_auth_url():
    """Print Cafe24 OAuth authorization URL for user to click."""
    mall = os.environ.get('CAFE24_MALL_ID', 'atlm')
    cid = os.environ.get('CAFE24_CLIENT_ID')
    redirect = os.environ.get('CAFE24_REDIRECT_URI', 'https://atlm.kr/cafe24-callback')
    if not cid:
        print("CAFE24_CLIENT_ID missing in .env")
        return
    import urllib.parse
    params = {
        'response_type': 'code',
        'client_id': cid,
        'state': 'lumen-price-001',
        'redirect_uri': redirect,
        'scope': 'mall.read_product,mall.read_category',
    }
    url = f"https://{mall}.cafe24api.com/api/v2/oauth/authorize?" + urllib.parse.urlencode(params)
    print("=" * 60)
    print("Open this URL in your browser:")
    print()
    print(url)
    print()
    print("=" * 60)
    print("After login + approval, you'll be redirected to:")
    print(f"  {redirect}?code=XXXXXX&state=lumen-price-001")
    print()
    print("Copy the full URL from address bar and run:")
    print("  python lumen_auto_translate.py --cafe24-exchange-code <code>")
    print("  (the value after 'code=' in the redirect URL)")


def cafe24_exchange_code(code):
    """Exchange authorization code for access token."""
    import base64
    mall = os.environ.get('CAFE24_MALL_ID', 'atlm')
    cid = os.environ.get('CAFE24_CLIENT_ID')
    secret = os.environ.get('CAFE24_CLIENT_SECRET')
    redirect = os.environ.get('CAFE24_REDIRECT_URI', 'https://atlm.kr/cafe24-callback')

    url = f"https://{mall}.cafe24api.com/api/v2/oauth/token"
    print(f"[DEBUG] POST {url}")
    print(f"[DEBUG] redirect_uri: {redirect}")
    print(f"[DEBUG] client_id: {cid}")
    print(f"[DEBUG] secret length: {len(secret or '')}")
    print(f"[DEBUG] code: {code}")

    # Method 1: Basic auth header
    creds = f"{cid}:{secret}"
    b64 = base64.b64encode(creds.encode()).decode()
    headers1 = {
        'Authorization': f'Basic {b64}',
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    data1 = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect,
    }
    print("\n[Try 1] Basic auth header...")
    r = requests.post(url, headers=headers1, data=data1, timeout=30)
    print(f"  HTTP {r.status_code}: {r.text[:300]}")
    if r.status_code == 200:
        tok = r.json()
    else:
        # Method 2: credentials in body
        print("\n[Try 2] Credentials in body...")
        headers2 = {'Content-Type': 'application/x-www-form-urlencoded'}
        data2 = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': cid,
            'client_secret': secret,
            'redirect_uri': redirect,
        }
        r = requests.post(url, headers=headers2, data=data2, timeout=30)
        print(f"  HTTP {r.status_code}: {r.text[:300]}")
        if r.status_code != 200:
            return
    if r.status_code == 200:
        tok = r.json()
    print(f"[OK] access_token: {tok.get('access_token', '')[:20]}...")
    print(f"  expires_at: {tok.get('expires_at')}")
    print(f"  refresh_token: {tok.get('refresh_token', '')[:20]}...")
    # Save to .env
    env_path = '.env'
    lines = []
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.startswith('CAFE24_ACCESS_TOKEN=') and not line.startswith('CAFE24_REFRESH_TOKEN='):
                lines.append(line.rstrip('\n'))
    lines.append(f"CAFE24_ACCESS_TOKEN={tok.get('access_token')}")
    lines.append(f"CAFE24_REFRESH_TOKEN={tok.get('refresh_token')}")
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(f"\n[OK] Tokens saved to {env_path}")
    print("Now run: python lumen_auto_translate.py --cafe24-export-prices")


def full_price_table():
    """All Shopify + Cafe24 products, with USD/KRW/JPY/Buyma data, output to CSV."""
    # Load Shopify - keep all variants but dedupe by base product
    shopify_by_name = {}
    with open('shopify_prices_usd.csv', 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = normalize_name(row['title'])
            if key and (key not in shopify_by_name or float(row['price_usd'] or 0) > float(shopify_by_name[key]['price'] or 0)):
                shopify_by_name[key] = {
                    'title': row['title'],
                    'handle': row['handle'],
                    'price': row['price_usd'],
                }

    # Load Cafe24 - keep all sellable products
    cafe24_rows = []
    with open('cafe24_prices_krw.csv', 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            price = float(row['price'] or 0)
            name = row.get('product_name') or ''
            if price <= 0:
                continue
            if '직원' in name or name.startswith('구매'):
                continue
            if not name.strip():
                continue
            cafe24_rows.append({
                'name': name,
                'code': row['product_code'],
                'price': price,
                'retail': row['retail_price'],
                'key': normalize_name(name),
            })

    # Load Buyma - aggregated by family (no color)
    buyma = {}
    with open('buyma_jpy_prices.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            fkey = normalize_family(row['product_name'])
            if not fkey:
                continue
            price = int(row['price_jpy'])
            if fkey not in buyma:
                buyma[fkey] = {'prices': [], 'sellers': []}
            buyma[fkey]['prices'].append(price)
            buyma[fkey]['sellers'].append(row['seller'])

    # Build unified rows
    USD_RATE = 1400
    out_rows = []
    matched_shopify_keys = set()

    for c in cafe24_rows:
        s = shopify_by_name.get(c['key'], {})
        # Buyma uses family key (without color)
        fkey = normalize_family(c['name'])
        b = buyma.get(fkey, {})
        if s:
            matched_shopify_keys.add(c['key'])

        krw = c['price']
        usd_shopify = float(s.get('price') or 0)
        usd_rrp = krw * 1.3 / USD_RATE
        jpy_rrp = krw * 1.3 / 10
        # JPY currently displayed on Shopify (auto-converted from USD at ~150 rate)
        SHOPIFY_USD_TO_JPY = 150
        jpy_shopify_display = int(usd_shopify * SHOPIFY_USD_TO_JPY) if usd_shopify else 0

        bp = b.get('prices', [])
        jpy_min = min(bp) if bp else 0
        jpy_max = max(bp) if bp else 0
        jpy_avg = int(sum(bp) / len(bp)) if bp else 0

        out_rows.append({
            'cafe24_name': c['name'],
            'cafe24_code': c['code'],
            'krw': krw,
            'shopify_title': s.get('title', ''),
            'shopify_handle': s.get('handle', ''),
            'usd_shopify': usd_shopify,
            'usd_rrp': round(usd_rrp, 0),
            'jpy_rrp': int(jpy_rrp),
            'jpy_shopify_display': jpy_shopify_display,
            'jpy_buyma_min': jpy_min,
            'jpy_buyma_max': jpy_max,
            'jpy_buyma_avg': jpy_avg,
            'buyma_listings': len(bp),
            'source': 'Cafe24+Shopify' if s else 'Cafe24 only',
        })

    # Add Shopify-only products
    for key, s in shopify_by_name.items():
        if key in matched_shopify_keys:
            continue
        usd = float(s.get('price') or 0)
        out_rows.append({
            'cafe24_name': '',
            'cafe24_code': '',
            'krw': '',
            'shopify_title': s['title'],
            'shopify_handle': s['handle'],
            'usd_shopify': usd,
            'usd_rrp': '',
            'jpy_rrp': '',
            'jpy_shopify_display': int(usd * 150) if usd else 0,
            'jpy_buyma_min': 0,
            'jpy_buyma_max': 0,
            'jpy_buyma_avg': 0,
            'buyma_listings': 0,
            'source': 'Shopify only',
        })

    # Sort: Cafe24+Shopify first, then Cafe24 only, then Shopify only; alphabetical within
    out_rows.sort(key=lambda r: (
        {'Cafe24+Shopify': 0, 'Cafe24 only': 1, 'Shopify only': 2}[r['source']],
        (r['cafe24_name'] or r['shopify_title']).upper()
    ))

    out_csv = 'full_price_table_v3.csv'
    with open(out_csv, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow([
            'cafe24_name', 'cafe24_code', 'KRW',
            'shopify_title', 'shopify_handle', 'USD_shopify',
            'USD_RRP', 'JPY_RRP', 'JPY_shopify_display_today',
            'JPY_buyma_min', 'JPY_buyma_max', 'JPY_buyma_avg', 'buyma_listings',
            'source'
        ])
        for r in out_rows:
            w.writerow([r['cafe24_name'], r['cafe24_code'], r['krw'],
                        r['shopify_title'], r['shopify_handle'], r['usd_shopify'],
                        r['usd_rrp'], r['jpy_rrp'], r.get('jpy_shopify_display', 0),
                        r['jpy_buyma_min'], r['jpy_buyma_max'], r['jpy_buyma_avg'], r['buyma_listings'],
                        r['source']])
    print(f"Saved: {out_csv} ({len(out_rows)} rows)")

    # Summary
    cs = sum(1 for r in out_rows if r['source'] == 'Cafe24+Shopify')
    co = sum(1 for r in out_rows if r['source'] == 'Cafe24 only')
    so = sum(1 for r in out_rows if r['source'] == 'Shopify only')
    with_buyma = sum(1 for r in out_rows if r['buyma_listings'])
    print(f"\nBreakdown:")
    print(f"  Cafe24 + Shopify matched: {cs}")
    print(f"  Cafe24 only (한국 전용): {co}")
    print(f"  Shopify only (해외 전용): {so}")
    print(f"  With Buyma data: {with_buyma}")


def price_compare_report():
    """Match Shopify USD + Cafe24 KRW + Buyma JPY by product name, output comparison report."""
    # Load Shopify
    shopify = {}
    with open('shopify_prices_usd.csv', 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = normalize_name(row['title'])
            if key not in shopify or float(shopify[key]['price']) < float(row['price_usd'] or 0):
                shopify[key] = {'title': row['title'], 'price': row['price_usd'], 'handle': row['handle']}

    # Load Cafe24 (filter 0 price + 직원구매)
    cafe24 = {}
    with open('cafe24_prices_krw.csv', 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            price = float(row['price'] or 0)
            if price <= 0:
                continue
            if '직원' in (row['product_name'] or '') or '구매' in (row['product_name'] or '')[:3]:
                continue
            key = normalize_name(row['product_name'])
            if not key:
                continue
            if key not in cafe24:
                cafe24[key] = {'name': row['product_name'], 'price': price, 'retail': row['retail_price']}

    # Load Buyma (aggregate: min/max/avg per product)
    buyma = {}
    with open('buyma_jpy_prices.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = normalize_name(row['product_name'])
            price = int(row['price_jpy'])
            if key not in buyma:
                buyma[key] = {'name': row['product_name'], 'prices': [], 'sellers': []}
            buyma[key]['prices'].append(price)
            buyma[key]['sellers'].append(row['seller'])

    # Match — find products in all 3 (or 2) sources
    all_keys = set(shopify.keys()) | set(cafe24.keys()) | set(buyma.keys())
    USD_RATE = 1400
    JPY_RATE = 9.5  # rough KRW per JPY

    rows = []
    for k in all_keys:
        s = shopify.get(k, {})
        c = cafe24.get(k, {})
        b = buyma.get(k, {})
        if not any([s, c, b]):
            continue
        # Skip if only 1 source
        sources = sum([bool(s), bool(c), bool(b)])
        if sources < 2:
            continue

        usd_p = float(s.get('price') or 0)
        krw_p = c.get('price', 0)
        jpy_min = min(b.get('prices', [0])) if b else 0
        jpy_max = max(b.get('prices', [0])) if b else 0
        jpy_avg = (sum(b.get('prices', [])) / len(b['prices'])) if b else 0

        # Derived: expected USD from KRW (×1.3 / 1400) — USD RRP
        expected_usd = (krw_p * 1.3 / USD_RATE) if krw_p else 0
        # JPY RRP: KRW × 1.3 / 10 (LUMEN's JP price formula — same structure as USD)
        jpy_rrp = (krw_p * 1.3 / 10) if krw_p else 0
        # vs Buyma analysis
        jpy_vs_rrp = (jpy_avg - jpy_rrp) if (jpy_avg and jpy_rrp) else 0
        jpy_vs_rrp_pct = (jpy_vs_rrp / jpy_rrp * 100) if jpy_rrp else 0

        rows.append({
            'name': s.get('title') or c.get('name') or b.get('name'),
            'krw': krw_p,
            'usd_shopify': usd_p,
            'usd_expected': expected_usd,
            'jpy_rrp': jpy_rrp,
            'jpy_min': jpy_min,
            'jpy_max': jpy_max,
            'jpy_avg': int(jpy_avg) if jpy_avg else 0,
            'jpy_vs_rrp_pct': jpy_vs_rrp_pct,
            'buyma_count': len(b.get('prices', [])),
            'sources': sources,
        })

    # Sort by name
    rows.sort(key=lambda r: r['name'].upper())

    out = 'price_comparison_report.md'
    with open(out, 'w', encoding='utf-8') as f:
        f.write("# LUMEN 3-Channel Price Comparison Report\n\n")
        f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Sources: Shopify (intl.atlm.kr USD) + Cafe24 (atlm.kr KRW) + Buyma (resellers JPY)\n")
        f.write(f"Formulas:\n")
        f.write(f"  USD RRP = KRW × 1.3 / 1400\n")
        f.write(f"  JPY RRP = KRW × 1.3 / 10  ← LUMEN's official Japan pricing\n\n")
        f.write("| Product | KRW | USD intl | USD RRP | **JPY RRP** | Buyma min | Buyma max | Buyma avg | vs RRP | n |\n")
        f.write("|---|---|---|---|---|---|---|---|---|---|\n")
        for r in rows:
            jpy_rrp_str = f"¥{int(r['jpy_rrp']):>6,}" if r['jpy_rrp'] else "-"
            vs_rrp = f"{r['jpy_vs_rrp_pct']:+.0f}%" if r['buyma_count'] and r['jpy_rrp'] else "-"
            f.write(f"| {r['name'][:50]} | ₩{r['krw']:>9,.0f} | ${r['usd_shopify']:>5} | ${r['usd_expected']:>5.0f} | **{jpy_rrp_str}** | ¥{r['jpy_min']:>6,} | ¥{r['jpy_max']:>6,} | ¥{r['jpy_avg']:>6,} | {vs_rrp} | {r['buyma_count']} |\n")
        f.write(f"\nTotal matched products: {len(rows)}\n")
    print(f"Saved: {out}")
    print(f"\nMatched products (in ≥2 sources): {len(rows)}")
    print(f"Shopify-only: {len(set(shopify.keys()) - set(cafe24.keys()) - set(buyma.keys()))}")
    print(f"Cafe24-only: {len(set(cafe24.keys()) - set(shopify.keys()) - set(buyma.keys()))}")
    print(f"Buyma-only: {len(set(buyma.keys()) - set(shopify.keys()) - set(cafe24.keys()))}")


def normalize_name(name):
    """Normalize product name for matching including color/variant.

    Keeps color information so different colors don't collapse.
    Strips only brand markers, special chars, and Korean.
    """
    if not name:
        return ''
    import re
    n = name.upper()
    # Strip brand prefixes (within or outside brackets)
    n = re.sub(r'\[LUMEN[^\]]*\]|\bLUMEN\s*X\s*[A-Z]+\b|\bATELIER\s+DE\s+LUMEN\b|\bLUMEN\b', ' ', n)
    # Strip brackets/parens but KEEP their content (color info inside)
    n = re.sub(r'[\[\]\(\)【】「」]', ' ', n)
    # Strip special markers
    n = re.sub(r'[☆★◆◇■□♥♡●○•・/+&]', ' ', n)
    # Strip Korean (Cafe24 sometimes has Korean+English mix)
    n = re.sub(r'[가-힣]+', ' ', n)
    # Strip non-alphanumeric (but keep word boundaries)
    n = re.sub(r'[^A-Z0-9\s]', ' ', n)
    # Collapse whitespace
    n = re.sub(r'\s+', ' ', n).strip()
    # Filter generic marketing words but KEEP color words
    words = n.split()
    stop = {'BAG', 'BAGS', 'COLOR', 'COLORS', 'COLLECTION', 'NEW', 'SALE', 'SS', 'FW', 'AW', 'NEWoman', 'PCS', 'CASE'}
    core = [w for w in words if w not in stop and len(w) > 1]
    return ' '.join(core)


def normalize_family(name):
    """Normalize for family-level matching (no color). Used for Buyma matching."""
    if not name:
        return ''
    import re
    n = name.upper()
    n = re.sub(r'\[LUMEN[^\]]*\]|\bLUMEN\s*X\s*[A-Z]+\b|\bATELIER\s+DE\s+LUMEN\b|\bLUMEN\b', ' ', n)
    n = re.sub(r'[\[\]\(\)【】「」]', ' ', n)
    n = re.sub(r'[☆★◆◇■□♥♡●○•・/+&]', ' ', n)
    n = re.sub(r'[가-힣]+', ' ', n)
    n = re.sub(r'[^A-Z0-9\s]', ' ', n)
    n = re.sub(r'\s+', ' ', n).strip()
    words = n.split()
    # Strip color words for family matching
    colors = {'BLACK', 'BROWN', 'WHITE', 'YELLOW', 'GREEN', 'RED', 'BLUE', 'PINK', 'GREY', 'GRAY',
              'SOFT', 'TAN', 'ORGAN', 'EGG', 'MISTY', 'NUBUCK', 'PATTERN', 'SAND', 'CHARCOAL',
              'TAUPE', 'BEIGE', 'IVORY', 'SANDY', 'MELLOW', 'OAK', 'SUEDE', 'MUSTARD',
              'PORCELAIN', 'HAY', 'MUD', 'CARMINE', 'BRUSHED', 'FAWN', 'TAWNY', 'KHAKI',
              'WRINKLE', 'CANVAS', 'DOVE', 'DRIED', 'MATTE', 'VANILLA', 'WALNUT', 'CREAM'}
    stop = {'BAG', 'BAGS', 'COLOR', 'COLORS', 'COLLECTION', 'NEW', 'SS', 'FW', 'AW', 'CASE',
            'SHOES', 'BOOTS', 'BELT', 'WALLET', 'POUCH', 'KEYRING', 'HOLDER', 'NECKLACE',
            'RING', 'CHARM', 'CUFF'}
    core = [w for w in words if w not in colors and w not in stop and len(w) > 1][:4]
    return ' '.join(core)


def cafe24_export_prices():
    """Export all Cafe24 product prices to CSV."""
    mall = os.environ.get('CAFE24_MALL_ID', 'atlm')
    token = os.environ.get('CAFE24_ACCESS_TOKEN')
    if not token:
        print("CAFE24_ACCESS_TOKEN missing. Run --cafe24-auth-url first.")
        return
    base = f"https://{mall}.cafe24api.com/api/v2/admin/products"
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    all_products = []
    offset = 0
    limit = 100
    while True:
        params = {'limit': limit, 'offset': offset, 'fields': 'product_no,product_name,price,retail_price,supply_price,product_code,display'}
        r = requests.get(base, headers=headers, params=params, timeout=30)
        if r.status_code != 200:
            print(f"[ERROR] HTTP {r.status_code}: {r.text}")
            return
        data = r.json()
        products = data.get('products', [])
        if not products:
            break
        all_products.extend(products)
        if len(products) < limit:
            break
        offset += limit
        print(f"  fetched {len(all_products)}...")

    out_path = 'cafe24_prices_krw.csv'
    with open(out_path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['product_no', 'product_code', 'product_name', 'price', 'retail_price', 'supply_price', 'display'])
        for p in all_products:
            w.writerow([p.get('product_no'), p.get('product_code'), p.get('product_name'),
                        p.get('price'), p.get('retail_price'), p.get('supply_price'), p.get('display')])
    print(f"\n[OK] Saved {len(all_products)} products to {out_path}")
    print("\nFirst 15:")
    for p in all_products[:15]:
        print(f"  {p.get('price')} KRW  {p.get('product_name')}")


ALL_PRODUCTS_PRICES_QUERY = """
query ($after: String) {
  products(first: 100, after: $after) {
    edges {
      cursor
      node {
        id
        title
        handle
        status
        variants(first: 5) {
          edges {
            node { title price compareAtPrice }
          }
        }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""


def export_shopify_prices():
    """Export all Shopify product prices to CSV for comparison."""
    print("Fetching all products with prices...")
    cursor = None
    all_rows = []
    while True:
        r = gql(ALL_PRODUCTS_PRICES_QUERY, {'after': cursor})
        for e in r['products']['edges']:
            p = e['node']
            for ve in p['variants']['edges']:
                v = ve['node']
                all_rows.append({
                    'handle': p['handle'],
                    'title': p['title'],
                    'variant': v['title'],
                    'price_usd': v['price'],
                    'compare_at': v.get('compareAtPrice') or '',
                    'status': p['status'],
                })
        if not r['products']['pageInfo']['hasNextPage']:
            break
        cursor = r['products']['pageInfo']['endCursor']

    out_path = 'shopify_prices_usd.csv'
    with open(out_path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['handle', 'title', 'variant', 'price_usd', 'compare_at_usd', 'status'])
        for r in all_rows:
            w.writerow([r['handle'], r['title'], r['variant'], r['price_usd'], r['compare_at'], r['status']])
    print(f"Saved: {out_path} ({len(all_rows)} rows)")
    print(f"\nFirst 15 rows:")
    for r in all_rows[:15]:
        print(f"  ${r['price_usd']:>7}  {r['title']}")


PRICELIST_FIXED_PRICES = """
query ($id: ID!, $after: String) {
  priceList(id: $id) {
    name
    currency
    prices(first: 100, after: $after) {
      edges {
        cursor
        node {
          variant {
            id
            displayName
            product { title handle }
          }
          price { amount currencyCode }
          compareAtPrice { amount currencyCode }
        }
      }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""

JAPAN_PRICELIST_ID = "gid://shopify/PriceList/" # will fill dynamically


def inspect_japan_pricelist():
    print("Step 1: Find Japan PriceList ID...")
    data = gql(CATALOGS_QUERY)
    pl_id = None
    for c in data['catalogs']['nodes']:
        if c.get('priceList') and 'Japan' in (c.get('priceList', {}).get('name') or ''):
            pl_id = c['priceList']['id']
            break
    if not pl_id:
        print("Japan PriceList not found.")
        return
    print(f"Japan PriceList: {pl_id}\n")

    cursor = None
    all_prices = []
    while True:
        r = gql(PRICELIST_FIXED_PRICES, {'id': pl_id, 'after': cursor})
        pl = r['priceList']
        for edge in pl['prices']['edges']:
            n = edge['node']
            all_prices.append({
                'handle': n['variant']['product']['handle'],
                'title': n['variant']['product']['title'],
                'variant': n['variant']['displayName'],
                'amount': n['price']['amount'],
                'currency': n['price']['currencyCode'],
            })
        if not pl['prices']['pageInfo']['hasNextPage']:
            break
        cursor = pl['prices']['pageInfo']['endCursor']

    print(f"Total fixed prices: {len(all_prices)}")
    print(f"PriceList currency: {pl.get('currency')}\n")
    print("First 30 fixed prices:")
    for p in all_prices[:30]:
        print(f"  {p['amount']} {p['currency']}  {p['title']}")

    out_path = 'japan_pricelist.txt'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(f"PriceList currency: {pl.get('currency')}\nTotal fixed prices: {len(all_prices)}\n\n")
        for p in all_prices:
            f.write(f"{p['amount']:>8} {p['currency']}  {p['title']} | {p['handle']}\n")
    print(f"\nSaved: {out_path}")


CATALOGS_QUERY = """
{
  catalogs(first: 30) {
    nodes {
      id
      title
      status
      ... on MarketCatalog {
        markets(first: 5) { nodes { id name handle } }
      }
      priceList {
        id
        name
        currency
        fixedPricesCount
        parent {
          adjustment {
            type
            value
          }
        }
      }
    }
  }
}
"""


def inspect_catalogs():
    print("=== Catalogs & Price Lists ===")
    data = gql(CATALOGS_QUERY)
    out_path = 'catalogs_inspection.txt'
    with open(out_path, 'w', encoding='utf-8') as f:
        for c in data['catalogs']['nodes']:
            line = f"\n[Catalog] {c['title']} ({c['id']}) status={c['status']}"
            print(line)
            f.write(line + "\n")
            for m in (c.get('markets') or {}).get('nodes') or []:
                ml = f"  Market: {m['handle']} ({m['name']})"
                print(ml); f.write(ml + "\n")
            pl = c.get('priceList')
            if pl:
                pll = f"  PriceList: {pl['name']} currency={pl['currency']} fixedPrices={pl.get('fixedPricesCount')}"
                print(pll); f.write(pll + "\n")
                parent = pl.get('parent')
                if parent and parent.get('adjustment'):
                    adj = parent['adjustment']
                    al = f"    Parent adjustment: type={adj.get('type')} value={adj.get('value')}"
                    print(al); f.write(al + "\n")
            else:
                f.write("  (no priceList)\n")
    print(f"\nSaved: {out_path}")


PRODUCT_PRICES_QUERY = """
query ($handle: String!) {
  productByHandle(handle: $handle) {
    title
    variants(first: 10) {
      edges {
        node {
          id
          title
          price
          compareAtPrice
          contextualPricing(context: {country: JP}) {
            price { amount currencyCode }
            compareAtPrice { amount currencyCode }
          }
        }
      }
    }
  }
}
"""


def inspect_product_prices(handle):
    print(f"Checking prices for: {handle}")
    try:
        data = gql(PRODUCT_PRICES_QUERY, {'handle': handle})
    except Exception as e:
        print(f"[ERROR] {e}")
        return
    p = data.get('productByHandle')
    if not p:
        print("Product not found")
        return
    print(f"Product: {p['title']}\n")
    for e in p['variants']['edges']:
        v = e['node']
        print(f"Variant: {v['title']}")
        print(f"  Base price: {v['price']} (shop default currency)")
        cp = v.get('contextualPricing') or {}
        cprice = cp.get('price') or {}
        print(f"  Japan context price: {cprice.get('amount')} {cprice.get('currencyCode')}")


CURRENCIES_ENABLE = """
mutation enable($currencies: [CurrencyCode!]!) {
  currencyActivate: enabledPresentmentCurrenciesUpdate(currencies: $currencies) {
    shop { enabledPresentmentCurrencies currencyCode }
    userErrors { field message }
  }
}
"""


def enable_presentment_jpy():
    """Try to add JPY to enabled presentment currencies (works in non-unified mode)."""
    print("Enabling JPY as presentment currency...")
    try:
        r = gql(CURRENCIES_ENABLE, {'currencies': ['USD', 'JPY']})
    except Exception as e:
        print(f"[ERROR] {e}")
        return
    errs = r['currencyActivate']['userErrors']
    if errs:
        print(f"[ERROR] {errs}")
    else:
        s = r['currencyActivate']['shop']
        print(f"[OK] Enabled presentment currencies: {s['enabledPresentmentCurrencies']}")


MARKET_CURRENCY_UPDATE = """
mutation upd($marketId: ID!, $input: MarketCurrencySettingsUpdateInput!) {
  marketCurrencySettingsUpdate(marketId: $marketId, input: $input) {
    market { id name handle currencySettings { baseCurrency { currencyCode } localCurrencies } }
    userErrors { field message code }
  }
}
"""

SHOP_CURRENCY_ENABLE = """
mutation enable($currencies: [CurrencyCode!]!) {
  shopLocaleEnable: currencyFormatsUpdate(currencyFormats: {moneyFormat: "<span class=money>{{amount_with_comma_separator}}</span>"}) {
    shop { currencyFormats { moneyFormat } }
    userErrors { field message }
  }
}
"""


def enable_japan_jpy():
    """Set Japan market currency to JPY."""
    print("Step 1: Find Japan market...")
    data = gql(MARKETS_QUERY)
    japan = None
    for m in data['markets']['nodes']:
        if m['handle'] == 'japan' or m['name'].lower() == 'japan':
            japan = m
            break
    if not japan:
        print("Japan market not found.")
        return
    print(f"Found: {japan['name']} ({japan['id']})")
    cur_base = (japan.get('currencySettings') or {}).get('baseCurrency')
    print(f"Current base currency: {cur_base}")

    print("\nStep 2: Update Japan market currency to JPY...")
    r = gql(MARKET_CURRENCY_UPDATE, {
        'marketId': japan['id'],
        'input': {
            'baseCurrency': 'JPY',
            'localCurrencies': False,
        }
    })
    errs = r['marketCurrencySettingsUpdate']['userErrors']
    if errs:
        print(f"[ERROR] {errs}")
        return
    m = r['marketCurrencySettingsUpdate']['market']
    print(f"[OK] {m['handle']} base currency = {m['currencySettings']['baseCurrency']['currencyCode']}")
    print(f"  localCurrencies enabled: {m['currencySettings']['localCurrencies']}")


SHOP_CURRENCY_QUERY = """
{
  shop {
    name
    myshopifyDomain
    primaryDomain { url }
    currencyCode
    enabledPresentmentCurrencies
    currencyFormats {
      moneyFormat
      moneyWithCurrencyFormat
    }
  }
}
"""


def inspect_shop_currency():
    print("=== Shop Currency / Payment Settings ===")
    data = gql(SHOP_CURRENCY_QUERY)
    s = data['shop']
    print(f"Shop: {s['name']} ({s['myshopifyDomain']})")
    print(f"Primary domain: {s.get('primaryDomain', {}).get('url')}")
    print(f"Shop base currency: {s.get('currencyCode')}")
    print(f"Enabled presentment currencies: {s.get('enabledPresentmentCurrencies')}")
    cf = s.get('currencyFormats') or {}
    print(f"Money format: {cf.get('moneyFormat')}")
    print(f"Money with currency: {cf.get('moneyWithCurrencyFormat')}")


MARKETS_QUERY = """
{
  markets(first: 20) {
    nodes {
      id
      name
      handle
      primary
      enabled
      regions(first: 10) { nodes { ... on MarketRegionCountry { code name currency { currencyCode } } } }
      currencySettings {
        baseCurrency { currencyCode enabled rateUpdatedAt }
        localCurrencies
      }
      webPresence { rootUrls { url locale } }
    }
  }
}
"""


def inspect_markets():
    print("=== Markets Configuration ===")
    data = gql(MARKETS_QUERY)
    out_path = 'markets_inspection.txt'
    with open(out_path, 'w', encoding='utf-8') as f:
        for m in data['markets']['nodes']:
            line = f"\n[{m['handle']}] {m['name']} (primary={m['primary']}, enabled={m['enabled']})"
            print(line)
            f.write(line + "\n")
            cs = m.get('currencySettings') or {}
            base = cs.get('baseCurrency') or {}
            lc_info = f"  baseCurrency: {base.get('currencyCode')} enabled={base.get('enabled')}"
            f.write(lc_info + "\n")
            print(lc_info)
            local_info = f"  localCurrencies enabled: {cs.get('localCurrencies')}"
            f.write(local_info + "\n")
            print(local_info)
            for region in (m.get('regions') or {}).get('nodes') or []:
                rs = f"    region: {region.get('code')} ({region.get('name')}) currency={(region.get('currency') or {}).get('currencyCode')}"
                f.write(rs + "\n")
                print(rs)
            for url in (m.get('webPresence') or {}).get('rootUrls') or []:
                f.write(f"    url: {url.get('url')} ({url.get('locale')})\n")
    print(f"\nSaved: {out_path}")


def inspect_metaobject_definitions():
    """Print all metaobject definitions and their entries."""
    print("=== Metaobject Definitions ===")
    data = gql(METAOBJECT_DEFINITIONS_QUERY)
    defs = data['metaobjectDefinitions']['nodes']
    out_path = 'metaobject_inspection.txt'
    with open(out_path, 'w', encoding='utf-8') as f:
        for d in defs:
            line = f"\n[{d['type']}] {d['name']} ({d['id']})"
            print(line)
            f.write(line + "\n")
            for fd in d['fieldDefinitions']:
                fl = f"  field: {fd['key']} ({fd['name']}) type={fd['type']['name']} required={fd['required']}"
                print(fl)
                f.write(fl + "\n")
            # Fetch entries for key types we care about
            if d['type'] in ('payment_delivery', 'exchange_refund', 'warranty', '$app:payment_delivery', '$app:exchange_refund'):
                try:
                    entries = gql(METAOBJECT_BY_TYPE_QUERY, {'type': d['type']})['metaobjects']['nodes']
                    f.write(f"  ENTRIES ({len(entries)}):\n")
                    for e in entries:
                        f.write(f"    - {e['handle']} ({e['id']})\n")
                        for ff in e['fields']:
                            v = (ff.get('value') or '')[:80]
                            f.write(f"        {ff['key']} = {v}\n")
                    print(f"  ({len(entries)} entries)")
                except Exception as ex:
                    print(f"  [ERR fetching entries] {ex}")
    print(f"\nSaved: {out_path}")


def jp_update_batch(filt='all', limit=None, apply=False):
    """Process multiple products: translate body+details, write japan_* metafields."""
    print(f"=== JP Update Batch: filter={filt}, limit={limit}, apply={apply} ===")
    print("Fetching all PRODUCT translatable resources...")
    prods = fetch_resources('PRODUCT')

    # Filter by title
    targets = []
    for p in prods:
        en_title = ''
        for c in p['translatableContent']:
            if c['key'] == 'title':
                en_title = c['value'] or ''
                break
        if filt == 'ihnn' and 'IHNN' not in en_title.upper():
            continue
        if filt == 'non-ihnn' and 'IHNN' in en_title.upper():
            continue
        # 'all' falls through
        # extract gid suffix as ID for handle lookup later
        targets.append({'gid': p['resourceId'], 'title': en_title})

    if limit:
        targets = targets[:limit]

    print(f"Targets: {len(targets)}")
    for t in targets[:30]:
        print(f"  - {t['title']}")
    if len(targets) > 30:
        print(f"  ... and {len(targets)-30} more")

    if not apply:
        print(f"\n[DRY-RUN — no apply] Add --apply to process these {len(targets)} products.")
        return

    # Need handles - fetch via product gid
    PRODUCT_HANDLE_QUERY = """
    query getHandle($id: ID!) {
      product(id: $id) {
        handle
        title
      }
    }
    """

    succeeded = 0
    failed = []
    for i, t in enumerate(targets, 1):
        try:
            h_data = gql(PRODUCT_HANDLE_QUERY, {'id': t['gid']})
            handle = h_data['product']['handle']
            print(f"\n[{i}/{len(targets)}] {t['title']} ({handle})")
            jp_update(handle, apply=True)
            succeeded += 1
        except Exception as e:
            print(f"  [ERROR] {e}")
            failed.append({'gid': t['gid'], 'title': t['title'], 'error': str(e)})

    print(f"\n=== Done ===")
    print(f"Succeeded: {succeeded}/{len(targets)} | Failed: {len(failed)}")
    if failed:
        with open('jp_batch_failed.json', 'w', encoding='utf-8') as f:
            json.dump(failed, f, ensure_ascii=False, indent=2)
        print("Failed items saved to jp_batch_failed.json")


def jp_revert(handle):
    """Restore japan metafields from jp_backup_<handle>.json."""
    backup_path = f'jp_backup_{handle}.json'
    if not os.path.exists(backup_path):
        print(f"Backup not found: {backup_path}")
        return
    with open(backup_path, 'r', encoding='utf-8') as f:
        b = json.load(f)
    print(f"Reverting {handle} ({b['product_id']})...")
    metafield_inputs = []
    if b.get('had_japan_decription'):
        metafield_inputs.append({
            'ownerId': b['product_id'],
            'namespace': 'custom',
            'key': 'japan_product_decription',
            'type': 'multi_line_text_field',
            'value': b['japan_product_decription'],
        })
    if b.get('had_japan_details'):
        metafield_inputs.append({
            'ownerId': b['product_id'],
            'namespace': 'custom',
            'key': 'japan_product_details',
            'type': 'multi_line_text_field',
            'value': b['japan_product_details'],
        })
    if not metafield_inputs:
        print("Nothing to revert (no original values stored).")
        return
    r = gql(METAFIELDS_SET, {'metafields': metafield_inputs})
    errs = r['metafieldsSet']['userErrors']
    if errs:
        print(f"[ERROR] {errs}")
    else:
        for m in r['metafieldsSet']['metafields']:
            print(f"  [OK] {m['namespace']}.{m['key']} reverted ({len(m['value'])} chars)")


def get_main_theme():
    data = gql(THEMES_QUERY)
    themes = data['themes']['nodes']
    return next((t for t in themes if t['role'] == 'MAIN'), None)


def fetch_theme_file_content(theme_id, filename):
    cursor = None
    while True:
        r = gql(THEME_FILES_QUERY, {'id': theme_id, 'after': cursor})
        for n in r['theme']['files']['nodes']:
            if n['filename'] == filename:
                return (n.get('body') or {}).get('content') or ''
        info = r['theme']['files']['pageInfo']
        if not info['hasNextPage']:
            return None
        cursor = info['endCursor']


def prepare_theme_mod():
    """Save current info-drawers.liquid + proposed version. Do NOT apply."""
    main = get_main_theme()
    if not main:
        print("No main theme.")
        return
    print(f"Theme: {main['name']} ({main['id']})")
    filename = 'snippets/info-drawers.liquid'
    content = fetch_theme_file_content(main['id'], filename)
    if content is None:
        print(f"File not found: {filename}")
        return

    backup_path = f'theme_BEFORE_{filename.replace("/", "_")}.txt'
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Saved BEFORE: {backup_path} ({len(content)} chars)")

    # Build proposed modification using regex on the full product_details block.
    # Pattern matches the entire if/endif block including the <div> wrapper.
    pattern = re.compile(
        r"({%-\s*if\s+product\.metafields\.custom\.product_details\s*!=\s*blank\s*-%}\s*\n)"
        r"(\s*<div class=\"pd-details__text\">\s*\n)"
        r"(\s*\{\{\s*product\.metafields\.custom\.product_details\.value\s*\}\}\s*\n)"
        r"(\s*</div>\s*\n)"
        r"(\s*\{%-\s*endif\s*-%\})"
    )
    m = pattern.search(content)
    if not m:
        print("[ERROR] Could not locate the product_details block with expected structure.")
        print("Open theme_BEFORE_*.txt and check L53-L57 area.")
        return

    indent_div = m.group(2).split('<')[0]   # leading whitespace before <div>
    indent_value = m.group(3).split('{{')[0]
    indent_div_close = m.group(4).split('</')[0]
    indent_endif = m.group(5).split('{%-')[0]

    new_block = (
        m.group(1) +  # original {%- if ... product_details ... -%}
        # Replace the if condition with japan branch first
        ''
    )

    # Build replacement: keep formatting exactly; add japan branch wrapping the same <div> structure
    replacement = (
        f"{{%- if localization.market.handle == 'japan' and product.metafields.custom.japan_product_details != blank -%}}\n"
        f"{indent_div}<div class=\"pd-details__text\">\n"
        f"{indent_value}{{{{ product.metafields.custom.japan_product_details.value }}}}\n"
        f"{indent_div_close}</div>\n"
        f"{indent_endif}{{%- elsif product.metafields.custom.product_details != blank -%}}\n"
        f"{indent_div}<div class=\"pd-details__text\">\n"
        f"{indent_value}{{{{ product.metafields.custom.product_details.value }}}}\n"
        f"{indent_div_close}</div>\n"
        f"{indent_endif}{{%- endif -%}}"
    )

    proposed = content[:m.start()] + replacement + content[m.end():]

    proposed_path = f'theme_PROPOSED_{filename.replace("/", "_")}.txt'
    with open(proposed_path, 'w', encoding='utf-8') as f:
        f.write(proposed)
    print(f"Saved PROPOSED: {proposed_path} ({len(proposed)} chars)")

    # Save diff snippet showing the modified region
    # Find the block area in original and proposed
    diff_path = f'theme_DIFF_{filename.replace("/", "_")}.txt'
    with open(diff_path, 'w', encoding='utf-8') as f:
        f.write("=== BEFORE (current) ===\n")
        # Show lines around product_details
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if 'product_details' in line:
                start = max(0, i - 4)
                end = min(len(lines), i + 4)
                for j in range(start, end):
                    f.write(f"  L{j+1}: {lines[j]}\n")
                f.write("\n")
        f.write("\n=== AFTER (proposed) ===\n")
        plines = proposed.split('\n')
        for i, line in enumerate(plines, 1):
            if 'product_details' in line:
                start = max(0, i - 4)
                end = min(len(plines), i + 4)
                for j in range(start, end):
                    f.write(f"  L{j+1}: {plines[j]}\n")
                f.write("\n")
    print(f"Saved DIFF: {diff_path}")
    print(f"\n>>> Review {diff_path} carefully. Then run --apply-theme-mod to push.")


def apply_theme_mod():
    """Push proposed file to theme."""
    main = get_main_theme()
    if not main:
        print("No main theme.")
        return
    filename = 'snippets/info-drawers.liquid'
    proposed_path = f'theme_PROPOSED_{filename.replace("/", "_")}.txt'
    if not os.path.exists(proposed_path):
        print(f"Proposed file missing: {proposed_path}. Run --prepare-theme-mod first.")
        return
    with open(proposed_path, 'r', encoding='utf-8') as f:
        new_content = f.read()
    print(f"Applying {len(new_content)} chars to {filename}...")
    r = gql(THEME_FILES_UPSERT, {
        'themeId': main['id'],
        'files': [{
            'filename': filename,
            'body': {'type': 'TEXT', 'value': new_content},
        }]
    })
    errs = r['themeFilesUpsert']['userErrors']
    if errs:
        print(f"[ERROR] {errs}")
    else:
        print(f"[OK] Theme file updated: {filename}")
        print("To revert, copy theme_BEFORE_*.txt to theme_PROPOSED_*.txt and run --apply-theme-mod again.")


def create_jp_details_metafield_definition():
    """Create custom.japan_product_details metafield definition for products."""
    print("Creating metafield definition: custom.japan_product_details (Product)")
    r = gql(METAFIELD_DEF_CREATE, {
        'definition': {
            'name': 'JAPAN Product Details',
            'namespace': 'custom',
            'key': 'japan_product_details',
            'description': 'Japan market PRODUCT DETAILS panel content (multi-line text). Used by theme when localization.market.handle == japan.',
            'type': 'multi_line_text_field',
            'ownerType': 'PRODUCT',
            'access': {'storefront': 'PUBLIC_READ'},
        }
    })
    errs = r['metafieldDefinitionCreate']['userErrors']
    if errs:
        # check if already exists
        already = any('TAKEN' in (e.get('code') or '') or 'taken' in e.get('message', '').lower() for e in errs)
        if already:
            print(f"[OK] Already exists: custom.japan_product_details")
            return
        print(f"[ERROR] {errs}")
    else:
        d = r['metafieldDefinitionCreate']['createdDefinition']
        print(f"[OK] Created: {d['name']} ({d['namespace']}.{d['key']}) id={d['id']}")


def read_theme_file(filename):
    print(f"Reading theme file: {filename}")
    data = gql(THEMES_QUERY)
    themes = data['themes']['nodes']
    main = next((t for t in themes if t['role'] == 'MAIN'), None)
    if not main:
        print("No main theme.")
        return
    cursor = None
    while True:
        r = gql(THEME_FILES_QUERY, {'id': main['id'], 'after': cursor})
        for n in r['theme']['files']['nodes']:
            if n['filename'] == filename:
                content = (n.get('body') or {}).get('content') or ''
                out = f'theme_file_{re.sub(r"[^a-z0-9_.]", "_", filename.lower())}.txt'
                with open(out, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Saved: {out} ({len(content)} chars)")
                return
        info = r['theme']['files']['pageInfo']
        if not info['hasNextPage']:
            break
        cursor = info['endCursor']
    print(f"File not found: {filename}")


def inspect_theme(keyword):
    print(f"Searching theme code for: '{keyword}'")
    try:
        data = gql(THEMES_QUERY)
    except Exception as e:
        print(f"[ERROR] {e}")
        print("Need 'read_themes' scope on the app. Add it in Dev Dashboard.")
        return

    themes = data['themes']['nodes']
    main = next((t for t in themes if t['role'] == 'MAIN'), themes[0] if themes else None)
    if not main:
        print("No theme found.")
        return
    print(f"Main theme: {main['name']} ({main['id']})")

    matches = []
    cursor = None
    files_scanned = 0
    while True:
        try:
            r = gql(THEME_FILES_QUERY, {'id': main['id'], 'after': cursor})
        except Exception as e:
            print(f"[ERROR fetching files] {e}")
            return
        nodes = r['theme']['files']['nodes']
        for n in nodes:
            files_scanned += 1
            body = n.get('body') or {}
            content = body.get('content') or ''
            if not content:
                continue
            if keyword.lower() in content.lower():
                # Find matching lines
                lines = content.split('\n')
                hits = []
                for i, line in enumerate(lines, 1):
                    if keyword.lower() in line.lower():
                        hits.append((i, line.strip()))
                matches.append({'filename': n['filename'], 'hits': hits})
        info = r['theme']['files']['pageInfo']
        if not info['hasNextPage']:
            break
        cursor = info['endCursor']

    print(f"Scanned {files_scanned} files. Matches: {len(matches)}")
    out_path = f'theme_search_{re.sub(r"[^a-z0-9_]", "_", keyword.lower())}.txt'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(f"Search keyword: {keyword}\n")
        f.write(f"Theme: {main['name']}\n")
        f.write(f"Files scanned: {files_scanned}\n")
        f.write(f"Matching files: {len(matches)}\n\n")
        for m in matches:
            f.write(f"=== {m['filename']} ===\n")
            for ln, line in m['hits']:
                f.write(f"  L{ln}: {line}\n")
            f.write("\n")
    print(f"Saved: {out_path}")
    for m in matches[:20]:
        print(f"  - {m['filename']} ({len(m['hits'])} hits)")


INSPECT_QUERY = """
query inspect($id: ID!) {
  product(id: $id) {
    id
    title
    handle
    descriptionHtml
    metafields(first: 50) {
      edges {
        node {
          id
          namespace
          key
          type
          value
          definition { name }
        }
      }
    }
  }
  translatableResource(resourceId: $id) {
    resourceId
    translatableContent { key value digest type locale }
    translations(locale: "ja") { key value }
  }
}
"""


def inspect_product(gid):
    print(f"Inspecting {gid}...")
    data = gql(INSPECT_QUERY, {'id': gid})
    p = data.get('product')
    tr = data.get('translatableResource')
    out_path = 'inspect_product.txt'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(f"=== PRODUCT BASIC ===\n")
        if p:
            f.write(f"id: {p['id']}\n")
            f.write(f"title: {p['title']}\n")
            f.write(f"handle: {p['handle']}\n")
            f.write(f"descriptionHtml ({len(p.get('descriptionHtml') or '')} chars):\n")
            f.write(f"{p.get('descriptionHtml')}\n\n")
            f.write(f"=== METAFIELDS ({len(p['metafields']['edges'])}) ===\n")
            for e in p['metafields']['edges']:
                n = e['node']
                defname = (n.get('definition') or {}).get('name') or ''
                v = n['value'] or ''
                f.write(f"\n[{n['namespace']}.{n['key']}] type={n['type']} def={defname}\n")
                f.write(f"  id: {n['id']}\n")
                f.write(f"  value ({len(v)} chars): {v[:500]}\n")
                if len(v) > 500:
                    f.write(f"  ... [truncated, total {len(v)} chars]\n")
        else:
            f.write("(not found)\n")

        f.write(f"\n\n=== TRANSLATABLE RESOURCE (PRODUCT level) ===\n")
        if tr:
            for c in tr['translatableContent']:
                v = c.get('value') or ''
                f.write(f"\n[key={c['key']}] type={c.get('type')} digest={c.get('digest')[:16]}...\n")
                f.write(f"  value ({len(v)} chars): {v[:300]}\n")
            f.write(f"\n--- existing JA translations ---\n")
            for t in (tr.get('translations') or []):
                v = t.get('value') or ''
                f.write(f"  [{t['key']}] {v[:200]}\n")
        else:
            f.write("(not found)\n")
    print(f"Saved: {out_path}")
    # Also print a short summary
    if p:
        print(f"  title: {p['title']}")
        print(f"  metafields: {len(p['metafields']['edges'])}")
    if tr:
        print(f"  translatable keys: {[c['key'] for c in tr['translatableContent']]}")


def run_phase_metaobjects(locale='ja', dry_run=False, preview=False, limit=None):
    """Translate METAOBJECT content (e.g., Material Info / COW LEATHER paragraphs)."""
    label = 'METAOBJECTS'
    print(f"=== Phase: {label} ===")
    print("Fetching all METAOBJECT resources...")
    objs = fetch_resources('METAOBJECT')
    print(f"Total METAOBJECT resources: {len(objs)}")

    targets = []
    skipped = 0
    for o in objs:
        ja_existing_map = {t['key']: t['value'] for t in (o.get('translations') or [])}
        for c in o['translatableContent']:
            v = c['value'] or ''
            s = v.strip()
            if not s:
                continue
            # Skip color-name-only and very short label-only values
            if len(s) < 5:
                skipped += 1
                continue
            # Skip JSON/code blobs
            if s.startswith(('{', '[', '/*', '<!--')):
                skipped += 1
                continue
            targets.append({
                'resource_id': o['resourceId'],
                'key': c['key'],
                'value': v,
                'digest': c['digest'],
                'en_title': f"{o['resourceId'].split('/')[-1]} ({c['key']})",
                'ja_old': ja_existing_map.get(c['key'], ''),
            })

    print(f"Skipped: {skipped}")
    print(f"Translatable targets: {len(targets)}")

    if limit:
        targets = targets[:limit]

    if dry_run:
        for t in targets[:30]:
            v = t['value'].replace('\n', ' ')[:80]
            print(f"  - {t['en_title']} | {len(t['value'])} chars | {v}...")
        print("[dry-run] No translation. No registration.")
        return

    if not targets:
        print("Nothing to do.")
        return

    BATCH_SIZE = 5
    total_in = total_out = total_cr = total_cw = 0
    succeeded = 0
    failed = []
    all_translations = []

    for batch_start in range(0, len(targets), BATCH_SIZE):
        batch = targets[batch_start:batch_start + BATCH_SIZE]
        items = [t['value'] for t in batch]
        try:
            translations, usage = translate_batch(items, 'product detail / material content')
        except Exception as e:
            print(f"  [batch {batch_start}] failed: {e}")
            failed.extend(batch)
            continue

        all_translations.extend(translations)
        total_in += usage.input_tokens
        total_out += usage.output_tokens
        total_cr += getattr(usage, 'cache_read_input_tokens', 0) or 0
        total_cw += getattr(usage, 'cache_creation_input_tokens', 0) or 0

        if not preview:
            for t, ja_value in zip(batch, translations):
                try:
                    res = register_translation(
                        resource_id=t['resource_id'],
                        key=t['key'],
                        locale=locale,
                        value=ja_value,
                        translatable_content_digest=t['digest'],
                    )
                    errs = res['translationsRegister']['userErrors']
                    if errs:
                        print(f"  [WARN] {t['en_title']}: {errs}")
                        failed.append(t)
                    else:
                        succeeded += 1
                except Exception as e:
                    print(f"  [ERROR] {t['en_title']}: {e}")
                    failed.append(t)

        done = min(batch_start + BATCH_SIZE, len(targets))
        print(f"  Progress: {done}/{len(targets)}")

    cost = (total_in*3 + total_out*15 + total_cr*0.30 + total_cw*3.75) / 1_000_000

    if preview:
        out_path = f'preview_{label.lower()}.txt'
        with open(out_path, 'w', encoding='utf-8') as f:
            for i, (t, ja_new) in enumerate(zip(targets, all_translations), 1):
                f.write(f"=== {i}. {t['en_title']} ===\n\n")
                f.write(f"[ENGLISH]\n{t['value']}\n\n")
                f.write(f"[OLD JA]\n{t['ja_old']}\n\n")
                f.write(f"[NEW JA (LUMEN tone)]\n{ja_new}\n\n")
                f.write("=" * 80 + "\n\n")
        print(f"\n[PREVIEW] Saved to: {out_path}")

    print(f"\n=== Done: {label} ===")
    print(f"Succeeded: {succeeded}/{len(targets)} | Failed: {len(failed)}")
    print(f"Tokens: in={total_in} out={total_out} cache_read={total_cr} cache_write={total_cw}")
    print(f"Estimated cost: ${cost:.3f}")


if __name__ == '__main__':
    main()
