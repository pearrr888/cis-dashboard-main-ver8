"""
calculate_modules/company_health.py
-------------------------------------
สูตรคำนวณโมดูล "Company Health" (💚) — คู่กับ pages_content/company_health.py

=== DATA CONTRACT (ห้ามลบ/เปลี่ยนชื่อ key โดยไม่แจ้งทีม — เพิ่ม key ใหม่ได้อิสระ) ===

calculate_health_module(df_fin_ticker) รับ:
    df_fin_ticker : pd.DataFrame งบการเงินของหุ้น "1 ตัว" ทุกปีที่มี (มาจากตาราง stock_financials
                    กรองด้วย ticker แล้ว) ต้องมีคอลัมน์: year, roe, roa, de_ratio, current_ratio

คืนค่าเป็น dict ที่ต้องมี key ต่อไปนี้เสมอ (คนอื่น/orchestrator/หน้า UI จะเรียกใช้ key พวกนี้):
    health_score      : float 0-100 หรือ NaN  (คะแนนรวม ใช้ทั้งหน้า Overview และ Company Health)
    roe, roa           : float หรือ NaN  (% ตามที่อยู่ในงบ)
    de_ratio            : float หรือ NaN  (เท่า)
    current_ratio        : float หรือ NaN  (เท่า)
    s_profitability      : float 0-100 หรือ NaN (ใช้ในหน้า Company Health ส่วน Dimensions)
    s_liquidity          : float 0-100 หรือ NaN
    s_debt               : float 0-100 หรือ NaN (ใช้ซ้ำในหน้า Risk Analysis ด้วย เป็น proxy Financial Risk)
    s_roe, s_roa         : float 0-100 หรือ NaN (คะแนนย่อยที่ป้อนสูตรคะแนนรวมจริง)
    data_complete        : bool  (True = มีครบทั้ง 4 ตัวแปรในงบปีล่าสุด)
    missing_fields       : str   (ชื่อคอลัมน์ที่ขาด คั่นด้วย comma เช่น "roe,de_ratio" — เป็น '' ถ้าครบ
                                  ใช้ str ไม่ใช่ list เพราะต้องบันทึกลง SQLite ผ่าน to_sql ได้)

*** [ISSUE 02] การเปลี่ยนแปลง contract: ถ้าข้อมูลขาด ค่าที่เกี่ยวข้องจะเป็น NaN (ไม่ใช้ค่า default สมมติอีกต่อไป)
    กฎ: health_score จะมีค่าก็ต่อเมื่อมีครบทั้ง 4 ตัวแปร (ROE, ROA, D/E, Current Ratio) ไม่เช่นนั้นเป็น NaN
    โมดูลอื่นที่อ่าน health_score / s_debt ต้องรองรับ NaN (ดู pd.isna) ***

build_health_score_yearly(df_fin_ticker) คืน pd.DataFrame คอลัมน์ [year, health_score]
    ใช้วาดกราฟ "Company Health Score Trend" ในหน้า Company Health
    ปีที่ข้อมูลไม่ครบ health_score = NaN (กราฟจะไม่วาดจุดของปีนั้น)

ที่มาของสูตร: ดูละเอียดใน DATA_FORMULA_AUDIT.md หัวข้อ 1 (Module: Company Health)
สรุปสั้น: ROE/ROA/D/E/Current Ratio เป็นอัตราส่วนมาตรฐาน แต่ตัวคูณ (3.5, 7.0, 45.0, 40.0)
และน้ำหนักถ่วง (30/25/20/25%) เป็นค่าที่กำหนดเอง (custom heuristic) ไม่ใช่มาตรฐานอุตสาหกรรม
ถ้าจะปรับปรุงสูตรนี้ ทำได้ที่ไฟล์นี้ไฟล์เดียว โดยคง key ที่ return ให้ครบตาม contract ด้านบน
"""

import numpy as np

# [ISSUE 01] น้ำหนักที่ใช้คำนวณ health_score "จริง" -- แก้ที่นี่ที่เดียว
# UI (pages_content/company_health.py) import ค่านี้ไปแสดงผล จึงไม่มีตัวเลขน้ำหนักซ้ำซ้อน/ไม่ตรงกัน
# รวมกันต้องได้ 1.0
HEALTH_WEIGHTS = {
    'roe': 0.30,        # Profitability - ROE
    'roa': 0.25,        # Profitability - ROA
    'liquidity': 0.20,  # Current Ratio
    'debt': 0.25,       # D/E Ratio
}
assert abs(sum(HEALTH_WEIGHTS.values()) - 1.0) < 1e-9

# [ISSUE 02] คอลัมน์ในตารางงบการเงินที่ "ต้องมี" ถึงจะคิดคะแนนรวมได้ (ตามลำดับ roe, roa, de, current ratio)
REQUIRED_COLS = ('roe', 'roa', 'de_ratio', 'current_ratio')

_MISSING_TOKENS = {'', '-', 'nan', 'none', 'n/a', 'null'}


def to_float_or_nan(v):
    """[ISSUE 02] แปลงเป็น float; ถ้าไม่มีค่า/อ่านไม่ได้/เป็น inf -> NaN (ไม่มีค่า default สมมติ)"""
    try:
        if v is None:
            return np.nan
        if isinstance(v, str) and v.strip().lower() in _MISSING_TOKENS:
            return np.nan
        f = float(v)
        return f if np.isfinite(f) else np.nan
    except (TypeError, ValueError):
        return np.nan


def _extract_metrics(r):
    """ดึงค่า (roe, roa, de, current_ratio) จากแถวงบ 1 แถว (Series หรือ dict) ตามชื่อคอลัมน์ในฐานข้อมูลกลาง"""
    return tuple(to_float_or_nan(r.get(c)) for c in REQUIRED_COLS)


def _compute_scores(roe, roa, de, curr_ratio):
    """สูตรคะแนนชุดเดียว ใช้ร่วมกันทั้งปีล่าสุดและรายปี (กันสูตรสองที่ไม่ตรงกัน)
    NaN ในตัวแปรใดๆ จะส่งต่อเป็น NaN ในคะแนนที่เกี่ยวข้อง (np.clip / การคูณ ไม่ทำให้ NaN หาย)"""
    s_roe = np.clip(roe * 3.5, 0, 100)
    s_roa = np.clip(roa * 7.0, 0, 100)
    s_liq = np.clip(curr_ratio * 45.0, 0, 100)
    s_debt = np.clip((2.5 - de) * 40.0, 0, 100)   # [ISSUE 03] จะปรับเป็นเพดานตามกลุ่มอุตสาหกรรมภายหลัง
    raw = (
        s_roe * HEALTH_WEIGHTS['roe'] + s_roa * HEALTH_WEIGHTS['roa']
        + s_liq * HEALTH_WEIGHTS['liquidity'] + s_debt * HEALTH_WEIGHTS['debt']
    )   # NaN ถ้าขาดตัวใดตัวหนึ่ง => ไม่ให้คะแนนรวมจากข้อมูลไม่ครบ
    return s_roe, s_roa, s_liq, s_debt, raw


def _final_score(raw):
    """[ISSUE 05 ยังไม่แก้] clip 25-98 คงไว้ตามเดิม; NaN ผ่านได้ (np.clip(nan) = nan)"""
    return round(float(np.clip(raw, 25, 98)), 1)


def _r(x, nd):
    """round ที่รักษา NaN ไว้"""
    return round(float(x), nd)


def calculate_health_module(df_fin_ticker):
    """Module 1: Company Health (ใช้งบปีล่าสุดที่มีจริง — ไม่ย้อนเอาค่าปีก่อนมาเติมช่องว่าง)"""
    if df_fin_ticker is None or len(df_fin_ticker) == 0:
        r = {}   # ไม่มีงบเลย -> ทุกตัวเป็น NaN แทนที่จะ crash ทั้ง pipeline
    else:
        r = df_fin_ticker.sort_values(by='year').iloc[-1]

    roe, roa, de, curr_ratio = _extract_metrics(r)
    s_roe, s_roa, s_liq, s_debt, raw = _compute_scores(roe, roa, de, curr_ratio)

    missing = [c for c, v in zip(REQUIRED_COLS, (roe, roa, de, curr_ratio)) if np.isnan(v)]

    return {
        'health_score': _final_score(raw),
        'roe': _r(roe, 2),
        'roa': _r(roa, 2),
        'de_ratio': _r(de, 2),
        'current_ratio': _r(curr_ratio, 2),
        's_profitability': _r((s_roe * 0.6) + (s_roa * 0.4), 1),
        's_liquidity': _r(s_liq, 1),
        's_debt': _r(s_debt, 1),
        's_roe': _r(s_roe, 1),
        's_roa': _r(s_roa, 1),
        'data_complete': len(missing) == 0,
        'missing_fields': ",".join(missing),
    }


def build_health_score_yearly(df_fin_ticker):
    """คำนวณคะแนน Health รายปีจากงบการเงินจริงแต่ละปี เพื่อวาดกราฟ trend
    (ใช้ _compute_scores ชุดเดียวกับ calculate_health_module(); ปีที่ข้อมูลไม่ครบ health_score = NaN)"""
    import pandas as pd
    rows = []
    if df_fin_ticker is not None and len(df_fin_ticker) > 0:
        for _, r in df_fin_ticker.sort_values('year').iterrows():
            roe, roa, de, curr_ratio = _extract_metrics(r)
            *_, raw = _compute_scores(roe, roa, de, curr_ratio)
            rows.append({'year': int(r['year']), 'health_score': _final_score(raw)})
    return pd.DataFrame(rows, columns=['year', 'health_score'])
