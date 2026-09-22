"""
pages_content/company_health.py
---------------------------
หน้า "Company Health" ของ CIS Dashboard

วิธีทดสอบหน้านี้แบบเดี่ยว (ไม่ต้องรอทีมคนอื่น):
    streamlit run preview_my_page.py
    (แล้วเลือกโมดูลนี้จาก dropdown ในไฟล์ preview_my_page.py)

ข้อมูลที่ใช้ได้ใน ctx (ดูนิยามเต็มใน common.py -> class PageContext):
    ctx.selected_ticker, ctx.stock_info, ctx.stock_daily, ctx.fin_stock, ctx.sector_peers,
    ctx.scores_df, ctx.fin_df, ctx.feat_imp_df, ctx.backtest_df, ctx.risk_hist_df,
    ctx.health_yearly_df, ctx.fair_value_yearly_df,
    ctx.current_price, ctx.change_pct, ctx.change_val, ctx.change_color, ctx.change_sign, ctx.arrow_sign

ห้ามแก้ CSS ส่วนกลางหรือ helper function ใน common.py จากไฟล์นี้ — ถ้าจำเป็นต้องแก้ ให้แจ้ง Layout Lead ก่อน
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from common import fmt_mb, fmt_ratio, safe, show_chart, render_nav_footer, COMPANY_NAMES, SECTOR_MAP
from calculate_modules.company_health import HEALTH_WEIGHTS  # [ISSUE 01] น้ำหนักจริงที่ใช้คิดคะแนนรวม


def render(ctx):

    def get_fin_val(target_yr, col_name, default="-", fmt="{:.1f}"):
        match = ctx.fin_stock[ctx.fin_stock['year'] == target_yr]
        if not match.empty:
            v = match.iloc[0].get(col_name)
            if v is not None and str(v).strip() not in ['', '-', 'nan', 'None']:
                try:
                    return fmt.format(float(v))
                except Exception:
                    return str(v)
        return str(default)

    def num_or_none(v):
        """[ISSUE 02] แปลงเป็น float; ถ้าไม่มีค่า ('-', 'nan', None, NaN) คืน None -- ไม่แทนด้วย 0 หรือค่าสมมติ"""
        try:
            f = float(v)
        except (TypeError, ValueError):
            return None
        return None if np.isnan(f) else f

    FIELD_LABELS = {'roe': 'ROE', 'roa': 'ROA', 'de_ratio': 'D/E', 'current_ratio': 'Current Ratio'}
    _mf = ctx.stock_info.get('missing_fields')
    missing_labels = [FIELD_LABELS.get(c, c) for c in str(_mf).split(',') if c and c != 'nan' and c != 'None'] if _mf else []

    roe_23, roe_24, roe_25 = get_fin_val(2023, 'roe'), get_fin_val(2024, 'roe'), get_fin_val(2025, 'roe')
    roa_23, roa_24, roa_25 = get_fin_val(2023, 'roa'), get_fin_val(2024, 'roa'), get_fin_val(2025, 'roa')
    npm_23, npm_24, npm_25 = get_fin_val(2023, 'net_margin'), get_fin_val(2024, 'net_margin'), get_fin_val(2025, 'net_margin')
    de_23, de_24, de_25 = get_fin_val(2023, 'de_ratio', fmt="{:.2f}"), get_fin_val(2024, 'de_ratio', fmt="{:.2f}"), get_fin_val(2025, 'de_ratio', fmt="{:.2f}")
    cr_23, cr_24, cr_25 = get_fin_val(2023, 'current_ratio', fmt="{:.2f}"), get_fin_val(2024, 'current_ratio', fmt="{:.2f}"), get_fin_val(2025, 'current_ratio', fmt="{:.2f}")

    st.markdown("""<div style="display:flex; justify-content:space-between; align-items:flex-end; margin-bottom:15px;">
    <div><div style="display:flex; align-items:center; gap:8px;"><h2 style="margin:0; font-size:23px; font-weight:bold; color:#F8FAFC; letter-spacing:0.5px;">COMPANY HEALTH</h2></div>
    <div style="font-size:15px; color:#94A3B8; margin-top:2px;">ประเมินสุขภาพทางการเงินของบริษัทจากมิติสำคัญตามงบการเงินจริง</div></div>
    </div>""", unsafe_allow_html=True)

    r1_c1, r1_c2, r1_c3 = st.columns([1.1, 1.4, 1.5])

    # [ISSUE 02] ไม่มีค่า default สมมติ (เดิม 75 = EXCELLENT) -- ถ้า health_score เป็น NaN ให้แสดง N/A
    _hs = num_or_none(ctx.stock_info.get('health_score'))
    if _hs is None:
        h_score, h_ring, h_txt = None, 0, "N/A"
        h_badge, h_color, h_stars = "N/A", "#64748B", 0
        h_sub = "ข้อมูลไม่เพียงพอสำหรับคำนวณคะแนน" + (f" (ขาด: {', '.join(missing_labels)})" if missing_labels else "")
    else:
        h_score = int(round(_hs))
        h_ring, h_txt = h_score, str(h_score)
        h_badge = "EXCELLENT" if h_score >= 75 else ("MODERATE" if h_score >= 50 else "WEAK")
        h_color = "#10B981" if h_score >= 75 else ("#F59E0B" if h_score >= 50 else "#EF4444")
        h_stars = min(5, max(1, round(h_score / 20)))
        h_sub = "ประเมินจากอัตราส่วนทางการเงินจริงปี 2023-2025"

    with r1_c1:
        st.markdown(f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px; padding:16px; min-height:235px; display:flex; flex-direction:column; justify-content:space-between;">
    <div style="font-size:14.5px; font-weight:bold; color:#94A3B8; letter-spacing:0.5px;">COMPANY HEALTH SCORE</div>
    <div style="display:flex; align-items:center; gap:16px; margin:auto 0;">
    <div style="width:92px; height:92px; border-radius:50%; background:conic-gradient({h_color} 0% {h_ring}%, #1E293B {h_ring}% 100%); display:flex; align-items:center; justify-content:center; flex-shrink:0;">
    <div style="width:76px; height:76px; border-radius:50%; background-color:#0F172A; display:flex; flex-direction:column; align-items:center; justify-content:center;">
    <span style="font-size:23px; font-weight:bold; color:#FFFFFF; line-height:1;">{h_txt}</span><span style="font-size:13px; color:#64748B;">{'' if h_score is None else '/100'}</span></div></div>
    <div><div style="color:{h_color}; font-size:18.5px; font-weight:bold; line-height:1.2;">{h_badge}</div>
    <div style="font-size:14.5px; color:#CBD5E1; line-height:1.4; margin-top:4px;">{h_sub}</div>
    <div style="color:{h_color}; font-size:15px; letter-spacing:2px; margin-top:6px;">{'★'*h_stars}{'☆'*(5-h_stars)}</div></div>
    </div></div>""", unsafe_allow_html=True)

    with r1_c2:
        st.markdown(f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px; padding:16px; min-height:235px; display:flex; flex-direction:column; justify-content:space-between;">
    <div><div style="font-size:14.5px; font-weight:bold; color:#94A3B8; letter-spacing:0.5px; margin-bottom:8px;">EXPLAINABLE FINANCIAL SUMMARY ({ctx.selected_ticker})</div>
    <p style="font-size:15px; color:#CBD5E1; line-height:1.6; margin:0;">
    ผลการวิเคราะห์สุขภาพการเงินของ <b>{ctx.selected_ticker}</b> พบว่ามีอัตราส่วนผลตอบแทนต่อส่วนของผู้ถือหุ้น (ROE) ล่าสุดอยู่ที่ {roe_25}% และความสามารถในการทำกำไรสุทธิ (Net Margin) อยู่ที่ {npm_25}% ในขณะที่ภาระหนี้สินต่อทุน (D/E Ratio) อยู่ที่ {de_25} เท่า และสภาพคล่องหมุนเวียน (Current Ratio) อยู่ที่ {cr_25} เท่า
    </p></div>
    <div><span style="display:inline-flex; align-items:center; gap:6px; background-color:#151E2F; border:1px solid #1E293B; color:#38BDF8; font-size:14px; padding:5px 12px; border-radius:6px;">
    Financial Health Benchmark: {ctx.stock_info.get('sector','-')}</span></div>
    </div>""", unsafe_allow_html=True)

    with r1_c3:
        st.markdown("""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px 12px 0 0; padding:12px 16px 0 16px;">
    <div style="font-size:14.5px; font-weight:bold; color:#94A3B8; letter-spacing:0.5px;">COMPANY HEALTH SCORE TREND (Actual, 2023-2025)</div></div>""", unsafe_allow_html=True)

        hy = ctx.health_yearly_df[ctx.health_yearly_df['ticker'] == ctx.selected_ticker].sort_values('year') if not ctx.health_yearly_df.empty else pd.DataFrame()
        # [ISSUE 02] ไม่สร้างเส้นสมมติจาก h_score; ปีที่ไม่มีคะแนน (NaN) จะไม่วาดจุด และแจ้ง N/A ใต้กราฟ
        trend_x = hy['year'].astype(str).tolist() if not hy.empty else []
        trend_y = [num_or_none(v) for v in hy['health_score']] if not hy.empty else []
        na_years = [x for x, y in zip(trend_x, trend_y) if y is None]

        fig_health_trend = go.Figure()
        fig_health_trend.add_trace(go.Scatter(
            x=trend_x, y=trend_y, mode='lines+markers+text', text=[('' if v is None else f'{v:.1f}') for v in trend_y], textposition='top center', connectgaps=False,
            textfont=dict(size=12.5, color='#F8FAFC'), line=dict(color='#10B981', width=2),
            marker=dict(size=10, color='#10B981', line=dict(width=1.5, color='#FFFFFF'))
        ))
        fig_health_trend.update_layout(
            height=168, margin=dict(l=25, r=15, t=10, b=20), paper_bgcolor="#0F172A", plot_bgcolor="#0F172A",
            yaxis=dict(range=[0, 110], tickvals=[0, 25, 50, 75, 100], tickfont=dict(size=11.5, color="#64748B"), gridcolor="#1E293B", zeroline=False),
            xaxis=dict(tickfont=dict(size=12, color="#94A3B8"), gridcolor="#1E293B"), showlegend=False
        )
        if not any(v is not None for v in trend_y):
            fig_health_trend.add_annotation(text="N/A - ข้อมูลไม่เพียงพอสำหรับกราฟ Trend", showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper", font=dict(size=13, color="#94A3B8"))
        show_chart(fig_health_trend, key="health_trend", expand_height=650)
        if na_years and any(v is not None for v in trend_y):
            st.markdown(f"<div style='font-size:12px; color:#F59E0B;'>N/A: ปี {', '.join(na_years)} ข้อมูลงบไม่ครบ จึงไม่แสดงคะแนน</div>", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:22px;'></div>", unsafe_allow_html=True)
    # ------------------------------------------------------------------
    # [ISSUE 01] แสดงเฉพาะ 4 องค์ประกอบ + น้ำหนักที่ใช้คำนวณ health_score จริง
    # (น้ำหนักอ่านจาก HEALTH_WEIGHTS ใน calculate_modules/company_health.py ไม่เขียนตัวเลขซ้ำในไฟล์นี้)
    # ------------------------------------------------------------------
    # [ISSUE 03] เพดาน D/E ที่ใช้จริงกับหุ้นตัวนี้ (คำนวณตาม sector มาจากฝั่งคำนวณแล้ว -- ที่นี่แค่แสดงผลให้โปร่งใส)
    _de_thr = num_or_none(ctx.stock_info.get('de_threshold_used'))
    _de_thr_txt = f" · D/E Cap ({ctx.stock_info.get('sector','-')}): {_de_thr:.1f}x" if _de_thr is not None else ""
    st.markdown(f"""<div style="font-size:15px; font-weight:bold; color:#F8FAFC; letter-spacing:0.5px; margin-bottom:8px;">
    SCORE COMPONENTS <span style="font-size:14.5px; color:#94A3B8; font-weight:normal; margin-left:6px;">องค์ประกอบและน้ำหนักที่ใช้คำนวณคะแนนรวมจริง (คำนวณจากอัตราส่วนจริง){_de_thr_txt}</span></div>""", unsafe_allow_html=True)

    # ใช้ในส่วน WATCH OUT ด้านล่าง (ไม่เกี่ยวกับคะแนนรวม)
    rev_growth = safe(ctx.stock_info.get('revenue_growth_yoy'), 0.0)

    def comp_score(key):
        """คืนคะแนน int 0-100 หรือ None ถ้าไม่มีค่า (ไม่ใส่ค่า default สมมติ)"""
        v = ctx.stock_info.get(key)
        try:
            v = float(v)
        except (TypeError, ValueError):
            return None
        return None if np.isnan(v) else int(round(v))

    def label_for(score):
        if score is None: return "N/A"
        if score >= 75: return "EXCELLENT"
        if score >= 55: return "GOOD"
        if score >= 35: return "MODERATE"
        return "WEAK"

    def pct(key):
        return f"{int(round(HEALTH_WEIGHTS[key] * 100))}%"

    dims = [
        ("1", "📊", "ROE", pct('roe'), comp_score('s_roe'), "#10B981"),
        ("2", "📈", "ROA", pct('roa'), comp_score('s_roa'), "#3B82F6"),
        ("3", "💧", "LIQUIDITY", pct('liquidity'), comp_score('s_liquidity'), "#06B6D4"),
        ("4", "🛡️", "DEBT (D/E)", pct('debt'), comp_score('s_debt'), "#EAB308"),
    ]
    dim_html = "".join([f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:10px; padding:10px 8px; text-align:center;">
    <div style="display:flex; align-items:center; justify-content:center; gap:4px;"><span style="font-size:14.5px;">{icon}</span><span style="font-size:13px; font-weight:bold; color:#CBD5E1;">{n}. {label}</span></div>
    <div style="font-size:12.5px; color:#64748B; margin-top:1px;">Weight {w}</div>
    <div style="margin:8px auto; width:60px; height:60px; border-radius:50%; background:conic-gradient({color} 0% {score or 0}%, #1E293B {score or 0}% 100%); display:flex; align-items:center; justify-content:center;">
    <div style="width:48px; height:48px; border-radius:50%; background-color:#0F172A; display:flex; flex-direction:column; align-items:center; justify-content:center;">
    <span style="font-size:16px; font-weight:bold; color:#FFFFFF; line-height:1;">{'N/A' if score is None else score}</span><span style="font-size:11.5px; color:#64748B;">{'' if score is None else '/100'}</span></div></div>
    <div style="color:{color if score is not None else '#64748B'}; font-size:13.5px; font-weight:bold;">{label_for(score)}</div>
    </div>""" for n, icon, label, w, score, color in dims])
    st.markdown(f"""<div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:8px;">{dim_html}</div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:22px;'></div>", unsafe_allow_html=True)
    r3_c1, r3_c2, r3_c3 = st.columns([1.5, 1.25, 1.25])

    with r3_c1:
        st.markdown(f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px; padding:14px; min-height:360px; display:flex; flex-direction:column; justify-content:space-between;">
    <div><div style="font-size:14.5px; font-weight:bold; color:#94A3B8; letter-spacing:0.5px; margin-bottom:8px;">KEY FINANCIAL HIGHLIGHTS ({ctx.selected_ticker})</div>
    <table style="width:100%; text-align:left; font-size:14px; color:#CBD5E1; border-collapse:collapse;">
    <tr style="border-bottom:1px solid #1E293B; color:#64748B; font-size:13px;"><th style="padding:4px 0;">Metric</th><th>2023</th><th>2024</th><th>2025</th></tr>
    <tr style="border-bottom:1px solid #1E293B;"><td style="padding:5px 0; font-weight:bold; color:#F8FAFC;">ROE (%)</td><td>{roe_23}</td><td>{roe_24}</td><td style="font-weight:bold; color:#F8FAFC;">{roe_25}</td></tr>
    <tr style="border-bottom:1px solid #1E293B;"><td style="padding:5px 0; font-weight:bold; color:#F8FAFC;">ROA (%)</td><td>{roa_23}</td><td>{roa_24}</td><td style="font-weight:bold; color:#F8FAFC;">{roa_25}</td></tr>
    <tr style="border-bottom:1px solid #1E293B;"><td style="padding:5px 0; font-weight:bold; color:#F8FAFC;">Net Profit Margin (%)</td><td>{npm_23}</td><td>{npm_24}</td><td style="font-weight:bold; color:#F8FAFC;">{npm_25}</td></tr>
    <tr style="border-bottom:1px solid #1E293B;"><td style="padding:5px 0; font-weight:bold; color:#F8FAFC;">Debt to Equity (x)</td><td>{de_23}</td><td>{de_24}</td><td style="font-weight:bold; color:#F8FAFC;">{de_25}</td></tr>
    <tr><td style="padding:5px 0; font-weight:bold; color:#F8FAFC;">Current Ratio (x)</td><td>{cr_23}</td><td>{cr_24}</td><td style="font-weight:bold; color:#F8FAFC;">{cr_25}</td></tr>
    </table></div>
    <div style="font-size:12px; color:#64748B; margin-top:6px;">* ข้อมูลทางการเงินดึงตรงจาก stock_financials.csv สำหรับปี 2023-2025 จริงทุกค่า</div>
    </div>""", unsafe_allow_html=True)

    with r3_c2:
        strengths, watch = [], []
        # [ISSUE 02] ค่าที่ขาดเป็น None และข้ามเงื่อนไขนั้นไป (เดิมแทนด้วย 0 ทำให้ D/E ขาดกลายเป็น "หนี้ต่ำ = จุดแข็ง")
        n_roe, n_cr, n_npm, n_de = num_or_none(roe_25), num_or_none(cr_25), num_or_none(npm_25), num_or_none(de_25)
        any_missing = any(v is None for v in (n_roe, n_cr, n_npm, n_de))
        if n_roe is not None and n_roe > 15: strengths.append(f"ROE ล่าสุดอยู่ในเกณฑ์ดีที่ {roe_25}%")
        if n_cr is not None and n_cr >= 1.0: strengths.append(f"สภาพคล่อง Current Ratio อยู่ที่ {cr_25} เท่า เพียงพอต่อภาระหนี้ระยะสั้น")
        if n_npm is not None and n_npm > 10: strengths.append(f"Net Margin ระดับ {npm_25}% สะท้อนความสามารถทำกำไรที่ดี")
        if n_de is not None and n_de < 1.5: strengths.append(f"โครงสร้างเงินทุนมี D/E เพียง {de_25} เท่า ความเสี่ยงหนี้สินต่ำ")
        if not strengths:
            strengths.append("ข้อมูลไม่เพียงพอสำหรับประเมินจุดแข็ง" if any_missing else "ผลประกอบการโดยรวมยังอยู่ระหว่างการฟื้นตัว")
        if n_de is not None and n_de > 1.5: watch.append(f"ภาระหนี้สินต่อทุนค่อนข้างสูงที่ {de_25} เท่า ควรติดตามใกล้ชิด")
        if n_cr is not None and n_cr < 1.0: watch.append(f"Current Ratio ต่ำกว่า 1 เท่า ({cr_25}) สภาพคล่องระยะสั้นควรเฝ้าระวัง")
        if rev_growth < 0: watch.append(f"รายได้หดตัว {rev_growth:.1f}% YoY ควรติดตามแนวโน้มปีถัดไป")
        if any_missing: watch.append("ข้อมูลงบล่าสุดบางรายการไม่ครบ (แสดงเป็น N/A) จึงประเมินความเสี่ยงได้ไม่ครบถ้วน")
        elif not watch: watch.append("ยังไม่พบสัญญาณความเสี่ยงเชิงโครงสร้างที่ชัดเจนในงบล่าสุด")

        st.markdown(f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px; padding:14px; height:360px; overflow-y:auto;">
    <div style="font-size:14px; font-weight:bold; color:#10B981; margin-bottom:6px;">STRENGTHS ({ctx.selected_ticker})</div>
    <div style="font-size:13px; color:#CBD5E1; line-height:1.45; margin-bottom:10px;">
    {''.join([f'<div style="display:flex; gap:6px; margin-bottom:3px;"><span style="color:#10B981;">✔</span><span>{s}</span></div>' for s in strengths])}
    </div>
    <div style="font-size:14px; font-weight:bold; color:#F59E0B; margin-bottom:6px; border-top:1px dashed #1E293B; padding-top:8px;">WATCH OUT</div>
    <div style="font-size:13px; color:#CBD5E1; line-height:1.45;">
    {''.join([f'<div style="display:flex; gap:6px; margin-bottom:3px;"><span style="color:#F59E0B;">⚠️</span><span>{w}</span></div>' for w in watch])}
    </div></div>""", unsafe_allow_html=True)

    with r3_c3:
        # ค่าเฉลี่ยอุตสาหกรรม (sector) จากข้อมูลจริงของปีล่าสุดที่มี ในกลุ่มเดียวกัน
        sector_fin = ctx.fin_df[(ctx.fin_df['ticker'].isin(ctx.sector_peers['ticker'])) & (ctx.fin_df['year'] == ctx.fin_stock['year'].max())]
        ind_roe = sector_fin['roe'].mean() if not sector_fin.empty else safe(roe_25 if roe_25 != '-' else 0)
        ind_roa = sector_fin['roa'].mean() if not sector_fin.empty else safe(roa_25 if roa_25 != '-' else 0)
        ind_npm = sector_fin['net_margin'].mean() if not sector_fin.empty else safe(npm_25 if npm_25 != '-' else 0)
        ind_de = sector_fin['de_ratio'].mean() if not sector_fin.empty else safe(de_25 if de_25 != '-' else 0)
        ind_cr = sector_fin['current_ratio'].mean() if not sector_fin.empty else safe(cr_25 if cr_25 != '-' else 0)

        def pct_bar(stock_val, ind_val, higher_better=True):
            if ind_val == 0: return 50
            ratio = (stock_val / ind_val) if higher_better else (ind_val / max(stock_val, 0.01))
            return int(np.clip(ratio * 50, 5, 100))

        rows_cmp = [
            ("ROE (%)", roe_25, f"{ind_roe:.1f}", pct_bar(safe(roe_25 if roe_25 != '-' else 0), ind_roe)),
            ("ROA (%)", roa_25, f"{ind_roa:.1f}", pct_bar(safe(roa_25 if roa_25 != '-' else 0), ind_roa)),
            ("Net Margin (%)", npm_25, f"{ind_npm:.1f}", pct_bar(safe(npm_25 if npm_25 != '-' else 0), ind_npm)),
            ("Debt to Equity (x)", de_25, f"{ind_de:.2f}", pct_bar(safe(de_25 if de_25 != '-' else 0), ind_de, higher_better=False)),
            ("Current Ratio (x)", cr_25, f"{ind_cr:.2f}", pct_bar(safe(cr_25 if cr_25 != '-' else 0), ind_cr)),
        ]
        rows_html = "".join([f"""<tr style="border-bottom:1px solid #1E293B;">
    <td style="padding:4px 0;">{name}</td><td style="font-weight:bold; color:#F8FAFC;">{v}</td><td style="color:#64748B;">{avg}</td>
    <td><div style="display:flex; align-items:center; gap:6px;"><div style="background:#1E293B; width:60px; height:9px; border-radius:4px; overflow:hidden;"><div style="background:#10B981; width:{pct}%; height:100%;"></div></div><span style="font-size:12px; color:#10B981; font-weight:bold;">{pct}%</span></div></td>
    </tr>""" for name, v, avg, pct in rows_cmp])

        st.markdown(f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px; padding:14px; height:360px;">
    <div style="font-size:14.5px; font-weight:bold; color:#94A3B8; letter-spacing:0.5px;">INDUSTRY COMPARISON</div>
    <div style="font-size:12.5px; color:#64748B; margin-bottom:8px;">เทียบกับค่าเฉลี่ยจริงของกลุ่ม ({ctx.stock_info.get('sector','-')}, ปีล่าสุด)</div>
    <table style="width:100%; text-align:left; font-size:13.5px; color:#CBD5E1; border-collapse:collapse;">
    <tr style="border-bottom:1px solid #1E293B; color:#64748B; font-size:12.5px;"><th style="padding:3px 0;">Metric</th><th>{ctx.selected_ticker}</th><th>Sector Avg</th><th>vs Avg</th></tr>
    {rows_html}
    </table></div>""", unsafe_allow_html=True)

    render_nav_footer("m1", prev_page=" 🏠 Overview", next_page=" ⚖️ Fair Value")
