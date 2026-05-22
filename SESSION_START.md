# LUMEN_WEB 세션 시작 프롬프트

> 새 Claude Code 세션에서 이 내용을 붙여넣어 컨텍스트를 이어받는다.
> LUMEN_WEB 폴더를 열면 CLAUDE.md가 자동 로드됨 (별도 붙여넣기 불필요).

---

## 세션 초기화 프롬프트 (복사해서 붙여넣기)

```
당신은 Atelier de LUMEN 글로벌 쇼핑몰(intl.atlm.kr, Shopify) 담당 에이전트입니다.

## 즉시 실행
1. git pull origin main
2. CLAUDE.md 읽어서 현재 진행 현황 파악
3. reports/ 폴더 최신 보고서 확인

## 스토어 기본
- URL: https://intl.atlm.kr
- Shopify Store ID: h3id7y-ij
- 주요 시장: JP / SG / HK / US
- 이메일: Shopify Email 단독 (외부 ESP 없음)
- $10 크레딧: 쿠폰 코드 없음, 로그인 시 자동 적용

## 현재 최우선 작업
1. [SEO] 제품 페이지 Product 스키마(JSON-LD) 삽입 → schemas/ 폴더 확인
2. [팝업] Klaviyo Form UnKPet 초안 완성 (절대 활성화 금지)
   - 에디터: https://www.klaviyo.com/forms/UnKPet/edit
   - 레퍼런스: C:\Users\이원영 AMES\Downloads\lumen_welcome_popup.html
3. [이메일] Shopify Email 웰컴 시리즈 EN/JP 분기 구성

## 주요 파일 경로
- 환경변수: C:\Users\이원영 AMES\Downloads\.env
- 번역 스크립트: C:\Users\이원영 AMES\Downloads\lumen_auto_translate.py
- 번역 CSV: C:\Users\이원영 AMES\Downloads\Atelier_de_LUMEN_translations_TITLES_FIXED.csv
- 팝업 레퍼런스: C:\Users\이원영 AMES\Downloads\lumen_welcome_popup.html

## 작업 원칙
- 물어보지 않고 판단하여 완수, 완료 후 보고
- 보고서: reports/YYYY-MM-DD_내용.md
- 작업 후: git add . && git commit -m "내용" && git push
```

---

## 빠른 작업별 시작 프롬프트

### SEO 스키마 작업 시작
```
LUMEN_WEB/schemas/ 폴더와 CLAUDE.md를 확인하고,
intl.atlm.kr 제품 페이지에 삽입할 Product JSON-LD 스키마를 작성해줘.
Shopify 테마 liquid 파일에 어디에 어떻게 삽입할지도 포함해서.
```

### 팝업 폼 작업 재개 시
```
CLAUDE.md 확인 후, Klaviyo Form UnKPet 팝업 작업을 이어서 해줘.
레퍼런스: C:\Users\이원영 AMES\Downloads\lumen_welcome_popup.html
에디터: https://www.klaviyo.com/forms/UnKPet/edit
절대 활성화 버튼 누르지 말 것.
```

### 일본어 번역 재실행 시
```
C:\Users\이원영 AMES\Downloads\lumen_auto_translate.py 스크립트로
일본어 번역을 실행해줘. .env 파일에서 키 로드.
입력: Atelier_de_LUMEN_translations_TITLES_FIXED.csv
```

### Shopify Email 웰컴 시리즈 작업 시
```
Shopify Email로 웰컴 시리즈를 구성해야 해.
트리거: 이메일 마케팅 구독 즉시
EN/JP 분기 필요.
JP 조건: customer.locale이 ja 또는 country가 Japan
$10 store credit (쿠폰 코드 없음, 로그인 자동 적용) 안내 포함.
CLAUDE.md에서 JP 이메일 제목/본문 샘플 확인할 것.
```

---

## 팀원 초기 설정

```bash
# 저장소 클론
git clone https://github.com/wonyoung-png/LUMEN_WEB.git
cd LUMEN_WEB

# Claude Code로 폴더 열기 → CLAUDE.md 자동 로드됨
```
