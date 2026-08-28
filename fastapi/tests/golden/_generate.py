"""골든 스냅샷 픽스처를 (재)생성하는 일회성 스크립트.

주의: 이 스크립트는 "현재 동작을 있는 그대로 고정"하기 위한 것이다.
의도적으로 응답 형식을 바꾼 뒤에는 변경이 올바른지 직접 확인하고 나서만
이 스크립트로 픽스처를 다시 생성해야 한다. 절대 무비판적으로 재실행해
테스트를 통과시키는 용도로 쓰지 말 것.
"""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from tests.test_golden_snapshots import CASES

client = TestClient(app)
OUT_DIR = Path(__file__).parent

for case in CASES:
    response = client.post(case["path"], json=case["body"])
    fixture = {
        "status_code": response.status_code,
        "body": response.json(),
    }
    out_path = OUT_DIR / f"{case['name']}.json"
    out_path.write_text(
        json.dumps(fixture, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {out_path}")
