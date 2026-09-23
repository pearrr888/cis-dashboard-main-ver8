"""
calculate_scores.py — Orchestrator (Data Pipeline / Integration Lead ดูแลไฟล์นี้)
------------------------------------------------------------------------------------
ไฟล์นี้ "ไม่มีสูตรคำนวณของโมดูลไหนอยู่ในนี้แล้ว" — ทำหน้าที่แค่:
    1. โหลดข้อมูลจากฐานข้อมูล
    2. วนลูปแต่ละหุ้น เรียกฟังก์ชันคำนวณของทั้ง 6 โมดูลจาก calculate_modules/
    3. รวมผลลัพธ์ + บันทึกกลับลงฐานข้อมูล

สูตร/ตรรกะการคำนวณจริงของแต่ละโมดูลอยู่ที่:
    calculate_modules/company_health.py       (เจ้าของ: คนที่ดูแล pages_content/company_health.py)
    calculate_modules/fair_value.py           (เจ้าของ: คนที่ดูแล pages_content/fair_value.py)
    calculate_modules/entry_timing.py         (เจ้าของ: คนที่ดูแล pages_content/entry_timing.py)
    calculate_modules/ai_prediction.py        (เจ้าของ: คนที่ดูแล pages_content/ai_prediction.py)
    calculate_modules/risk_analysis.py        (เจ้าของ: คนที่ดูแล pages_content/risk_analysis.py)
    calculate_modules/industry_benchmark.py   (เจ้าของ: คนที่ดูแล pages_content/industry_benchmark.py)

⚠️ ไฟล์นี้เป็น "ของกลาง" เหมือน common.py ของฝั่ง UI — โดยปกติ เจ้าของแต่ละโมดูลไม่ต้องแก้ไฟล์นี้เลย
แก้แค่ calculate_modules/<โมดูลของตัวเอง>.py พอ ถ้าจำเป็นต้องแก้ไฟล์นี้ (เช่น เพิ่มตารางผลลัพธ์ใหม่)
ให้แจ้ง Data Pipeline / Integration Lead ก่อน
"""

import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime

from calculate_modules.common import clean_float, SECTOR_MAP
from calculate_modules import company_health, fair_value, entry_timing, ai_prediction, risk_analysis, industry_benchmark

DB_NAME = 'cis_database.db'
TARGET_STOCKS = ['ADVANC', 'CCET', 'DELTA', 'HANA', 'JMART', 'KCE', 'THCOM', 'TRUE']


def load_data_from_db(engine):
    df_fin = pd.read_sql("SELECT * FROM stock_financials", con=engine)
    df_price = pd.read_sql("SELECT * FROM stock_daily_prices", con=engine)
    df_price['date'] = pd.to_datetime(df_price['date'])
    try:
        df_risk = pd.read_sql("SELECT * FROM stock_risk_static", con=engine)
    except Exception:
        df_risk = pd.DataFrame(columns=['ticker', 'beta', 'volatility_pct', 'max_drawdown_pct'])
    return df_fin, df_price, df_risk


def run_full_pipeline():
    engine = create_engine(f'sqlite:///{DB_NAME}')
    df_fin_all, df_price_all, df_risk_all = load_data_from_db(engine)

    print("\n--- เริ่มประมวลผลระบบ CIS Scoring สำหรับหุ้นทั้ง 8 ตัว (ใช้ข้อมูลจริงทั้งหมด) ---")
    all_summary = []
    all_feature_importance = []
    all_backtest = []
    all_risk_history = []
    all_health_yearly = []
    all_fair_value_yearly = []

    for ticker in TARGET_STOCKS:
        fin_sub = df_fin_all[df_fin_all['ticker'] == ticker]
        price_sub = df_price_all[df_price_all['ticker'] == ticker].sort_values(by='date')
        risk_sub = df_risk_all[df_risk_all['ticker'] == ticker] if not df_risk_all.empty else None

        if price_sub.empty:
            continue

        current_price = round(clean_float(price_sub.iloc[-1]['close'], default=10.0), 2)
        latest_date = str(price_sub.iloc[-1]['date'])[:10]
        if len(price_sub) >= 2:
            prev_close = clean_float(price_sub.iloc[-2]['close'], default=current_price)
            change_val = round(current_price - prev_close, 2)
            change_pct = round((change_val / prev_close) * 100, 2) if prev_close else 0.0
        else:
            change_val, change_pct = 0.0, 0.0

        sector = SECTOR_MAP.get(ticker, 'Technology')
        
        # [ป้องกัน TypeError] ดักจับกรณีโมดูลพังและส่ง None กลับมา ให้แปลงเป็น Dictionary เปล่าแทน
        m1 = company_health.calculate_health_module(fin_sub, sector=sector) or {}
        m2 = fair_value.calculate_valuation_module(fin_sub, current_price, ticker) or {}
        m3 = entry_timing.calculate_timing_module(price_sub) or {}
        
        try:
            m4, feat_imp, backtest_df = ai_prediction.train_and_predict_ai(price_sub, ticker)
        except Exception:
            m4, feat_imp, backtest_df = {}, {}, pd.DataFrame()
            
        m4 = m4 or {}
        m5 = risk_analysis.calculate_risk_module(price_sub, risk_sub) or {}

        fin_sorted = fin_sub.sort_values('year')
        rev_growth, ni_growth = None, None
        if len(fin_sorted) >= 2:
            rev_prev, rev_curr = fin_sorted.iloc[-2]['total_revenue'], fin_sorted.iloc[-1]['total_revenue']
            ni_prev, ni_curr = fin_sorted.iloc[-2]['net_income'], fin_sorted.iloc[-1]['net_income']
            if rev_prev and clean_float(rev_prev) != 0:
                rev_growth = round((clean_float(rev_curr) - clean_float(rev_prev)) / clean_float(rev_prev) * 100, 1)
            if ni_prev and clean_float(ni_prev) != 0:
                ni_growth = round((clean_float(ni_curr) - clean_float(ni_prev)) / clean_float(ni_prev) * 100, 1)
        
        latest_row = fin_sorted.iloc[-1] if not fin_sorted.empty else None
        fcf_latest = round(clean_float(latest_row.get('free_cash_flow')), 1) if latest_row is not None else None

        all_summary.append({
            'ticker': ticker,
            'current_price': current_price,
            'change_val': change_val,
            'change_pct': change_pct,
            'latest_date': latest_date,
            'sector': sector,
            'revenue_growth_yoy': rev_growth,
            'net_income_growth_yoy': ni_growth,
            'free_cash_flow_latest': fcf_latest,
            **m1, **m2, **m3, **m4, **m5
        })

        if isinstance(feat_imp, dict):
            for f, imp in feat_imp.items():
                all_feature_importance.append({'ticker': ticker, 'feature': f, 'importance': imp})

        if isinstance(backtest_df, pd.DataFrame) and not backtest_df.empty:
            bt = backtest_df.copy()
            bt['ticker'] = ticker
            all_backtest.append(bt)

        rh = risk_analysis.build_risk_rolling_history(price_sub)
        if isinstance(rh, pd.DataFrame) and not rh.empty:
            rh['ticker'] = ticker
            all_risk_history.append(rh)

        hy = company_health.build_health_score_yearly(fin_sub, sector=sector)
        if isinstance(hy, pd.DataFrame) and not hy.empty:
            hy['ticker'] = ticker
            all_health_yearly.append(hy)

        fv = fair_value.build_fair_value_yearly(fin_sub, price_sub, ticker)
        if isinstance(fv, pd.DataFrame) and not fv.empty:
            fv['ticker'] = ticker
            all_fair_value_yearly.append(fv)

    df_res = pd.DataFrame(all_summary)

    # ===== โมดูลสุดท้าย: Industry Benchmark =====
    df_res = industry_benchmark.compute_industry_rankings(df_res)
    df_res['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ===== บันทึกผลลัพธ์ทั้งหมดลงฐานข้อมูล =====
    df_res.to_sql('cis_summary_scores', con=engine, if_exists='replace', index=False)

    df_feat = pd.DataFrame(all_feature_importance)
    if not df_feat.empty:
        df_feat.to_sql('ai_feature_importance', con=engine, if_exists='replace', index=False)

    if all_backtest:
        df_bt = pd.concat(all_backtest, ignore_index=True)
        df_bt['date'] = df_bt['date'].astype(str)
        df_bt.to_sql('ai_backtest_history', con=engine, if_exists='replace', index=False)

    if all_risk_history:
        df_rh = pd.concat(all_risk_history, ignore_index=True)
        df_rh['date'] = df_rh['date'].astype(str)
        df_rh.to_sql('risk_rolling_history', con=engine, if_exists='replace', index=False)

    if all_health_yearly:
        df_hy = pd.concat(all_health_yearly, ignore_index=True)
        df_hy.to_sql('health_score_yearly', con=engine, if_exists='replace', index=False)

    if all_fair_value_yearly:
        df_fv = pd.concat(all_fair_value_yearly, ignore_index=True)
        df_fv.to_sql('fair_value_yearly', con=engine, if_exists='replace', index=False)

    print("\n✅ ประมวลผลและบันทึกคะแนนจริงของหุ้นทั้ง 8 ตัวลง cis_database.db เรียบร้อยแล้ว:")
    print("=" * 85)
    
    # [ป้องกัน KeyError] เลือก Print เฉพาะคอลัมน์ที่มีอยู่จริงใน DataFrame เท่านั้น
    expected_cols = ['ticker', 'current_price', 'fair_value', 'margin_of_safety', 'overall_score',
                     'recommendation', 'health_score', 'ai_score', 'beta']
    exist_cols = [c for c in expected_cols if c in df_res.columns]
    print(df_res[exist_cols])
    print("=" * 85)


if __name__ == '__main__':
    run_full_pipeline()
