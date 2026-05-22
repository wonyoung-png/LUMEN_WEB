# intl.atlm.kr 기술 스택 감사 보고서 (BuiltWith + Shopify Admin)
> 작성일: 2026-05-22
> 출처: BuiltWith 기술 프로파일 + Shopify Admin 앱 목록 직접 확인

---

## 총평

| 지표 | 현황 | 평가 |
|------|------|------|
| 설치된 앱 수 | **28개** | 🔴 과다 (권장 10개 이하) |
| 팝업/이메일 수집 앱 | **5개 중복** | 🔴 심각 |
| 할인/가격 앱 | 2개 중복 | 🟡 |
| BuiltWith AI Index | 48/100 (Low) | 🟡 |
| 유료 앱 추정 비용 | 연 $600~900 추정 | 🟡 낭비 |
| 프론트 스크립트 주입 앱 | 10개+ | 🔴 속도 저하 |

핵심 문제는 **앱 과부하**. 같은 기능을 하는 앱이 여러 개 깔려 있어 (1) 사이트 속도 저하 (2) 월 구독료 누수 (3) 팝업 충돌 위험이 발생.

---

## 설치된 앱 전체 목록 (28개)

### 🔴 중복 1: 팝업 / 이메일 수집 (5개 — 1개로 통합 필요)

| 앱 | 기능 | 상태 |
|----|------|------|
| Klaviyo: Email Marketing & SMS | 팝업 폼(UnKPet) + 트래킹 | 사용 중 (팝업 작업 중) |
| Adoric Pop Ups & Email Popup | 팝업 | **좀비 의심** |
| SendWILL Email Popups | 팝업 | **좀비 의심** |
| Forms (Shopify Forms) | 폼/팝업 | 중복 |
| Essential Announcer | 공지 바 | 팝업 인접 기능 |

→ BuiltWith가 "Adoric" 기술을 감지한 것은 Adoric 앱이 실제로 스토어프론트에 스크립트를 주입하고 있다는 의미. **팝업 작업은 Klaviyo로 일원화 결정됨 → Adoric, SendWILL 제거 대상.**

### 🔴 중복 2: 할인 / 가격 (2개)

| 앱 | 비용 | 비고 |
|----|------|------|
| Rubix Bulk Price Editor | 30일마다 $14.95 | 시즌 세일가 일괄 수정용 |
| Discounty | - | 할인 자동화 |

→ 둘 다 상시 필요한지 검토. 시즌 세팅 끝나면 Rubix 일시정지로 월 $14.95 절약 가능.

### 🟡 결제 관련 (3개)

| 앱 | 비고 |
|----|------|
| Paymentwall - Credit Cards | 결제 게이트웨이 |
| Stripe Subscriptions | **구독 상품 판매 안 하면 좀비** — 핸드백몰에 구독 불필요 |
| BUCKS | 통화 컨버터, 연 $76.75 |

### 🟡 커스텀 앱 (4개 — 정리 필요)

| 앱 | 상태 |
|----|------|
| ATLM_REVISE_API | **Markets 호환 안 됨 경고 표시** — 번역 API용, 점검 필요 |
| ATLM-Data-API | 용도 확인 필요 |
| lumen-2026 | 용도 확인 필요 |
| Shopify Claude Connector App | MCP 연동용 (유지) |

→ 커스텀 앱 4개 중복. ATLM_REVISE_API는 CLAUDE.md에 기재된 토큰 발급 실패 이슈 앱. 사용 안 하는 커스텀 앱은 권한 회수 차원에서 정리.

### 🟢 정상 사용 중 (유지)

| 앱 | 기능 |
|----|------|
| Messaging | Shopify Email (공식 ESP) |
| Microsoft Clarity | 히트맵 분석 |
| BLOY Loyalty Rewards | 적립금/로열티 |
| Flow | Shopify 자동화 |
| Translate & Adapt | 일본어 번역 |
| Search & Discovery | 검색/필터/추천 |
| Orbe Geolocation | 국가 자동 감지 |
| HIKO Social Login | 소셜 로그인 |
| Channel Talk | 라이브챗 (유료 — 실사용 확인 필요) |
| バクアゲ 住所チェック | 일본 주소 검증 (JP 시장 필수) |
| Matrixify | 대량 import/export |
| Knowledge Base / WISE COMMERCE / Revize / Essential Announcer | 용도 확인 필요 |

---

## BuiltWith 기술 분석 상세

### 정상 적용된 항목 ✓
- Shopify (Dawn 테마 기반)
- hreflang: 영어 + 일본어 양방향 ✓
- Canonical 태그 ✓
- Open Graph + Twitter Cards ✓
- JSON-LD: **Organization 스키마만** 감지
- Meta Description / H1 / H2 ✓
- Google Webmaster 등록 ✓
- 이미지 최적화: srcset, picture element, priority hints ✓
- JS defer, JS modules ✓ (성능 양호)

### 미흡 / 수정 항목

**1. Product 스키마 없음 (최우선)**
- 현재 JSON-LD는 Organization 스키마만 존재
- Product 스키마(가격·재고·SKU) 없음 → 구글 쇼핑 리치결과 / AI 답변 노출 불가
- 조치: `product.liquid`에 Product JSON-LD 삽입 (SEO Phase 1)

**2. AI Index 48/100 분석**

| 세부 지표 | 점수 | 해석 |
|-----------|------|------|
| AI Openness | 100 | 크롤러 차단 없음 ✓ |
| AI Visibility | 90 | 메타/콘텐츠 읽기 가능 ✓ |
| AI Maturity | **0** | 구조화 데이터 깊이 부족 |
| Agent Readiness | **0** | llms.txt 없음, AI 친화 엔드포인트 없음 |

→ Maturity·Agent Readiness 0점이 평균을 깎음. 해결책:
   - Product / BreadcrumbList / WebSite(SearchAction) 스키마 추가
   - `llms.txt` 파일 루트에 배치 (AI 크롤러용 사이트 안내)
   - FAQ 스키마 (FAQPage)

**3. X-UA-Compatible 태그**
- 구형 IE 호환 메타 태그 잔존 (Dawn 테마 기본값)
- 기능 문제는 없으나 불필요 — 정리하면 깔끔

**4. hreflang 시장 커버리지**
- 현재: EN + JA
- 목표 시장 SG(영어)·HK(번체)·US(영어)
- SG/US는 영어로 커버됨. HK는 번체 중국어 번역이 없으면 hreflang 추가 의미 없음 → 번역 우선순위 결정 후 진행

---

## 속도 영향 분석

스토어프론트에 JavaScript를 주입하는 앱이 10개 이상:
Klaviyo · Adoric · SendWILL · Clarity · BLOY · Channel Talk · BUCKS · Orbe · Essential Announcer · HIKO 등

- 앱마다 50~300ms 로드 추가 → 누적 시 LCP/TBT 직접 악화
- 특히 **팝업 앱 3개 동시 로드**는 명백한 낭비
- Adoric + SendWILL 제거만으로 체감 속도 개선 예상

---

## 실행 우선순위

| 순위 | 작업 | 효과 | 난이도 | 승인 |
|------|------|------|--------|------|
| 1 | Adoric 제거 | 속도↑ + 팝업충돌 제거 | 5분 | 대표 확인 |
| 2 | SendWILL Email Popups 제거 | 속도↑ | 5분 | 대표 확인 |
| 3 | Stripe Subscriptions 제거 (구독 미판매 시) | 비용↓ | 5분 | 대표 확인 |
| 4 | Product JSON-LD 스키마 삽입 | SEO + AI Index↑ | 2시간 | 자동화 가능 |
| 5 | WebSite + BreadcrumbList 스키마 추가 | AI Index↑ | 30분 | 자동화 가능 |
| 6 | llms.txt 생성 | Agent Readiness↑ | 30분 | 자동화 가능 |
| 7 | 사용 안 하는 커스텀 앱(ATLM-Data-API 등) 정리 | 보안↑ | 10분 | 대표 확인 |
| 8 | Rubix Bulk Price Editor — 시즌 후 일시정지 | 월 $14.95↓ | 1분 | 담당자 |

---

## 비용 누수 추정 (추정치)

| 앱 | 추정 비용 |
|----|-----------|
| Rubix Bulk Price Editor | $14.95/월 = $179/년 |
| BUCKS | $76.75/년 |
| Channel Talk | 유료 (플랜별 상이, 추정 $30~50/월) |
| Adoric / SendWILL / BLOY | 무료~유료 혼재 |

→ 미사용 앱 정리 시 **연 $300~600 절감 가능 (추정치)**

---

## 주의사항

- 앱 제거는 스토어 설정 변경 → **대표 승인 후 진행** (가드레일 준수)
- 앱 제거 전 해당 앱이 테마에 심은 코드 스니펫이 남는지 확인 필요
- Klaviyo는 팝업(UnKPet) 작업 중이므로 **유지** (이메일 발송은 미사용, 팝업만 사용)
