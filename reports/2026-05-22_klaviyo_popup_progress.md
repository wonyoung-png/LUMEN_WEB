# Klaviyo Welcome Popup 작업 진행 보고서
> 작성일: 2026-05-22
> 담당: intl.atlm.kr (Shopify 글로벌)

---

## 작업 목표

lumen_welcome_popup.html 디자인을 Klaviyo Form으로 구현.
Cult Gaia(cultgaia.com) 동일 방식으로 native Klaviyo 두 컬럼 팝업 제작.

---

## 완료된 작업

| 항목 | 상태 |
|------|------|
| Form 생성 (UnKPet) | ✅ |
| 팝업 크기 920×647px 설정 | ✅ |
| 배경색 #F6F5EE 설정 | ✅ |
| 좌측 이미지 613px (main_banner.jpg) | ✅ Survey + Email Opt-In 양쪽 |
| 헤딩 폰트 Cormorant Garamond 적용 | ✅ |
| 헤딩 크기 54px 설정 | ✅ |
| 헤딩 텍스트 "$10 / Store / Credit" (3줄) | ✅ |

---

## 미완료 항목 (재개 시 순서대로)

1. **헤딩 폰트 재확인**
   - Cormorant Garamond Normal 400 / 54px 적용됨
   - 텍스트 입력 시 Arial 14px로 리셋되는 Klaviyo 버그 반복 → 선택 후 재적용 필요
   - 최종 확인 필요: font-weight Light(300) 가능 여부

2. **브랜드 레이블 추가** (헤딩 위)
   - "Atelier de Lumen" / 7.5px / #888 / letter-spacing 0.22em / uppercase

3. **서브텍스트 수정**
   - 현재: "on your first order"
   - 목표: "ENTER YOUR EMAIL TO RECEIVE / $10 OFF YOUR FIRST ORDER"
   - 9px / #555 / uppercase / letter-spacing 0.14em

4. **CTA 버튼 텍스트 수정**
   - 현재: 기본 텍스트
   - 목표: "Claim $10 Store Credit"
   - 배경 #1a1a1a / 글자 #F6F5EE / 8.5px / letter-spacing 0.2em

5. **Fine print 추가**
   - "Applied automatically at checkout."
   - "Valid on first order · Sign-in required."
   - 7.5px / #aaa

6. **Skip 링크 추가**
   - "No thanks" / 7.5px / #aaa / underline

7. **Survey 스텝 정리** (불필요 시 삭제)

---

## Klaviyo 작업 시 주의사항 (이번 세션에서 확인된 버그)

| 버그 | 원인 | 해결법 |
|------|------|--------|
| 텍스트 입력 후 Arial 14px로 리셋 | 새 텍스트 입력 시 Heading 스타일이 Body로 전환됨 | Ctrl+A → 폰트 드롭다운 클릭 → 검색창 클릭 → "Cormorant" 검색 → 선택 → 스크롤 오른쪽으로 이동 → 크기 54 입력 |
| 폰트 드롭다운에서 타이핑이 텍스트에 입력됨 | 드롭다운 열린 상태에서 검색창 클릭 안 하고 타이핑 | 드롭다운 열리면 반드시 검색창(돋보기 아이콘 옆) 먼저 클릭 |
| Ctrl+Z가 이미지/설정까지 되돌림 | Klaviyo의 undo가 전역 적용됨 | Ctrl+Z 최소화, 실수 시 Ctrl+Y로 복구 |

---

## 폼 접근 정보

- **Form ID**: UnKPet
- **에디터 URL**: https://www.klaviyo.com/forms/UnKPet/edit
- **상태**: 초안 (Draft) — **절대 Publish/활성화 금지**
- **viewId**: 01KS6H3Z53VTS8EKHTGKGT0PZG (Email Opt-In 스텝)
- **componentId**: 01KS6H3ZC3P30ZY335FKPWR8DB (헤딩 블록)

---

## 레퍼런스

- 팝업 HTML: `shopify/popup/lumen_welcome_popup.html`
- Cult Gaia 구현 확인: company_id `Ci6hq6`, 920×647px, flex-row, 배경 #F6F5EE — native Klaviyo 확인됨
