"""
calculate_modules/company_health.py
-------------------------------------
สูตรคำนวณโมดูล "Company Health" (💚)
"""

import numpy as np
import pandas as pd

def clean_float_or_na(val):
    """
    Issue 02: แปลงข้อความ/ตัวเลขให้เป็น float หากว่างเปล่าหรือแปลงไม่ได้ คืนค่า "N/A"
    """
    if pd.isna(val) or val is None:
        return "N/A"
    if isinstance(val, (int, float)):
        return float(val)
    try:
        cleaned = str(val).replace(',', '').replace('%', '').strip()
        if cleaned in ['', '-', 'nan', 'None']:
            return "N/A"
        return float(cleaned)
    except Exception:
        return "N/A"

def calculate_health_module(df_fin_ticker, sector=None):
    """
    Module 1: Company Health
    คำนวณสุขภาพการเงินจาก 4 ตัวชี้วัดหลัก: ROE, ROA, D/E Ratio, Current Ratio
    """
    row_latest = df_fin_ticker.sort_values(by='year').iloc[[-1]]
    r = row_latest.iloc[0]

    # Issue 04: ดึงค่าโดยตรงจากชื่อคอลัมน์ในฐานข้อมูลกลาง
    roe_val = clean_float_or_na(r.get('roe'))
    roa_val = clean_float_or_na(r.get('roa'))
    de_val = clean_float_or_na(r.get('de_ratio'))
    cr_val = clean_float_or_na(r.get('current_ratio'))

    missing_fields = []
    
    def get_valid(val, field_name):
        if val == "N/A":
            missing_fields.append(field_name)
            return 0.0 # ให้คะแนนชั่วคราวเป็น 0 เพื่อรันต่อ แต่จะถูกดักไว้ใน missing_fields
        return val

    roe_num = get_valid(roe_val, 'ROE')
    roa_num = get_valid(roa_val, 'ROA')
    de_num = get_valid(de_val, 'D/E Ratio')
    cr_num = get_valid(cr_val, 'Current Ratio')

    # Issue 03: Dynamic Threshold สำหรับ D/E Ratio ตาม Sector
    de_threshold = 2.5
    if sector and "Technology" in sector:
        de_threshold = 3.5

    # คำนวณคะแนนย่อย
    s_roe = np.clip(roe_num * 3.5, 0, 100)
    s_roa = np.clip(roa_num * 7.0, 0, 100)
    s_liq = np.clip(cr_num * 45.0, 0, 100)
    s_debt = np.clip((de_threshold - de_num) * 40.0, 0, 100)

    # Issue 01: ถ่วงน้ำหนัก 4 มิติ
    w_roe, w_roa, w_liq, w_debt = 0.30, 0.25, 0.20, 0.25
    health_score_raw = (s_roe * w_roe) + (s_roa * w_roa) + (s_liq * w_liq) + (s_debt * w_debt)

    # ขยายช่วงเป็น 0-100 ไม่ล็อคคะแนน
    health_score = round(float(np.clip(health_score_raw, 0, 100)), 1)

    return {
        'health_score': health_score if not missing_fields else "N/A",
        
        'roe': roe_val if roe_val == "N/A" else round(roe_val, 2),
        'roa': roa_val if roa_val == "N/A" else round(roa_val, 2),
        'de_ratio': de_val if de_val == "N/A" else round(de_val, 2),
        'current_ratio': cr_val if cr_val == "N/A" else round(cr_val, 2),
        
        # Issue 01: ส่งคะแนนมิติหลัก 4 ตัวพร้อมน้ำหนักจริงกลับไปที่ UI
        'dim_roe_score': round(float(s_roe), 1),
        'dim_roe_weight': f"{int(w_roe*100)}%",
        'dim_roa_score': round(float(s_roa), 1),
        'dim_roa_weight': f"{int(w_roa*100)}%",
        'dim_liquidity_score': round(float(s_liq), 1),
        'dim_liquidity_weight': f"{int(w_liq*100)}%",
        'dim_debt_score': round(float(s_debt), 1),
        'dim_debt_weight': f"{int(w_debt*100)}%",
        
        'health_data_complete': len(missing_fields) == 0,
        'health_missing_fields': ', '.join(missing_fields) if missing_fields else ''
    }

def build_health_score_yearly(df_fin_ticker, sector=None):
    """
    คำนวณคะแนน Health Score แบบ Time-series สำหรับวาดกราฟ Trend
    """
    rows = []
    
    de_threshold = 2.5
    if sector and "Technology" in sector:
        de_threshold = 3.5

    for _, r in df_fin_ticker.sort_values('year').iterrows():
        roe = clean_float_or_na(r.get('roe'))
        roa = clean_float_or_na(r.get('roa'))
        de = clean_float_or_na(r.get('de_ratio'))
        cr = clean_float_or_na(r.get('current_ratio'))
        
        if "N/A" in [roe, roa, de, cr]:
            continue

        s_roe = np.clip(roe * 3.5, 0, 100)
        s_roa = np.clip(roa * 7.0, 0, 100)
        s_liq = np.clip(cr * 45.0, 0, 100)
        s_debt = np.clip((de_threshold - de) * 40.0, 0, 100)

        score = (s_roe * 0.30) + (s_roa * 0.25) + (s_liq * 0.20) + (s_debt * 0.25)
        
        # Issue 05: ตัด np.clip(25, 98) ออก ส่งค่าดิบ 0-100 ลงกราฟ
        score_raw = round(float(np.clip(score, 0, 100)), 1)
        rows.append({'year': int(r['year']), 'health_score': score_raw})
        
    return pd.DataFrame(rows)
