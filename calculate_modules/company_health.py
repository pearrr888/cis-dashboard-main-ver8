"""
company_health Cal.py (หรือ calculate_modules/company_health.py)
--------------------------------------------------------------
"""
import numpy as np
import pandas as pd

def clean_float_or_na(val):
    """
    Issue 02: ตรวจจับข้อมูลว่างเปล่า (NaN/None) หากไม่มีข้อมูลให้คืนค่า np.nan 
    เพื่อป้องกัน Error คณิตศาสตร์ และใช้เป็นสัญลักษณ์ว่าข้อมูลแหว่ง (ห้ามใช้ค่า Default)
    """
    if pd.isna(val) or val is None:
        return np.nan
    if isinstance(val, (int, float)):
        return float(val)
    try:
        cleaned = str(val).replace(',', '').replace('%', '').strip()
        if cleaned in ['', '-', 'nan', 'None']:
            return np.nan
        return float(cleaned)
    except Exception:
        return np.nan

def calculate_health_module(df_fin_ticker, sector=None):
    """Module 1: Company Health (คำนวณจากงบปีล่าสุด)"""
    row_latest = df_fin_ticker.sort_values(by='year').iloc[[-1]]
    r = row_latest.iloc[0]

    # Issue 04: ดึงค่าโดยตรงจากชื่อคอลัมน์มาตรฐาน
    roe_val = clean_float_or_na(r.get('roe'))
    roa_val = clean_float_or_na(r.get('roa'))
    de_val = clean_float_or_na(r.get('de_ratio'))
    cr_val = clean_float_or_na(r.get('current_ratio'))

    missing_fields = []
    
    # ดักจับว่าตัวแปรใดแหว่งบ้าง
    if pd.isna(roe_val): missing_fields.append('ROE')
    if pd.isna(roa_val): missing_fields.append('ROA')
    if pd.isna(de_val): missing_fields.append('D/E Ratio')
    if pd.isna(cr_val): missing_fields.append('Current Ratio')

    # Issue 03: ปรับตรรกะ D/E Ratio (Dynamic Threshold)
    # หากเป็นกลุ่ม Technology/Telecomm ให้ยอมรับเพดานหนี้ได้สูงขึ้น
    de_threshold = 2.5
    if sector and "Technology" in str(sector):
        de_threshold = 3.5

    # Issue 01: น้ำหนัก 4 มิติที่ใช้จริง
    w_roe, w_roa, w_liq, w_debt = 0.30, 0.25, 0.20, 0.25

    if missing_fields:
        # หากข้อมูลแหว่ง กำหนดให้คะแนนเป็น np.nan (แทน 0 หรือ Default เพื่อไม่ให้บิดเบือน)
        health_score = np.nan
        s_roe = s_roa = s_liq = s_debt = np.nan
    else:
        s_roe = np.clip(roe_val * 3.5, 0, 100)
        s_roa = np.clip(roa_val * 7.0, 0, 100)
        s_liq = np.clip(cr_val * 45.0, 0, 100)
        s_debt = np.clip((de_threshold - de_val) * 40.0, 0, 100)
        
        raw_score = (s_roe * w_roe) + (s_roa * w_roa) + (s_liq * w_liq) + (s_debt * w_debt)
        # ขยาย Scale เป็น 0-100 เต็มรูปแบบ
        health_score = round(float(np.clip(raw_score, 0, 100)), 1)

    return {
        'health_score': health_score, # เป็น float หรือ np.nan
        
        # Issue 02: คืนข้อความ "N/A" สำหรับให้ UI แสดงผลทันที
        'roe': "N/A" if pd.isna(roe_val) else round(roe_val, 2),
        'roa': "N/A" if pd.isna(roa_val) else round(roa_val, 2),
        'de_ratio': "N/A" if pd.isna(de_val) else round(de_val, 2),
        'current_ratio': "N/A" if pd.isna(cr_val) else round(cr_val, 2),
        
        # Issue 01: คืนค่ามิติจริง 4 ตัวพร้อมน้ำหนัก
        'dim_roe_score': "N/A" if pd.isna(s_roe) else round(float(s_roe), 1),
        'dim_roe_weight': f"{int(w_roe*100)}%",
        'dim_roa_score': "N/A" if pd.isna(s_roa) else round(float(s_roa), 1),
        'dim_roa_weight': f"{int(w_roa*100)}%",
        'dim_liquidity_score': "N/A" if pd.isna(s_liq) else round(float(s_liq), 1),
        'dim_liquidity_weight': f"{int(w_liq*100)}%",
        'dim_debt_score': "N/A" if pd.isna(s_debt) else round(float(s_debt), 1),
        'dim_debt_weight': f"{int(w_debt*100)}%",
        
        'health_data_complete': len(missing_fields) == 0,
        'health_missing_fields': ', '.join(missing_fields) if missing_fields else ''
    }

def build_health_score_yearly(df_fin_ticker, sector=None):
    """สำหรับวาดกราฟ Trend ย้อนหลัง 3 ปี"""
    rows = []
    
    de_threshold = 2.5
    if sector and "Technology" in str(sector):
        de_threshold = 3.5

    for _, r in df_fin_ticker.sort_values('year').iterrows():
        roe = clean_float_or_na(r.get('roe'))
        roa = clean_float_or_na(r.get('roa'))
        de = clean_float_or_na(r.get('de_ratio'))
        cr = clean_float_or_na(r.get('current_ratio'))
        
        # หากปีไหนข้อมูลแหว่ง ให้ข้ามไป ไม่ใช้ค่า Default มาหลอกวาดกราฟ
        if pd.isna(roe) or pd.isna(roa) or pd.isna(de) or pd.isna(cr):
            continue

        s_roe = np.clip(roe * 3.5, 0, 100)
        s_roa = np.clip(roa * 7.0, 0, 100)
        s_liq = np.clip(cr * 45.0, 0, 100)
        s_debt = np.clip((de_threshold - de) * 40.0, 0, 100)

        score_raw = (s_roe * 0.30) + (s_roa * 0.25) + (s_liq * 0.20) + (s_debt * 0.25)
        
        # Issue 05: ปลดล็อก np.clip(score, 25, 98) ออก ปล่อยคะแนนดิบ 0-100 ลงกราฟ
        score_final = round(float(np.clip(score_raw, 0, 100)), 1)
        rows.append({'year': int(r['year']), 'health_score': score_final})
        
    return pd.DataFrame(rows)
