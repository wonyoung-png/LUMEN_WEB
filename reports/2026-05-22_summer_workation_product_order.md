# Summer Workation 컬렉션 상품 배열 분석 보고서
> 작성일: 2026-05-22
> 데이터: Shopify 30일 매출 + Clarity 히트맵 30일 (247 방문자, 454 클릭)

---

## 핵심 문제 (현재 배열)

| 지표 | 현황 |
|------|------|
| 매출 1위 상품 (BLEP CROSSBODY ORGAN BROWN, $736) | **12번 위치** — 방문자 72%만 도달 |
| 매출 최하위 상품 (MON BAG $75) | **1-2번 위치** — 100% 노출 낭비 |
| BEST SELLING 자동정렬 오류 | Shopify가 클릭수 기준으로 정렬하여 매출 역행 발생 |
| 컬렉션 단가 인상 장애 | $75 MON BAG이 첫 인상 → 럭셔리 포지셔닝 희석 |

---

## 스크롤 도달률 (Clarity 30일)

| 페이지 위치 | 방문자 도달 | 이탈률 |
|-------------|-------------|--------|
| Row 1 (위치 1-4) ~20% scroll | **88%** (217명) | 12% |
| Row 2 (위치 5-8) ~35% scroll | **77%** (191명) | 23% |
| Row 3 (위치 9-12) ~50% scroll | **67%** (165명) | 33% |
| Row 4 (위치 13-16) ~65% scroll | **58%** (144명) | 42% |
| Row 5 (위치 17-18) ~80% scroll | **~50%** (추정치) | ~50% |

→ **상위 4개 위치**에 매출 상위 상품을 배치하면 전체 Revenue가 직접적으로 개선됨

---

## Shopify 30일 매출 (현재 컬렉션 기준)

| 매출 순위 | 상품명 | Gross Sales | 주문수 | 현재 위치 |
|-----------|--------|-------------|--------|-----------|
| 1 | BLEP CROSSBODY BAG (ORGAN BROWN) | $736 | 4 | **12번** ← 문제 |
| 2 | BLEP CROSSBODY BAG (CARMINE RED) | $460 | 2 | **11번** ← 문제 |
| 3 | BON BALLON BAG (ORGAN BROWN) | $405 | 2 | **9번** ← 문제 |
| 4 | 2WAY MESH BAG (SOFT BLACK) | $286 | 2 | 4번 (양호) |
| 5 | BON BALLON BAG (TAN BROWN) | $216 | 1 | **8번** |
| 6 | BLEP CROSSBODY BAG (SOFT BLACK) | $184 | 1 | **13번** |
| 7 | MON BAG (ECRU WHITE) | $75 | 1 | **1번** ← 문제 |
| 8 | MON BAG (SOFT BLACK) | $75 | 1 | **2번** ← 문제 |

무매출 상품 (30일 기준): 2WAY MESH OFF WHITE, BON BALLON SILK BLUE/BLACK/WHITE DOVE/SOFT BLACK, BLEP SHOULDER BAG ×2, ARETE DEMI BAG ×3

---

## 권장 배열 (Manual Sort 적용)

### 기준
1. **매출 기준 우선**: 실제 구매 발생한 상품 상위 배치
2. **ORGAN BROWN 컬러 리더십**: 두 라인 모두 1위 컬러 → 브랜드 시그니처 확립
3. **고가 → 저가 흐름**: 럭셔리 포지셔닝 유지 ($231 → $196 → $161 → $110 → $75)
4. **SALE 50% 상품 후방 배치**: MON BAG 50% SALE 태그가 첫 인상에서 브랜드 희석

| 위치 | 상품명 | 세일가 | 근거 |
|------|--------|--------|------|
| **1** | BLEP CROSSBODY BAG (ORGAN BROWN) | $161 | 매출 1위, 4주 4건 |
| **2** | BLEP CROSSBODY BAG (CARMINE RED) | $161 | 매출 2위, 시즌 컬러 |
| **3** | BON BALLON BAG (ORGAN BROWN) | $189 | 매출 3위 |
| **4** | 2WAY MESH BAG (SOFT BLACK) | $110 | 매출 4위, Clarity 고클릭 |
| **5** | BLEP CROSSBODY BAG (SOFT BLACK) | $161 | 매출 6위, 블랙 수요 |
| **6** | BON BALLON BAG (TAN BROWN) | $189 | 매출 5위 |
| **7** | BLEP SHOULDER BAG (ORGAN BROWN) | $231 | 최고가, 브랜드 앵커 |
| **8** | BLEP SHOULDER BAG (SOFT BLACK) | $231 | 최고가 |
| **9** | ARETE DEMI BAG (BRUSHED BROWN) | $196 | 신상 |
| **10** | ARETE DEMI BAG (NUBUCK FAWN) | $196 | 신상, 서머 컬러 |
| **11** | ARETE DEMI BAG (SOFT BLACK) | $196 | 신상 |
| **12** | BON BALLON BAG (SILK BLUE) | $147 | 서머 컬러 |
| **13** | BON BALLON BAG (WHITE DOVE) | $189 | 뉴트럴 |
| **14** | BON BALLON BAG (SOFT BLACK) | $189 | 기본 |
| **15** | BON BALLON BAG (SILK BLACK) | $147 | 무매출 |
| **16** | 2WAY MESH BAG (OFF WHITE) | $110 | 무매출 |
| **17** | MON BAG (ECRU WHITE) | $75 | 최저가, 후방 배치 |
| **18** | MON BAG (SOFT BLACK) | $75 | 최저가, 후방 배치 |

---

## 변경 방법 (Shopify Admin)

1. **Shopify Admin** → 제품 → 컬렉션 → Summer Workation
2. 정렬 기준 → **"수동 정렬"** 으로 변경 (현재 "베스트셀러")
3. 위 순서대로 드래그앤드롭 재배치
4. 저장

> ⚠️ 수동 정렬로 변경 후에는 신규 상품 추가 시 자동 배치되지 않으므로, 신규 추가 시 수동 위치 지정 필요

---

## 기대 효과 (추정치)

- 매출 1-3위 상품이 상위 노출 → CVR 20-30% 개선 예상
- 첫 화면 단가 $75 → $161+ 로 향상 → 객단가 인식 개선
- ORGAN BROWN 컬러 일관성 → 브랜드 시그니처 강화
- MON BAG 후방 배치 → SALE 50% 이미지 희석 방지

---

## 추가 권고사항

- **BON BALLON SILK BLUE/BLACK 30일 무매출** → 컬렉션 제외 검토 (슬림화)
- **ARETE DEMI BAG** 3개 무매출 → 아직 신상이므로 유지, 2주 후 재평가
- **MON BAG** 50% SALE 종료 시 컬렉션에서 제거하거나 단독 SALE 페이지로 이동 고려
