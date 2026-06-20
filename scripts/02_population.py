"""
02_population.py
SGIS 집계구 인구 데이터 전처리
- 시군구 전체 인구 집계 (31023: 성남시 분당구, 23080: 인천시 서구)
- 구역 내 인구: 면적 비례 배분 처리
- 직주비 산출
"""

import pandas as pd
import json
import os

# ── 설정 ────────────────────────────────────────────────────
CONFIG = {
    "pangyo": {
        "label": "제1판교",
        "sigungu_code": "31023",
        "sigungu_name": "경기도 성남시 분당구",
        "pop_file": "31023_2020년_인구총괄_총인구_.csv",
        "age_file": "31023_2020년_성연령별인구.csv",
        "den_file": "31023_2020년_인구총괄_인구밀도_.csv",
        "sigungu_area_km2": 71.5,
        "zone_area_km2": 3.3,
        "employment": 23097,
    },
    "cheongna": {
        "label": "청라국제업무지구",
        "sigungu_code": "23080",
        "sigungu_name": "인천광역시 서구",
        "pop_file": "23080_2020년_인구총괄_총인구_.csv",
        "age_file": "23080_2020년_성연령별인구.csv",
        "den_file": "23080_2020년_인구총괄_인구밀도_.csv",
        "sigungu_area_km2": 154.0,
        "zone_area_km2": 1.5,
        "employment": 26,
    },
}

AGE_VARS_TOTAL = [f"in_age_{i:03d}" for i in range(1, 22)]   # 전체(남녀합계)
AGE_VARS_WORK  = [f"in_age_{i:03d}" for i in range(3, 14)]   # 15-64세
AGE_VARS_OLD   = [f"in_age_{i:03d}" for i in range(14, 22)]  # 65세+
AGE_LABELS = [
    "0-4세","5-9세","10-14세","15-19세","20-24세","25-29세",
    "30-34세","35-39세","40-44세","45-49세","50-54세","55-59세",
    "60-64세","65-69세","70-74세","75-79세","80-84세","85-89세",
    "90-94세","95-99세","100세이상"
]


def load_csv(filepath):
    return pd.read_csv(filepath, encoding="cp949", header=None,
                       names=["year", "block_id", "var", "value"])


def process_zone(zone_key, data_dir="."):
    cfg = CONFIG[zone_key]

    # 총인구
    df_pop = load_csv(os.path.join(data_dir, cfg["pop_file"]))
    total_pop = int(df_pop["value"].sum())

    # 인구밀도
    df_den = load_csv(os.path.join(data_dir, cfg["den_file"]))
    avg_density = round(df_den["value"].mean(), 1)

    # 연령별 인구
    df_age = load_csv(os.path.join(data_dir, cfg["age_file"]))
    age_total = df_age[df_age["var"].isin(AGE_VARS_TOTAL)].groupby("var")["value"].sum()
    work_pop  = int(df_age[df_age["var"].isin(AGE_VARS_WORK)]["value"].sum())
    old_pop   = int(df_age[df_age["var"].isin(AGE_VARS_OLD)]["value"].sum())

    age_distribution = []
    for var, label in zip(AGE_VARS_TOTAL, AGE_LABELS):
        age_distribution.append({
            "age_group": label,
            "population": int(age_total.get(var, 0))
        })

    # 구역 내 추정 인구 (면적 비례)
    ratio = cfg["zone_area_km2"] / cfg["sigungu_area_km2"]
    zone_pop_est = round(total_pop * ratio)

    # 직주비
    emp = cfg["employment"]
    job_resident_ratio = round(emp / zone_pop_est, 2) if zone_pop_est > 0 else None

    result = {
        "zone": zone_key,
        "label": cfg["label"],
        "year": 2020,
        "sigungu": {
            "code": cfg["sigungu_code"],
            "name": cfg["sigungu_name"],
            "total_population": total_pop,
            "working_age_population": work_pop,
            "working_age_ratio": round(work_pop / total_pop * 100, 1),
            "elderly_population": old_pop,
            "elderly_ratio": round(old_pop / total_pop * 100, 1),
            "avg_density_per_km2": avg_density,
        },
        "zone_estimate": {
            "method": "면적 비례 배분",
            "zone_area_km2": cfg["zone_area_km2"],
            "sigungu_area_km2": cfg["sigungu_area_km2"],
            "area_ratio": round(ratio, 4),
            "estimated_population": zone_pop_est,
        },
        "job_resident_ratio": {
            "employment": emp,
            "estimated_population": zone_pop_est,
            "ratio": job_resident_ratio,
            "note": "면적비례 추정 인구 기반. 집계구 shapefile 확보 시 갱신 필요"
        },
        "age_distribution": age_distribution,
    }
    return result


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)

    for key in ["pangyo", "cheongna"]:
        print(f"\n처리 중: {CONFIG[key]['label']}")
        result = process_zone(key, data_dir=".")
        out_path = f"data/{key}_population.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"  시군구 총인구:    {result['sigungu']['total_population']:,}명")
        print(f"  구역 추정 인구:   {result['zone_estimate']['estimated_population']:,}명")
        print(f"  직주비:           {result['job_resident_ratio']['ratio']}")
        print(f"  저장 완료:        {out_path}")
