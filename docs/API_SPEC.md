# LocalHub API Specification v1.0

> Last updated: 2026-07-14  
> Project period: 2026-07-14 to 2026-07-16 15:00 (KST)  
> This document is the shared contract between FE, BE, and AI/data work. Do not change an endpoint or field name without team agreement.

## 1. Global conventions

### Base URL

```text
Local: http://localhost:8000/api
Production: https://{render-domain}/api
```

### Content type and naming

- Request and response body: `application/json`
- JSON field names: `camelCase`
- Python internal names may use `snake_case`, but Pydantic response aliases must produce `camelCase`.
- Date/time: ISO 8601 (`2026-07-14T13:30:00+09:00`)
- Empty collections: `[]`, not `null`
- Missing optional text: empty string or `null` only as defined by the relevant schema; do not invent values.

### Success envelope

```json
{
  "success": true,
  "data": {},
  "message": "요청에 성공했습니다."
}
```

### Paginated success envelope

```json
{
  "success": true,
  "data": {
    "items": [],
    "page": 1,
    "size": 10,
    "total": 0,
    "totalPages": 0
  },
  "message": "목록을 조회했습니다."
}
```

### Error envelope

```json
{
  "success": false,
  "data": null,
  "message": "요청을 처리할 수 없습니다.",
  "error": {
    "code": "INVALID_REQUEST",
    "detail": "필수 입력값이 누락되었습니다."
  }
}
```

### HTTP status codes

| Status | Usage |
|---:|---|
| 200 | Read, update, or delete succeeded |
| 201 | Resource created |
| 400 | Invalid request or business rule violation |
| 403 | Post password mismatch |
| 404 | Resource not found |
| 422 | Request schema validation failed |
| 500 | Internal server or OpenAI API failure |

### Error codes

| Code | Meaning |
|---|---|
| `INVALID_REQUEST` | Invalid query/body |
| `VALIDATION_ERROR` | Input validation failed |
| `NOT_FOUND` | Resource not found |
| `INVALID_PASSWORD` | Post password mismatch |
| `DATA_LOAD_ERROR` | Provided JSON could not be loaded |
| `OPENAI_API_ERROR` | OpenAI request failed |
| `INTERNAL_SERVER_ERROR` | Unhandled server error |

## 2. Shared schemas

### Post

```json
{
  "id": 1,
  "title": "구미 여행지 추천 부탁드립니다",
  "content": "주말에 가볼 만한 장소가 있을까요?",
  "category": "여행",
  "nickname": "익명",
  "viewCount": 12,
  "createdAt": "2026-07-14T13:30:00+09:00",
  "updatedAt": "2026-07-14T13:30:00+09:00"
}
```

Allowed post categories:

```text
여행 / 맛집 / 축제 / 생활 / 자유
```

`password` is accepted only in create/update/delete requests. It must never appear in a response or log.

### Place

```json
{
  "contentId": "3032819",
  "contentTypeId": "12",
  "contentType": "관광지",
  "title": "검성지 생태공원",
  "address": "경상북도 구미시 황상동",
  "detailAddress": "",
  "telephone": "",
  "longitude": 128.438086,
  "latitude": 36.114844,
  "imageUrl": "https://tong.visitkorea.or.kr/example.jpg",
  "thumbnailUrl": "https://tong.visitkorea.or.kr/example-thumbnail.jpg",
  "region": "구미",
  "tags": ["자연", "산책", "힐링"]
}
```

Source-to-API mapping:

| Source | API |
|---|---|
| `contentid` | `contentId` |
| `contenttypeid` | `contentTypeId` |
| file-level `contentType` | `contentType` |
| `addr1` | `address` |
| `addr2` | `detailAddress` |
| `tel` | `telephone` |
| `mapx` | `longitude` (number) |
| `mapy` | `latitude` (number) |
| `firstimage` | `imageUrl` |
| `firstimage2` | `thumbnailUrl` |

The original TourAPI JSON is read-only. Derived fields such as `region` and `tags` must be stored separately and joined by `contentId`.

### Travel type

| Code | Display name | Base keywords |
|---|---|---|
| `HEALING` | 고요한 쉼표 수집가 | 자연, 산책, 휴식, 조용함 |
| `EXPLORER` | 에너지 만렙 탐험가 | 레포츠, 체험, 야외, 활동 |
| `CULTURE` | 이야기를 좇는 시간여행자 | 문화, 역사, 전시, 사진 |
| `FOODIE` | 한입에 담는 로컬 미식가 | 음식점, 시장, 축제, 특산물 |

## 3. Post APIs

### GET `/api/posts`

Query parameters:

| Name | Required | Default | Description |
|---|---|---|---|
| `page` | No | 1 | Page number, minimum 1 |
| `size` | No | 10 | Page size |
| `category` | No | all | Allowed post category |
| `keyword` | No | - | Search title and content |
| `sort` | No | `latest` | `latest` or `views` |

Response: paginated `Post` list.

### GET `/api/posts/{id}`

- Returns one `Post`.
- A successful detail request increments `viewCount` once.

### POST `/api/posts`

Request:

```json
{
  "title": "구미 여행지 추천 부탁드립니다",
  "content": "주말에 가볼 만한 장소가 있을까요?",
  "category": "여행",
  "nickname": "익명",
  "password": "1234"
}
```

Response: `201` with the created `Post`.

### PUT `/api/posts/{id}`

Request:

```json
{
  "title": "수정된 제목",
  "content": "수정된 내용입니다.",
  "category": "여행",
  "nickname": "익명",
  "password": "1234"
}
```

Response: updated `Post`. Password mismatch returns `403 / INVALID_PASSWORD`.

### DELETE `/api/posts/{id}`

Request:

```json
{
  "password": "1234"
}
```

Response:

```json
{
  "success": true,
  "data": { "id": 1 },
  "message": "게시글을 삭제했습니다."
}
```

## 4. Place APIs

### GET `/api/places`

Query parameters:

| Name | Required | Default | Description |
|---|---|---|---|
| `page` | No | 1 | Page number |
| `size` | No | 12 | Page size |
| `type` | No | all | 관광지, 문화시설, 축제공연행사, 여행코스, 레포츠, 숙박, 쇼핑, 음식점 |
| `region` | No | all | 구미, 대구, 칠곡, 성주, 고령 |
| `keyword` | No | - | Search title and address |

Response: paginated `Place` list.

### GET `/api/places/{contentId}`

Response: one `Place`; unknown ID returns `404 / NOT_FOUND`.

## 5. Chat API

### POST `/api/chat`

Request:

```json
{
  "message": "구미에서 산책하기 좋은 관광지를 추천해줘",
  "history": [
    { "role": "user", "content": "구미 여행 정보를 알려줘" },
    { "role": "assistant", "content": "어떤 종류의 장소를 찾고 계신가요?" }
  ]
}
```

Allowed roles: `user`, `assistant`.

Response:

```json
{
  "success": true,
  "data": {
    "answer": "자연 속에서 산책하고 싶다면 검성지 생태공원을 추천합니다.",
    "references": [
      { "type": "place", "id": "3032819", "title": "검성지 생태공원" },
      { "type": "post", "id": "3", "title": "구미 산책 장소 후기" }
    ]
  },
  "message": "챗봇 답변을 생성했습니다."
}
```

Chat grounding rules:

1. Search provided JSON and posts before calling OpenAI.
2. Send only relevant records as context.
3. Never claim unavailable prices, schedules, reviews, or facilities.
4. Return every used place/post in `references`; otherwise return `[]`.
5. OpenAI failure returns `500 / OPENAI_API_ERROR` with no fabricated answer.

## 6. Travel test API

### GET `/api/travel-test/questions`

Returns the public travel-test question set. Scoring fields and type-selection metadata are backend-only and must not be included in this response.

Response:

```json
{
  "success": true,
  "data": {
    "version": "1.0",
    "requiredAnswerCount": 5,
    "questions": [
      {
        "questionId": 1,
        "question": "여행을 떠났을 때 가장 기대되는 순간은?",
        "options": [
          {
            "optionId": "Q1_A",
            "text": "자연 속에서 아무 생각 없이 여유롭게 쉬는 순간"
          }
        ]
      }
    ]
  },
  "message": "여행 취향 질문을 조회했습니다."
}
```

Question response rules:

1. Read the source question set from `data/derived/travel_test_questions.json`.
2. Return `questionId`, question text, `optionId`, and option text only, together with the public version and required answer count.
3. Never return `scores`, `primaryType`, `tieBreakQuestionOrder`, or `fallbackTypeOrder` to the browser.

### POST `/api/travel-test`

Request:

```json
{
  "answers": [
    { "questionId": 1, "optionId": "Q1_A" },
    { "questionId": 2, "optionId": "Q2_C" },
    { "questionId": 3, "optionId": "Q3_A" },
    { "questionId": 4, "optionId": "Q4_B" },
    { "questionId": 5, "optionId": "Q5_D" }
  ]
}
```

The backend owns option scores and type selection. FE sends identifiers only.

Response:

```json
{
  "success": true,
  "data": {
    "travelType": {
      "code": "HEALING",
      "name": "고요한 쉼표 수집가",
      "description": "바쁘게 움직이는 것보다 한 장소에서 천천히 머무는 시간을 좋아하는 여행자예요. 자연을 감상하거나 조용한 길을 걸으며 여행 속 여유를 발견해요.",
      "keywords": ["자연", "산책", "휴식", "조용함"]
    },
    "recommendations": [
      {
        "contentId": "3032819",
        "title": "검성지 생태공원",
        "contentType": "관광지",
        "address": "경상북도 구미시 황상동",
        "imageUrl": "https://tong.visitkorea.or.kr/example.jpg",
        "matchedKeywords": ["자연", "산책", "휴식"],
        "matchScore": 3,
        "reason": "자연을 감상하며 여유롭게 산책하기 좋은 장소입니다."
      }
    ]
  },
  "message": "여행 취향 분석을 완료했습니다."
}
```

Recommendation rules:

1. Use deterministic score calculation for the travel type and ranking.
2. Sort by `matchScore` descending and return up to three places.
3. Return the fixed user-facing `name` and `description` defined for the selected type; OpenAI must not select, rename, or rewrite the travel type.
4. OpenAI may phrase only `recommendations[].reason` from grounded place data.
5. If OpenAI fails, use a template: `선호 키워드인 {keywords}와 잘 맞는 장소입니다.`
6. Tags generated from sparse source metadata must be reviewed by a team member.

## 7. Festival API

### GET `/api/festivals`

Query parameters: `region`, `year`, `month` (all optional).

Response item:

```json
{
  "contentId": "3028462",
  "title": "구미라면축제",
  "address": "경상북도 구미시 원평동",
  "detailAddress": "구미역 일원",
  "telephone": "054-480-2652",
  "longitude": 128.331422,
  "latitude": 36.129404,
  "imageUrl": "https://tong.visitkorea.or.kr/example.jpg",
  "eventStartDate": "2026-10-09",
  "eventEndDate": "2026-10-10"
}
```

Important: the supplied festival list JSON does not contain `startDate` or `endDate`. Do not infer dates from titles, `createdtime`, `modifiedtime`, or OpenAI. Implement calendar filtering only after verified dates are available in a separate derived file. Otherwise return festival cards without calendar placement or defer this feature.

## 8. FE integration rules

```javascript
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  headers: { "Content-Type": "application/json" }
});
```

- Read actual payload from `response.data.data`.
- Read list payload from `response.data.data.items`.
- Display `error.response?.data?.message` when available.
- Do not call OpenAI directly from Vue.
- Do not silently replace API failures with fake production data.

## 9. API change process

No contributor or AI tool may change this contract alone. Share changes in this format:

```text
[API 명세 변경 요청]
대상: POST /api/travel-test
변경 전: type
변경 후: travelType
변경 이유: 다른 응답 필드와 의미 구분
영향 범위: FE 결과 화면, BE 응답 모델
```

After team approval, update this file first, then update BE schemas/tests, then FE calls.
