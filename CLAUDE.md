# CLAUDE.md — LUMEN_WEB 세션 컨텍스트

## 이 저장소의 목적
Atelier de LUMEN 및 AMESCOTES 웹사이트 SEO/AIO 분석 및 개선 작업을 세션 간 공유한다.

## 진행 현황

### intl.atlm.kr (Shopify — 글로벌)
- Phase 1 진행 중
- 최우선: Product 스키마 (JSON-LD) 삽입

### atlm.kr (Cafe24 — 국내)
- 현재 점수: ~30/100
- 풀 빌드업 필요 (LocalBusiness 스키마 포함)

### amescotes.co.kr (B2B)
- 거의 완료
- 잔여: FAQ 페이지 + ABOUT US + OUR CLIENTS 로고 5개 + Naver 블로그 양방향 링크

## 세션 시작 시 체크
1. `git pull origin main` 으로 최신 상태 동기화
2. `reports/` 폴더에서 이전 분석 보고서 확인
3. 작업 완료 후 반드시 `git push`

## 작업 원칙
- 분석 보고서는 `reports/YYYY-MM-DD_사이트명_내용.md` 형식으로 저장
- SEO 스키마 파일은 `schemas/` 폴더에 저장
- 커밋 메시지는 한국어로 간결하게
