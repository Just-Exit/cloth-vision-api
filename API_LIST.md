# API 목록

> 완료 기준: endpoint, 요청·응답 schema, 인증·인가, DB 처리가 현재 API 계약대로
> 동작하는 경우 `[x]`로 표시한다. 경로가 존재하더라도 목표 기능 일부가 빠졌으면 `[ ]`로
> 유지한다.

## P0 — 인증

- [x] `POST /api/v1/auth/signup`
- [x] `POST /api/v1/auth/login`
- [ ] `POST /api/v1/auth/oauth/{provider}/exchange`
- [ ] `POST /api/v1/auth/refresh`
- [ ] `POST /api/v1/auth/logout`
- [x] `GET /api/v1/auth/me`

## P0 — 프로필·온보딩·설정

- [ ] `GET /api/v1/profile`
- [ ] `PATCH /api/v1/profile`
- [ ] `POST /api/v1/profile/image`
- [ ] `DELETE /api/v1/profile/image`
- [ ] `PUT /api/v1/profile/onboarding/body`
- [ ] `GET /api/v1/preferences`
- [ ] `PATCH /api/v1/preferences`

## P0 — 옷장

- [x] `POST /api/v1/closets`
- [x] `GET /api/v1/closets`
- [ ] `GET /api/v1/closets/{closet_id}`
- [ ] `PATCH /api/v1/closets/{closet_id}`
- [ ] `DELETE /api/v1/closets/{closet_id}`
- [ ] `PUT /api/v1/closets/{closet_id}/default`

## P0 — 의류 아이템

- [ ] `POST /api/v1/closets/{closet_id}/items` — 동기·기초 분석만 구현
- [ ] `GET /api/v1/closets/{closet_id}/items` — 검색·필터·정렬·페이지네이션·이미지 URL 누락
- [x] `GET /api/v1/items/{item_id}`
- [x] `PATCH /api/v1/items/{item_id}`
- [x] `DELETE /api/v1/items/{item_id}`
- [ ] `POST /api/v1/items/{item_id}/reanalyze`
- [ ] `GET /api/v1/items/{item_id}/analyses`
- [ ] `PATCH /api/v1/items/{item_id}/lifecycle`
- [ ] `POST /api/v1/items/bulk-lifecycle`

## P0 — 이미지

- [ ] `GET /api/v1/items/{item_id}/images`
- [ ] `POST /api/v1/items/{item_id}/images`
- [ ] `GET /api/v1/item-images/{image_id}`
- [ ] `DELETE /api/v1/item-images/{image_id}`

## P0 — AI 분석 작업

- [ ] `GET /api/v1/analysis-jobs/{job_id}`
- [ ] `POST /api/v1/analysis-jobs/{job_id}/retry`
- [ ] `POST /api/v1/analysis-jobs/{job_id}/cancel`

## P0 — 코디 추천

- [ ] `POST /api/v1/outfit-recommendations`
- [ ] `GET /api/v1/outfits`
- [ ] `GET /api/v1/outfits/{outfit_id}`
- [ ] `PATCH /api/v1/outfits/{outfit_id}`
- [ ] `DELETE /api/v1/outfits/{outfit_id}`
- [ ] `PUT /api/v1/outfits/{outfit_id}/bookmark`
- [ ] `DELETE /api/v1/outfits/{outfit_id}/bookmark`
- [ ] `PUT /api/v1/outfits/{outfit_id}/feedback`
- [ ] `DELETE /api/v1/outfits/{outfit_id}/feedback`

## P0 — 착용·리뷰

- [ ] `POST /api/v1/outfits/{outfit_id}/wear`
- [ ] `GET /api/v1/wear-events`
- [ ] `GET /api/v1/wear-events/{wear_event_id}`
- [ ] `PUT /api/v1/wear-events/{wear_event_id}/review`
- [ ] `DELETE /api/v1/wear-events/{wear_event_id}/review`

## P1 — 홈 대시보드

- [ ] `GET /api/v1/dashboard`

## P1 — 옷장 분석

- [ ] `GET /api/v1/analytics/wardrobe`
- [ ] `GET /api/v1/analytics/wardrobe/colors`
- [ ] `GET /api/v1/analytics/wardrobe/seasons`
- [ ] `GET /api/v1/analytics/wardrobe/categories`
- [ ] `GET /api/v1/analytics/wardrobe/unworn-items`
- [ ] `GET /api/v1/analytics/wardrobe/cost-per-wear`
- [ ] `GET /api/v1/analytics/wardrobe/recommendations`
- [ ] `GET /api/v1/analytics/wardrobe/report`

## P2 — 외부 이미지 가져오기

- [ ] `POST /api/v1/import-jobs`
- [ ] `GET /api/v1/import-jobs`
- [ ] `GET /api/v1/import-jobs/{job_id}`
- [ ] `POST /api/v1/import-jobs/{job_id}/retry`
- [ ] `POST /api/v1/import-jobs/{job_id}/cancel`

## P2 — 구독 (NOT MVP)

- [ ] `GET /api/v1/subscription`
- [ ] `POST /api/v1/subscription/checkout`
- [ ] `POST /api/v1/subscription/portal`
- [ ] `POST /api/v1/webhooks/subscriptions/{provider}`

## 공통

- [x] `GET /api/v1/health`
