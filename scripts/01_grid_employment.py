"""
01_grid_employment.py
SGIS 100m 격자 종사자 데이터 전처리
- 구역(제1판교, 청라국제업무지구) 경계로 클리핑
- 결과를 data/ 폴더에 JSON으로 저장
"""

import pandas as pd
from pyproj import Transformer
import json
import os

# ── 좌표 변환 설정 ──────────────────────────────────────────
T_FWD = Transformer.from_crs("EPSG:4326", "EPSG:5186", always_xy=True)
T_INV = Transformer.from_crs("EPSG:5186", "EPSG:4326", always_xy=True)
HANGUL = "가나다라마바사아자차카타파하"

# 격자 원점 (TM중부 기준, 역산 보정값)
SX = -415204
SY = 190068


def coord_to_grid(lon, lat):
    """위경도 → 격자코드(구역, row, col)"""
    px, py = T_FWD.transform(lon, lat)
    dx, dy = px - SX, py - SY
    r_main = int(dy / 100000)
    c_main = int(dx / 100000)
    row = int((dy % 100000) / 100)
    col = int((dx % 100000) / 100)
    zone = HANGUL[r_main] + HANGUL[c_main]
    return zone, row, col


def grid_to_coord(zone_str, row, col):
    """격자코드 → 중심 위경도"""
    r_main = HANGUL.index(zone_str[0])
    c_main = HANGUL.index(zone_str[1])
    gx = SX + c_main * 100000 + col * 100 + 50   # 격자 중심
    gy = SY + r_main * 100000 + row * 100 + 50
    lon, lat = T_INV.transform(gx, gy)
    return lon, lat


def load_employment(filepath):
    df = pd.read_csv(filepath, encoding="cp949", header=None,
                     names=["year", "grid_id", "var", "value"])
    df["zone"] = df["grid_id"].str[:2]
    df["row_num"] = df["grid_id"].str[2:5].astype(int)
    df["col_num"] = df["grid_id"].str[5:8].astype(int)
    return df


# ── 구역 경계 정의 ──────────────────────────────────────────
ZONES = {
    "pangyo": {
        "label": "제1판교",
        "file": "2020년_종사자_라사_100M.csv",
        "grid_zone": "라사",
        "row_min": 414, "row_max": 441,
        "col_min": 227, "col_max": 271,
    },
    "cheongna": {
        "label": "청라국제업무지구",
        "file": "2020년_종사자_라바_100M.csv",
        "grid_zone": "라바",
        "row_min": 583, "row_max": 609,
        "col_min": 829, "col_max": 856,
    },
}


def process_zone(zone_key, data_dir="data/raw"):
    z = ZONES[zone_key]
    filepath = os.path.join(data_dir, z["file"])

    df = load_employment(filepath)
    filtered = df[
        (df["row_num"] >= z["row_min"]) & (df["row_num"] <= z["row_max"]) &
        (df["col_num"] >= z["col_min"]) & (df["col_num"] <= z["col_max"])
    ].copy()

    # 위경도 추가
    filtered[["lon", "lat"]] = filtered.apply(
        lambda r: pd.Series(grid_to_coord(z["grid_zone"], r["row_num"], r["col_num"])),
        axis=1
    )

    total_emp = int(filtered["value"].sum())
    grid_count = len(filtered)

    result = {
        "zone": zone_key,
        "label": z["label"],
        "year": 2020,
        "total_employment": total_emp,
        "grid_count": grid_count,
        "avg_per_grid": round(total_emp / grid_count, 1) if grid_count > 0 else 0,
        "max_grid": {
            "grid_id": filtered.loc[filtered["value"].idxmax(), "grid_id"] if grid_count > 0 else None,
            "value": int(filtered["value"].max()) if grid_count > 0 else 0,
        },
        "grids": filtered[["grid_id", "row_num", "col_num", "lon", "lat", "value"]]
                        .rename(columns={"value": "employment"})
                        .to_dict(orient="records")
    }
    return result


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)

    for key in ["pangyo", "cheongna"]:
        print(f"\n처리 중: {ZONES[key]['label']}")
        result = process_zone(key, data_dir=".")   # 원본 파일 경로 조정
        out_path = f"data/{key}_employment.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"  총 종사자: {result['total_employment']:,}명")
        print(f"  격자 수:   {result['grid_count']}개")
        print(f"  저장 완료: {out_path}")
