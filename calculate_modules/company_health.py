"""
calculate_modules/company_health.py
-------------------------------------
สูตรคำนวณโมดูล "Company Health" (💚) — คู่กับ pages_content/company_health.py

=== DATA CONTRACT (ห้ามลบ/เปลี่ยนชื่อ key โดยไม่แจ้งทีม — เพิ่ม key ใหม่ได้อิสระ) ===

calculate_health_module(df_fin_ticker, sector=None) รับ:
    df_fin_ticker : pd.DataFrame งบการเงินของหุ้น "1 ตัว" ทุกปีที่มี (มาจากตาราง stock_financials
                    กรองด้วย ticker แล้ว) ต้องมีคอลัมน์: year, roe, roa, de_ratio, current_ratio
    sector        : str หรือ None [ISSUE 03] ชื่อกลุ่มอุตสาหกรรม (ค่าจาก SECTOR_MAP ใน common.py)
                    ใช้เลือกเพดาน D/E ที่เหมาะสมกับกลุ่ม ถ้าไม่ส่งมา/ไม่รู้จักกลุ่ม -> ใช้ DEFAULT_DE_THRESHOLD
                    (2.5 เท่า เหมือนพฤติกรรมเดิมก่อนแก้ไข ไม่ Breaking Change กับโค้ดที่ยังไม่ได้ส่ง sector มา)

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
    de_threshold_used    : float (เพิ่มใหม่ [ISSUE 03] เพดาน D/E ที่ใช้จริงในการคิด s_debt ของหุ้นตัวนี้
                                  โปร่งใสว่าใช้เกณฑ์กลุ่มไหน ช่วย debug/ตรวจสอบย้อนหลังได้)

*** [ISSUE 02] การเปลี่ยนแปลง contract: ถ้าข้อมูลขาด ค่าที่เกี่ยวข้องจะเป็น NaN (ไม่ใช้ค่า default สมมติอีกต่อไป)
    กฎ: health_score จะมีค่าก็ต่อเมื่อมีครบทั้ง 4 ตัวแปร (ROE, ROA, D/E, Current Ratio) ไม่เช่นนั้นเป็น NaN
    โมดูลอื่นที่อ่าน health_score / s_debt ต้องรองรับ NaN (ดู pd.isna) ***

*** [ISSUE 03] การเปลี่ยนแปลง contract: เพดาน D/E ที่ใช้ตัดคะแนน s_debt ไม่ fix ที่ 2.5 อีกต่อไป
    แต่เลือกจากตาราง DE_SECTOR_THRESHOLDS ตามกลุ่มอุตสาหกรรม (sector) ที่ผู้เรียกส่งเข้ามา
    ⚠️ ตัวเลขเพดานในตารางเป็น "ค่าตั้งต้นให้ทีมพิจารณา" ไม่ใช่ตัวเลขจากมาตรฐานอุตสาหกรรมที่ตรวจสอบแล้ว
       ต้องให้ทีม/ผู้เชี่ยวชาญด้านการเงินอนุมัติตัวเลขจริงก่อนใช้งานจริง (ดู [ACTION REQUIRED] ในรายงาน)
    การเรียกที่ไม่ส่ง sector (โค้ด orchestrator เดิมที่ยังไม่แก้) จะยังได้ผลลัพธ์เหมือนก่อนแก้ไขทุกประการ
    (fallback ไปที่ DEFAULT_DE_THRESHOLD = 2.5 ซึ่งเท่ากับค่าที่ fix ไว้เดิม) ***

*** [ISSUE 04] ยืนยัน Single Source of Truth: ไฟล์นี้ "ไม่คำนวณ" ROE/ROA/D/E/Current Ratio เอง
    ทั้งหมดอ่านตรงจากคอลัมน์ df_fin_ticker (มาจากตาราง stock_financials ซึ่งโหลดมาจาก
    master_all_8_stocks_financials.csv ผ่าน import_data.py) เท่านั้น ผ่าน _extract_metrics()/to_float_or_nan()
    ไม่มีจุดไหนในไฟล์นี้เอา net_income, total_equity, total_liabilities ฯลฯ มาคำนวณ ratio ใหม่เอง
    ⚠️ เงื่อนไขที่ทำให้ข้อนี้เป็นจริง "อยู่นอกไฟล์นี้": ชื่อคอลัมน์ที่ import_data.py map จาก CSV ต้องตรงกับ
       REQUIRED_COLS ด้านล่างเป๊ะ (roe, roa, de_ratio, current_ratio - ตัวพิมพ์เล็ก) ถ้า CSV ต้นทางใช้หัวคอลัมน์
       ต่างจากนี้ (เช่น "ROE (%)") แล้ว import_data.py ไม่ได้ rename ให้ตรง จะทำให้ _extract_metrics() ได้ NaN
       ทุกค่าแบบเงียบๆ (เข้าใจผิดว่าเป็น Issue 02 ทั้งที่จริงเป็นปัญหา config) -- ดู _validate_columns() ด้านล่าง
       ที่เพิ่มเข้ามาเพื่อดักกรณีนี้ให้ error ชัดเจนแทนที่จะปล่อยเป็น N/A เงียบๆ ***

build_health_score_yearly(df_fin_ticker) คืน pd.DataFrame คอลัมน์ [year, health_score]
    ใช้วาดกราฟ "Company Health Score Trend" ในหน้า Company Health
    ปีที่ข้อมูลไม่ครบ health_score = NaN (กราฟจะไม่วาดจุดของปีนั้น)

*** [ISSUE 05] การเปลี่ยนแปลง contract: health_score ที่คืนจากฟังก์ชันนี้เป็น "คะแนนดิบ" ช่วง 0-100 เต็ม
    ไม่ถูกตัดขอบล่างที่ 25 เหมือนเดิมอีกต่อไป (เอา np.clip(score, 25, 98) ออกเฉพาะฟังก์ชันนี้)
    ⚠️ ผลข้างเคียงที่ตั้งใจ: จุดปี "ล่าสุด" ในกราฟ Trend อาจมีค่า "ไม่เท่ากับ" health_score บนการ์ดหลัก
       ของหน้า Company Health อีกต่อไป (การ์ดหลักยังใช้ calculate_health_module ซึ่งยังตัดขอบ 25-98 ตามเดิม
       -- คงไว้ตามขอบเขตที่ Issue 05 ระบุให้แก้เฉพาะ build_health_score_yearly) ถ้าต้องการให้ตัวเลขสองจุดนี้
       ตรงกันเป๊ะ ต้องตัดสินใจเพิ่มว่าจะเอา clip ออกจากการ์ดหลักด้วยหรือไม่ (ยังไม่ทำในรอบแก้ไขนี้) ***

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

# [ISSUE 03] เพดาน D/E ต่อกลุ่มอุตสาหกรรม (Dynamic Threshold) แทนค่า fix 2.5 เท่าเดิม
# ที่มา: ตาราง config นี้ "ต้องให้ทีมอนุมัติตัวเลขจริง" -- ค่าด้านล่างเป็นค่าตั้งต้นสำหรับให้ทีมพิจารณา/ปรับ
#        เท่านั้น ไม่ใช่ตัวเลขที่อ้างอิงมาตรฐานอุตสาหกรรมที่ตรวจสอบแล้ว (ดู ISSUE 03 ในรายงาน Root Cause)
# ทำไมใช้ตาราง config แทนการคำนวณค่าเฉลี่ยสดจาก peers ในฐานข้อมูล:
#   ฐานข้อมูลมีหุ้นแค่ 8 ตัว บางกลุ่ม (ดู SECTOR_MAP ใน common.py) มี peer แค่ 1-2 ตัว
#   ค่าเฉลี่ยที่ได้จะไม่มีนัยสำคัญทางสถิติและแกว่งง่ายตามหุ้นตัวเดียว จึงเลือกใช้เกณฑ์คงที่ต่อกลุ่มแทน
# key ต้องตรงกับค่าใน SECTOR_MAP (common.py) เป๊ะ ทุกตัวอักษร มิฉะนั้นจะตกไปใช้ DEFAULT_DE_THRESHOLD เงียบๆ
DE_SECTOR_THRESHOLDS = {
    'Technology & Telecomm': 2.5,   # TODO ทีม: ยืนยัน/ปรับตัวเลขนี้
    'Electronic Components': 1.8,   # TODO ทีม: กลุ่มนี้มักมีหนี้เพื่อลงทุนเครื่องจักรสูง พิจารณาว่าควรสูงกว่านี้หรือไม่
    'Commerce & Technology': 2.2,   # TODO ทีม: ยืนยัน/ปรับตัวเลขนี้
}
DEFAULT_DE_THRESHOLD = 2.5   # ใช้เมื่อไม่รู้จัก sector / ไม่ได้ส่ง sector มา -- เท่ากับค่าคงที่เดิมก่อนแก้ (ไม่ Breaking Change)


def get_de_threshold(sector):
    """[ISSUE 03] คืนเพดาน D/E ที่ควรใช้กับกลุ่มอุตสาหกรรมนี้ (คืน DEFAULT ถ้าไม่รู้จักกลุ่ม/ไม่ได้ส่งมา)"""
    if not sector:
        return DEFAULT_DE_THRESHOLD
    return DE_SECTOR_THRESHOLDS.get(sector, DEFAULT_DE_THRESHOLD)


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


def _validate_columns(df_fin_ticker):
    """[ISSUE 04] เช็คว่า df ที่ส่งเข้ามามีคอลัมน์ตาม REQUIRED_COLS จริงหรือไม่ (เช็ค schema ไม่ใช่ค่าที่ขาด)
    แยกให้ชัดจาก ISSUE 02: ถ้าคอลัมน์ "มีอยู่" แต่บางแถว/บางปีไม่มีค่า -> นั่นคือ ISSUE 02 (NaN ปกติ)
    ถ้าคอลัมน์ "ไม่มีอยู่เลย" ใน DataFrame -> เป็นบั๊ก config/schema mismatch (เช่น import_data.py แม็พชื่อ
    คอลัมน์จาก CSV ผิด) ต้อง error ทันทีตอน dev/test แทนที่จะปล่อยให้กลายเป็น N/A ทุกตัวแบบเงียบๆ ตอน production"""
    if df_fin_ticker is None or len(df_fin_ticker) == 0:
        return   # ไม่มีงบเลยเป็นกรณีที่ยอมรับได้ (ดู ISSUE 02) ไม่ใช่บั๊ก config
    missing_cols = [c for c in REQUIRED_COLS if c not in df_fin_ticker.columns]
    if missing_cols:
        raise KeyError(
            f"[ISSUE 04] ไม่พบคอลัมน์ {missing_cols} ในข้อมูลงบการเงินที่ส่งเข้ามา "
            f"(คอลัมน์ที่มีจริง: {list(df_fin_ticker.columns)}). "
            "ตรวจสอบว่า import_data.py แม็พชื่อคอลัมน์จาก master_all_8_stocks_financials.csv "
            "เป็น roe/roa/de_ratio/current_ratio (ตัวพิมพ์เล็ก) ตรงกับ Data Contract ของไฟล์นี้แล้วหรือยัง "
            "(ห้ามแก้ด้วยการคำนวณ/เดาชื่อคอลัมน์เองในไฟล์นี้ -- ต้องแก้ที่ import_data.py หรือ schema กลาง)"
        )


def _extract_metrics(r):
    """ดึงค่า (roe, roa, de, current_ratio) จากแถวงบ 1 แถว (Series หรือ dict) ตามชื่อคอลัมน์ในฐานข้อมูลกลาง
    [ISSUE 04] อ่านตรงจากคอลัมน์เท่านั้น ไม่มีการคำนวณ/ประมาณค่า ratio ขึ้นมาเองในฟังก์ชันนี้"""
    return tuple(to_float_or_nan(r.get(c)) for c in REQUIRED_COLS)


def _compute_scores(roe, roa, de, curr_ratio, de_threshold=DEFAULT_DE_THRESHOLD):
    """สูตรคะแนนชุดเดียว ใช้ร่วมกันทั้งปีล่าสุดและรายปี (กันสูตรสองที่ไม่ตรงกัน)
    NaN ในตัวแปรใดๆ จะส่งต่อเป็น NaN ในคะแนนที่เกี่ยวข้อง (np.clip / การคูณ ไม่ทำให้ NaN หาย)

    [ISSUE 03] s_debt: de_threshold คือเพดาน D/E ของกลุ่มอุตสาหกรรมนั้นๆ (มาจาก get_de_threshold())
    สูตรคง "รูปทรง" เดิมไว้ (de=0 -> เต็ม 100, de=threshold -> 0) แค่ตัวคูณ (เดิม fix 40.0)
    เปลี่ยนเป็น 100/threshold เพื่อให้เพดานขยับได้ตามกลุ่ม โดยที่ threshold=2.5 จะได้ผลเป๊ะเท่าสูตรเดิม"""
    s_roe = np.clip(roe * 3.5, 0, 100)
    s_roa = np.clip(roa * 7.0, 0, 100)
    s_liq = np.clip(curr_ratio * 45.0, 0, 100)
    thr = de_threshold if de_threshold and de_threshold > 0 else DEFAULT_DE_THRESHOLD
    s_debt = np.clip((thr - de) * (100.0 / thr), 0, 100)
    raw = (
        s_roe * HEALTH_WEIGHTS['roe'] + s_roa * HEALTH_WEIGHTS['roa']
        + s_liq * HEALTH_WEIGHTS['liquidity'] + s_debt * HEALTH_WEIGHTS['debt']
    )   # NaN ถ้าขาดตัวใดตัวหนึ่ง => ไม่ให้คะแนนรวมจากข้อมูลไม่ครบ
    return s_roe, s_roa, s_liq, s_debt, raw


def _final_score(raw, clip_to_business_range=True):
    """ปัดค่าคะแนนสุดท้าย; NaN ผ่านได้เสมอ (np.clip(nan, ..) = nan)

    clip_to_business_range=True  (ค่าเริ่มต้น ใช้ใน calculate_health_module / การ์ดคะแนนหลัก):
        ตัดขอบ 25-98 ตามกฎ Business เดิม (heuristic เดิมของทีม ไม่แตะในรอบแก้ไขนี้ -- Issue 05
        ขอให้แก้เฉพาะ build_health_score_yearly เท่านั้น)

    clip_to_business_range=False [ISSUE 05] ใช้ใน build_health_score_yearly (กราฟ Trend):
        ไม่ตัดขอบ 25-98 อีกต่อไป ส่งคะแนนดิบ (Raw Score) ตามจริง
        ยังกัน [0, 100] ไว้เป็น "ขอบเขตทางคณิตศาสตร์" เฉย ๆ (กัน float คลาดเคลื่อนเกิน 100.000001
        จาก s_roe/s_roa/s_liq/s_debt ที่ clip ไว้ 0-100 แต่ละตัวอยู่แล้ว และ HEALTH_WEIGHTS รวมกัน = 1.0
        ตามทฤษฎี raw จะไม่มีทางเกิน [0,100] อยู่แล้ว) ไม่ใช่การตัดขอบเชิงธุรกิจแบบ 25-98 เดิม"""
    lo, hi = (25, 98) if clip_to_business_range else (0, 100)
    return round(float(np.clip(raw, lo, hi)), 1)


def _r(x, nd):
    """round ที่รักษา NaN ไว้"""
    return round(float(x), nd)


def calculate_health_module(df_fin_ticker, sector=None):
    """Module 1: Company Health (ใช้งบปีล่าสุดที่มีจริง — ไม่ย้อนเอาค่าปีก่อนมาเติมช่องว่าง)
    sector: [ISSUE 03] ส่งชื่อกลุ่มอุตสาหกรรม (เช่น จาก SECTOR_MAP) เพื่อเลือกเพดาน D/E ที่เหมาะสม
            ถ้าไม่ส่งมา จะใช้ DEFAULT_DE_THRESHOLD (พฤติกรรมเดิมก่อนแก้ไข)"""
    _validate_columns(df_fin_ticker)   # [ISSUE 04] เช็ค schema ก่อน ไม่ใช่แค่เช็คค่าขาด
    if df_fin_ticker is None or len(df_fin_ticker) == 0:
        r = {}   # ไม่มีงบเลย -> ทุกตัวเป็น NaN แทนที่จะ crash ทั้ง pipeline
    else:
        r = df_fin_ticker.sort_values(by='year').iloc[-1]

    roe, roa, de, curr_ratio = _extract_metrics(r)
    de_threshold = get_de_threshold(sector)
    s_roe, s_roa, s_liq, s_debt, raw = _compute_scores(roe, roa, de, curr_ratio, de_threshold)

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
        'de_threshold_used': de_threshold,
    }


def build_health_score_yearly(df_fin_ticker, sector=None):
    """คำนวณคะแนน Health รายปีจากงบการเงินจริงแต่ละปี เพื่อวาดกราฟ trend
    (ใช้ _compute_scores ชุดเดียวกับ calculate_health_module(); ปีที่ข้อมูลไม่ครบ health_score = NaN)
    sector: [ISSUE 03] ใช้เพดาน D/E เดียวกันทุกปี (กลุ่มอุตสาหกรรมของหุ้นไม่เปลี่ยนปีต่อปี) เพื่อให้กราฟ
            Trend เทียบกันได้อย่างสมเหตุสมผล ไม่ใช่คนละเกณฑ์คนละปี"""
    import pandas as pd
    _validate_columns(df_fin_ticker)   # [ISSUE 04] เช็ค schema ก่อน ไม่ใช่แค่เช็คค่าขาด
    rows = []
    de_threshold = get_de_threshold(sector)
    if df_fin_ticker is not None and len(df_fin_ticker) > 0:
        for _, r in df_fin_ticker.sort_values('year').iterrows():
            roe, roa, de, curr_ratio = _extract_metrics(r)
            *_, raw = _compute_scores(roe, roa, de, curr_ratio, de_threshold)
            rows.append({'year': int(r['year']), 'health_score': _final_score(raw, clip_to_business_range=False)})   # [ISSUE 05] Raw Score
    return pd.DataFrame(rows, columns=['year', 'health_score'])
