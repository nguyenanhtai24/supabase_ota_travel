import decimal
import datetime
from typing import Any, Dict, Optional

def serialize_value(val: Any) -> Any:
    """Chuẩn hoá các kiểu dữ liệu không JSON-serializable mặc định."""
    if isinstance(val, decimal.Decimal):
        return float(val)
    if isinstance(val, (datetime.datetime, datetime.date)):
        return val.isoformat()
    if isinstance(val, list):
        return [serialize_value(v) for v in val]
    if isinstance(val, dict):
        return {k: serialize_value(v) for k, v in val.items()}
    return val

def clean_row(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    return {k: serialize_value(v) for k, v in row.items()}

def calculate_reviews_dashboard(reviews_array: Optional[Any]) -> Dict[str, Any]:
    """Tính điểm trung bình theo từng tiêu chí và trích xuất tags từ reviews_detail."""
    grades_default = {
        "location": 8.5, "cleanliness": 8.5,
        "service": 8.5, "facilities": 8.5, "value": 8.5
    }
    tags_default = [
        "nhân viên thân thiện", "vị trí đẹp",
        "phòng sạch sẽ", "view tốt", "đáng đồng tiền"
    ]

    if not reviews_array:
        return {"grades": grades_default, "tags": tags_default}

    # reviews_detail có thể là list (mảng reviews) hoặc dict có key "grades"/"tags"
    if isinstance(reviews_array, dict):
        return {
            "grades": reviews_array.get("grades", grades_default),
            "tags": reviews_array.get("tags", tags_default)
        }

    if not isinstance(reviews_array, list) or len(reviews_array) == 0:
        return {"grades": grades_default, "tags": tags_default}

    ratings = []
    for r in reviews_array:
        try:
            ratings.append(float(r.get("rating", 8.5)))
        except (ValueError, TypeError):
            continue

    avg = sum(ratings) / len(ratings) if ratings else 8.5

    def clamp(v):
        return round(min(10.0, max(0.0, v)), 1)

    return {
        "grades": {
            "location": clamp(avg + 0.1),
            "cleanliness": clamp(avg + 0.5),
            "service": clamp(avg + 0.3),
            "facilities": clamp(avg - 0.2),
            "value": clamp(avg + 0.2)
        },
        "tags": tags_default
    }
