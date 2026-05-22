# Welcome Email Series — 초안
> Shopify Email 내장 사용. 외부 ESP 없음.
> 최종 활성화 전 대표 확인 필수.

---

## 트리거
- 이메일 마케팅 구독 즉시 발송
- 분기 조건: customer.locale = `ja` 또는 shipping_country = `Japan`

---

## [EN] Welcome Email

**제목**: `[LUMEN] Welcome — $10 Store Credit, ready at checkout`
**미리보기 텍스트**: `There's more in-store for you`
**발신자**: Atelier de LUMEN / info@atlm.kr

**본문 핵심**:
```
A welcome gift, ready to use on your first piece.

$10 store credit applied at checkout — just sign in.

[Shop Now → intl.atlm.kr]
```

**Footer 문구**:
- Applied automatically at checkout.
- Valid on first order · Sign-in required.

---

## [JP] 환영 이메일

**제목**: `初回ご注文時、チェックアウトで自動適用される$10ストアクレジットをご用意しました。`
**미리보기 텍스트**: `アトリエ ドゥ ルーメンへようこそ`
**발신자**: Atelier de LUMEN / info@atlm.kr

**본문 핵심**:
```
ATELIER DE LUMEN へようこそ

初回ご注文で、チェックアウト時に自動適用される
$10ストアクレジットをご利用いただけます。

（チェックアウトで自動適用 — ログインのみ必要）

[ショッピングを始める → intl.atlm.kr]
```

---

## 구현 메모

- $10 크레딧: Shopify 계정 자동 적용. 쿠폰 코드 불필요 → 이메일에 코드 미포함.
- Sign-in required: 고객이 계정 로그인 시에만 크레딧 적용됨 → 반드시 명시.
- Shopify Email에서 locale 분기: Automation → Add condition → Customer language = Japanese
