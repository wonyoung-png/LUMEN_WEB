# CLAUDE.md — LUMEN_WEB 프로젝트 컨텍스트
> intl.atlm.kr (Shopify 글로벌몰) 전담 세션 지침
> 마지막 업데이트: 2026-05-22

---

## 스토어 기본 정보

| 항목 | 값 |
|------|-----|
| 스토어 URL | https://intl.atlm.kr |
| Shopify Store ID | h3id7y-ij |
| 플랜 | Shopify (기본) |
| 이메일 발송 | Shopify Email (내장) — 외부 ESP 없음 |
| 주요 시장 | JP / SG / HK / US |
| 통화 | USD |

---

## 폴더 구조

```
LUMEN_WEB/
├── CLAUDE.md              ← 이 파일 (세션 컨텍스트)
├── SESSION_START.md       ← 새 세션 시작용 붙여넣기 프롬프트
├── reports/               ← 분석 보고서 (YYYY-MM-DD_내용.md)
├── schemas/               ← SEO JSON-LD 스키마 파일
├── seo/                   ← SEO 관련 파일
└── shopify/               ← Shopify 작업 파일
    ├── popup/             ← 팝업 폼 관련
    ├── email/             ← 이메일 자동화
    ├── theme/             ← 테마 liquid 스니펫
    └── scripts/           ← Python 자동화 스크립트
```

---

## 진행 중인 작업 현황 (2026-05-22 기준)

### 1. SEO / AIO — Phase 1 [진행 중]
- **최우선**: 제품 페이지 Product 스키마 (JSON-LD) 삽입
- Shopify 테마에 `product.liquid` 수정 필요
- 참고 스키마: `schemas/` 폴더

### 2. Welcome 팝업 폼 [진행 중]
- **디자인 레퍼런스**: `C:\Users\이원영 AMES\Downloads\lumen_welcome_popup.html`
- 사양: 920×647px, 좌 613px 이미지 / 우 307px 폼, 배경 #F6F5EE
- 헤딩: Cormorant Garamond 54px Light, "$10 / Store / Credit"
- 현재 상태: Klaviyo Form UnKPet 초안 작업 중 (`https://www.klaviyo.com/forms/UnKPet/edit`)
- **주의**: 절대 활성화(Publish) 클릭 금지 — 초안 상태 유지

### 3. Welcome 이메일 자동화 [대기]
- Shopify Email(내장)로 웰컴 시리즈 운영
- 트리거: 이메일 마케팅 구독 시 즉시
- EN / JP 분기 필요
- JP 이메일 제목: `初回ご注文時、チェックアウトで自動適用される$10ストアクレジットをご用意しました。`
- 혜택: $10 store credit (별도 쿠폰 코드 없음, 계정 로그인 시 자동 적용)

### 4. 일본어 번역 [완료 → 재적용 필요]
- 스크립트: `C:\Users\이원영 AMES\Downloads\lumen_auto_translate.py`
- 자격증명: `C:\Users\이원영 AMES\Downloads\.env`
- 입력 백업: `C:\Users\이원영 AMES\Downloads\Atelier_de_LUMEN_translations_TITLES_FIXED.csv`
- Translate & Adapt 앱으로 최종 업로드
- 번역 품질 기준: The Row / Lemaire / Loewe 수준 럭셔리 톤

### 5. 테마 커스터마이즈 [완료]
- 국가 선택기(Country Selector) 스니펫 적용 완료
- 파일: `C:\Users\이원영 AMES\Downloads\theme_file_snippets_lumen_country_selector.liquid.txt`
- JS: `C:\Users\이원영 AMES\Downloads\theme_file_snippets_lumen_country_selector_js.liquid.txt`

### 6. Meta 광고 n8n 자동화 [미완료]
- 플랫폼: atlm.app.n8n.cloud
- 워크플로 4개 구축 완료, Meta 토큰 교체 + 활성화 미완

---

## 주요 결정사항 (변경 금지)

| 결정 | 내용 |
|------|------|
| ESP | Shopify Email 단독 운영. Klaviyo 이메일 삭제됨. 외부 ESP 제안 금지 |
| 리뷰 섹션 | intl.atlm.kr에 리뷰 섹션 없음 (의도적). 다시 제안 금지 |
| $10 크레딧 방식 | 쿠폰 코드 없음. Shopify 계정 로그인 시 자동 적용 |
| 이미지 CDN | https://intl.atlm.kr/cdn/shop/files/ |

---

## 자격증명 / 환경변수 위치

> 절대 코드에 하드코딩 금지. 항상 .env 파일 참조.

- `.env` 파일: `C:\Users\이원영 AMES\Downloads\.env`
- 포함된 키: `ANTHROPIC_API_KEY`, `SHOPIFY_CLIENT_ID`, `SHOPIFY_CLIENT_SECRET`, `SHOPIFY_STORE`
- Shopify Custom App 이름: `ATLM_REVISE_API`

---

## Shopify Admin API 상태

- **문제**: Access Token 발급 이력 있으나 재확인 필요
- **이슈**: HTTP 400 Bad Request (앱 Install 단계 누락 의심)
- 해결 흐름: 앱 만들기 → Scope 설정 → 릴리스 → 스토어에 Install → Token 발급
- 필요 Scope: `write_translations`, `read_translations`, `read_locales`, `read_products`

---

## 세션 시작 체크리스트

1. `git pull origin main` — 최신 상태 동기화
2. `reports/` 폴더 — 최신 보고서 확인
3. `schemas/` 폴더 — 작업된 스키마 확인
4. 위 "진행 중인 작업 현황" 최우선 항목부터 착수

---

## 작업 원칙

- 보고서 저장: `reports/YYYY-MM-DD_내용.md`
- 스키마 저장: `schemas/파일명.json`
- Shopify 작업 파일: `shopify/` 하위 분류
- 커밋 메시지: 한국어 간결하게
- 작업 후: `git add . && git commit -m "내용" && git push`
- Klaviyo 폼은 절대 Publish/활성화 금지 (초안 유지)
