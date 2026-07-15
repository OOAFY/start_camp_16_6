import json
import os
import re
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import requests
from dotenv import load_dotenv


# =========================================================
# 기본 설정
# =========================================================

load_dotenv()

API_ENDPOINT = os.getenv("FESTIVAL_API_ENDPOINT")

# 공공데이터포털의 Encoding 인증키를 넣어도
# requests에서 이중 인코딩되지 않도록 한 번 디코딩한다.
SERVICE_KEY = unquote(os.getenv("DATA_GO_KR_SERVICE_KEY", ""))

INPUT_PATH = Path("data/구미_경북권_축제공연행사(1).json")
OUTPUT_PATH = Path("data/구미_경북권_축제공연행사_with_dates.json")

API_RAW_PATH = Path("data/전국문화축제표준데이터_raw.json")
REPORT_PATH = Path("data/festival_date_merge_report.json")

PAGE_SIZE = 1000


# =========================================================
# 공공데이터 API 응답 처리
# =========================================================

def extract_items(payload: dict[str, Any]) -> tuple[list[dict], int]:
    """
    공공데이터 API 응답 구조가 조금씩 다를 수 있으므로
    자주 사용되는 여러 JSON 구조를 처리한다.
    """

    body: Any = payload

    if isinstance(payload.get("response"), dict):
        body = payload["response"].get("body", {})
    elif isinstance(payload.get("body"), dict):
        body = payload["body"]

    if not isinstance(body, dict):
        raise ValueError("API 응답의 body 구조를 확인할 수 없습니다.")

    items: Any = body.get("items", body.get("data", []))

    # {"items": {"item": [...]}} 형태 대응
    if isinstance(items, dict):
        items = items.get("item", items.get("items", []))

    # 데이터 한 건만 객체로 오는 경우
    if isinstance(items, dict):
        items = [items]

    if not isinstance(items, list):
        items = []

    total_count = body.get("totalCount", len(items))

    try:
        total_count = int(total_count)
    except (TypeError, ValueError):
        total_count = len(items)

    return items, total_count


def fetch_all_festivals() -> list[dict]:
    if not API_ENDPOINT:
        raise ValueError("FESTIVAL_API_ENDPOINT 환경변수가 없습니다.")

    if not SERVICE_KEY:
        raise ValueError("DATA_GO_KR_SERVICE_KEY 환경변수가 없습니다.")

    all_items: list[dict] = []
    page_no = 1

    while True:
        params = {
            "serviceKey": SERVICE_KEY,
            "pageNo": page_no,
            "numOfRows": PAGE_SIZE,
            "type": "json",
        }

        response = requests.get(
            API_ENDPOINT,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        try:
            payload = response.json()
        except ValueError as error:
            raise RuntimeError(
                "API가 JSON이 아닌 데이터를 반환했습니다. "
                "type=json 설정과 인증키를 확인해 주세요."
            ) from error

        items, total_count = extract_items(payload)
        all_items.extend(items)

        print(
            f"API {page_no}페이지 수집: "
            f"{len(items)}건 / 누적 {len(all_items)}건 / 전체 {total_count}건"
        )

        if not items:
            break

        if len(all_items) >= total_count:
            break

        if len(items) < PAGE_SIZE:
            break

        page_no += 1

    return all_items


# =========================================================
# 이름 및 주소 정규화
# =========================================================

def normalize_basic(value: Any) -> str:
    """
    공백과 특수문자를 제거한 기본 비교 문자열.
    """

    text = unicodedata.normalize("NFKC", str(value or ""))
    text = text.lower()

    # 한글, 영문, 숫자 이외 문자 제거
    text = re.sub(r"[^0-9a-z가-힣]", "", text)

    return text


def normalize_relaxed(value: Any) -> str:
    """
    연도, 회차, 괄호 부제를 추가로 제거한 비교 문자열.
    기본 비교로 찾지 못했을 때만 사용한다.
    """

    text = unicodedata.normalize("NFKC", str(value or ""))
    text = text.lower()

    # 괄호 속 부제 제거
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"<[^>]*>", "", text)
    text = re.sub(r"\[[^\]]*\]", "", text)

    # 2025, 2026 등의 연도 제거
    text = re.sub(r"\b(?:19|20)\d{2}\b", "", text)

    # 제20회, 20회 등의 회차 제거
    text = re.sub(r"제?\s*\d+\s*회", "", text)

    text = re.sub(r"[^0-9a-z가-힣]", "", text)

    return text


def extract_region_tokens(address: Any) -> set[str]:
    """
    주소에서 시·군·구 단위 토큰을 추출한다.
    """

    text = str(address or "")

    patterns = [
        r"[가-힣]+특별시",
        r"[가-힣]+광역시",
        r"[가-힣]+특별자치시",
        r"[가-힣]+특별자치도",
        r"[가-힣]+도",
        r"[가-힣]+시",
        r"[가-힣]+군",
        r"[가-힣]+구",
    ]

    tokens: set[str] = set()

    for pattern in patterns:
        tokens.update(re.findall(pattern, text))

    return tokens


def get_api_address(festival: dict) -> str:
    road_address = str(festival.get("rdnmadr") or "")
    lot_address = str(festival.get("lnmadr") or "")

    return f"{road_address} {lot_address}".strip()


def address_match_score(original_address: str, api_address: str) -> int:
    original_tokens = extract_region_tokens(original_address)
    api_tokens = extract_region_tokens(api_address)

    return len(original_tokens.intersection(api_tokens))


# =========================================================
# 날짜 처리
# =========================================================

def normalize_date(value: Any) -> str | None:
    """
    20260101, 2026-01-01 등의 값을 YYYY-MM-DD 형식으로 변환한다.
    """

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    digits = re.sub(r"[^0-9]", "", text)

    if len(digits) >= 8:
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"

    return text


def sortable_date(value: Any) -> str:
    normalized = normalize_date(value)
    return normalized or "0000-00-00"


# =========================================================
# 축제 매칭
# =========================================================

def select_candidate(
    candidates: list[dict],
    original_address: str,
) -> tuple[dict | None, bool]:
    """
    후보가 여러 건일 경우 주소 일치도와 시작일을 기준으로 선택한다.

    반환값:
    - 선택 후보
    - 후보가 명확하지 않은지 여부
    """

    if not candidates:
        return None, False

    if len(candidates) == 1:
        return candidates[0], False

    ranked: list[tuple[tuple[int, str], dict]] = []

    for candidate in candidates:
        score = address_match_score(
            original_address,
            get_api_address(candidate),
        )

        rank = (
            score,
            sortable_date(candidate.get("fstvlStartDate")),
        )

        ranked.append((rank, candidate))

    ranked.sort(key=lambda item: item[0], reverse=True)

    best_rank, best_candidate = ranked[0]

    # 1위와 2위 점수가 완전히 같으면 자동 선택하지 않는다.
    if len(ranked) >= 2 and ranked[1][0] == best_rank:
        return None, True

    return best_candidate, False


def build_indexes(api_festivals: list[dict]):
    strict_index: defaultdict[str, list[dict]] = defaultdict(list)
    relaxed_index: defaultdict[str, list[dict]] = defaultdict(list)

    for festival in api_festivals:
        festival_name = festival.get("fstvlNm", "")

        strict_key = normalize_basic(festival_name)
        relaxed_key = normalize_relaxed(festival_name)

        if strict_key:
            strict_index[strict_key].append(festival)

        if relaxed_key:
            relaxed_index[relaxed_key].append(festival)

    return strict_index, relaxed_index


def match_festival(
    original: dict,
    strict_index: dict[str, list[dict]],
    relaxed_index: dict[str, list[dict]],
) -> tuple[dict | None, str]:
    title = original.get("title", "")
    address = original.get("addr1", "")

    # 1단계: 공백 및 특수문자만 제거한 이름 비교
    strict_key = normalize_basic(title)
    strict_candidates = strict_index.get(strict_key, [])

    candidate, ambiguous = select_candidate(
        strict_candidates,
        address,
    )

    if candidate:
        return candidate, "normalized_title"

    if ambiguous:
        return None, "ambiguous_strict_match"

    # 2단계: 연도와 회차까지 제거한 이름 비교
    relaxed_key = normalize_relaxed(title)
    relaxed_candidates = relaxed_index.get(relaxed_key, [])

    candidate, ambiguous = select_candidate(
        relaxed_candidates,
        address,
    )

    if candidate:
        return candidate, "relaxed_title"

    if ambiguous:
        return None, "ambiguous_relaxed_match"

    return None, "unmatched"


# =========================================================
# JSON 병합
# =========================================================

def merge_dates(
    original_data: dict,
    api_festivals: list[dict],
) -> tuple[dict, dict]:
    strict_index, relaxed_index = build_indexes(api_festivals)

    matched_report: list[dict] = []
    unmatched_report: list[dict] = []
    ambiguous_report: list[dict] = []

    for item in original_data.get("items", []):
        api_item, match_method = match_festival(
            item,
            strict_index,
            relaxed_index,
        )

        if api_item:
            item["eventStartDate"] = normalize_date(
                api_item.get("fstvlStartDate")
            )
            item["eventEndDate"] = normalize_date(
                api_item.get("fstvlEndDate")
            )
            item["dateSource"] = "전국문화축제표준데이터"

            matched_report.append({
                "originalTitle": item.get("title"),
                "apiTitle": api_item.get("fstvlNm"),
                "matchMethod": match_method,
                "eventStartDate": item["eventStartDate"],
                "eventEndDate": item["eventEndDate"],
                "originalAddress": item.get("addr1"),
                "apiAddress": get_api_address(api_item),
            })

        elif match_method.startswith("ambiguous"):
            ambiguous_report.append({
                "title": item.get("title"),
                "address": item.get("addr1"),
                "reason": match_method,
            })

        else:
            unmatched_report.append({
                "title": item.get("title"),
                "address": item.get("addr1"),
                "reason": match_method,
            })

    report = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "originalCount": len(original_data.get("items", [])),
        "apiCount": len(api_festivals),
        "matchedCount": len(matched_report),
        "unmatchedCount": len(unmatched_report),
        "ambiguousCount": len(ambiguous_report),
        "matched": matched_report,
        "unmatched": unmatched_report,
        "ambiguous": ambiguous_report,
    }

    return original_data, report


# =========================================================
# 실행
# =========================================================

def main():
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"원본 JSON을 찾을 수 없습니다: {INPUT_PATH}"
        )

    with INPUT_PATH.open("r", encoding="utf-8") as file:
        original_data = json.load(file)

    api_festivals = fetch_all_festivals()

    # API 원본 데이터도 별도로 저장
    API_RAW_PATH.parent.mkdir(parents=True, exist_ok=True)

    with API_RAW_PATH.open("w", encoding="utf-8") as file:
        json.dump(
            api_festivals,
            file,
            ensure_ascii=False,
            indent=2,
        )

    merged_data, report = merge_dates(
        original_data,
        api_festivals,
    )

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(
            merged_data,
            file,
            ensure_ascii=False,
            indent=2,
        )

    with REPORT_PATH.open("w", encoding="utf-8") as file:
        json.dump(
            report,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print("병합 완료")
    print(f"전체 원본 축제: {report['originalCount']}건")
    print(f"날짜 매칭 성공: {report['matchedCount']}건")
    print(f"매칭 실패: {report['unmatchedCount']}건")
    print(f"중복 후보: {report['ambiguousCount']}건")
    print(f"결과 파일: {OUTPUT_PATH}")
    print(f"검토 파일: {REPORT_PATH}")


if __name__ == "__main__":
    main()