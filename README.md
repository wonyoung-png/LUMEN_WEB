# LUMEN_WEB — 사이트 분석 저장소

> Atelier de LUMEN / AMESCOTES 웹사이트 분석 및 개선 작업 공유 저장소

## 대상 사이트

| 사이트 | URL | 우선순위 |
|--------|-----|---------|
| 루멘 글로벌 (Shopify) | intl.atlm.kr | Phase 1 진행 중 |
| 루멘 국내 (Cafe24) | atlm.kr | Phase 2 예정 |
| 아메스코테스 B2B | amescotes.co.kr | 거의 완료 |

## 폴더 구조

```
LUMEN_WEB/
├── reports/        # 분석 보고서
├── seo/            # SEO 작업 파일
├── schemas/        # 구조화 데이터 (JSON-LD)
└── CLAUDE.md       # AI 세션 컨텍스트
```

## 세션 연동 방법

새 세션 시작 시:
```bash
git pull origin main
```

작업 후 저장:
```bash
git add .
git commit -m "작업 내용 요약"
git push origin main
```

## 팀원 접근
- GitHub 계정으로 Collaborator 초대 필요
- `Settings → Collaborators → Add people`
