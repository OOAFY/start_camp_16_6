import json
import hashlib
from pathlib import Path

base_path = Path('data/raw/구미_경북권_축제공연행사.json')
date_path = Path('data/raw/구미_경북권_축제공연행사_날짜.json')

with base_path.open(encoding='utf-8') as f:
    base_data = json.load(f)
with date_path.open(encoding='utf-8') as f:
    date_data = json.load(f)

base_items = base_data.get('items', [])
date_items = date_data.get('items', [])

existing_by_id = {item.get('contentid'): item for item in date_items if item.get('contentid')}


def make_dates(contentid: str):
    h = int(hashlib.md5(contentid.encode('utf-8')).hexdigest()[:8], 16)
    start_month = 3 + (h % 10)
    start_day = 1 + (h % 20)
    end_month = start_month + ((h // 10) % 2)
    end_day = start_day + 1 + (h % 2)
    year = 2026

    def fmt(month, day):
        return f"{year:04d}-{month:02d}-{day:02d}"

    if end_month > 12:
        end_month = 12
    return fmt(start_month, start_day), fmt(end_month, end_day)


merged_items = []
for item in base_items:
    cid = item.get('contentid')
    existing = existing_by_id.get(cid)
    new_item = dict(item)

    if existing is not None:
        for key in ['eventStartDate', 'eventEndDate', 'dateSource', 'isEstimatedDate']:
            if key in existing:
                new_item[key] = existing[key]

    if 'eventStartDate' not in new_item or 'eventEndDate' not in new_item:
        start, end = make_dates(cid)
        new_item['eventStartDate'] = start
        new_item['eventEndDate'] = end
        new_item['dateSource'] = '임의 생성값'
        new_item['isEstimatedDate'] = True
    elif 'dateSource' not in new_item or 'isEstimatedDate' not in new_item:
        new_item['dateSource'] = '임의 생성값'
        new_item['isEstimatedDate'] = True

    merged_items.append(new_item)

result = {
    'region': date_data.get('region', base_data.get('region')),
    'contentType': date_data.get('contentType', base_data.get('contentType')),
    'contentTypeId': date_data.get('contentTypeId', base_data.get('contentTypeId')),
    'total': len(merged_items),
    'items': merged_items,
    'dateDataSummary': {
        'apiMatchedCount': sum(1 for item in merged_items if item.get('dateSource') == '전국문화축제표준데이터'),
        'estimatedCount': sum(1 for item in merged_items if item.get('isEstimatedDate') is True),
        'note': 'isEstimatedDate가 true인 일정은 임의 생성값입니다.'
    }
}

with date_path.open('w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
    f.write('\n')

print('updated', date_path)
print('item_count', len(merged_items))
print('apiMatchedCount', result['dateDataSummary']['apiMatchedCount'])
print('estimatedCount', result['dateDataSummary']['estimatedCount'])
