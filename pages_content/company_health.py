"""
pages_content/company_health.py
---------------------------
หน้า "Company Health" ของ CIS Dashboard
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from common import fmt_mb, safe, show_chart, render_nav_footer, COMPANY_NAMES, SECTOR_MAP

def render(ctx):
    # ป้องกันการหยุดชะงักเมื่อไม่มีข้อมูล
    h_score_raw = ctx.stock_info.get('health_score', "N/A")
    data_complete = ctx.stock_info.get('health_data_complete', True)
    missing_fields = ctx.stock_info.get('health_missing_fields', '')

    st.markdown("""<div style="display:flex; justify-content:space-between; align-items:flex-end; margin-bottom:15px;">
    <div><div style="display:flex; align-items:center; gap:8px;"><h2 style="margin:0; font-size:23px; font-weight:bold; color:#F8FAFC; letter-spacing:0.5px;">COMPANY HEALTH</h2></div>
    <div style="font-size:15px; color:#94A3B8; margin-top:2px;">ประเมินสุขภาพทางการเงินของบริษัทจากมิติสำคัญตามงบการเงินจริง</div></div>
    </div>""", unsafe_allow_html=True)

    # ----------------------------------------------------
    # ส่วนแจ้งเตือนกรณีข้อมูลขาดหาย
    # ----------------------------------------------------
    if not data_complete or h_score_raw == "N/A":
        st.markdown(f"""
        <div style="background-color:rgba(239, 68, 68, 0.1); border-left:4px solid #EF4444; padding:16px; border-radius:4px; margin-bottom:20px;">
            <span style="color:#EF4444; font-size:16px; font-weight:bold;">⚠️ Data Incomplete (ข้อมูลไม่สมบูรณ์)</span>
            <p style="color:#CBD5E1; margin:4px 0 0 0; font-size:14px;">
                ระบบไม่สามารถประเมิน Company Health Score ได้เนื่องจากขาดข้อมูล: <b>{missing_fields}</b> ของปีล่าสุด
            </p>
        </div>
        """, unsafe_allow_html=True)
        return  # หยุดเรนเดอร์เนื้อหาส่วนที่เหลือของหน้านี้ทันที

    # ----------------------------------------------------
    # การ์ดหลัก Company Health Score
    # ----------------------------------------------------
    h_score = int(round(float(h_score_raw)))
    h_badge = "EXCELLENT" if h_score >= 75 else ("MODERATE" if h_score >= 50 else "WEAK")
    h_color = "#10B981" if h_score >= 75 else ("#F59E0B" if h_score >= 50 else "#EF4444")
    h_stars = min(5, max(1, round(h_score / 20)))

    r1_c1, r1_c2, r1_c3 = st.columns([1.1, 1.4, 1.5])

    with r1_c1:
        st.markdown(f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px; padding:16px; min-height:235px; display:flex; flex-direction:column; justify-content:space-between;">
    <div style="font-size:14.5px; font-weight:bold; color:#94A3B8; letter-spacing:0.5px;">COMPANY HEALTH SCORE</div>
    <div style="display:flex; align-items:center; gap:16px; margin:auto 0;">
    <div style="width:92px; height:92px; border-radius:50%; background:conic-gradient({h_color} 0% {h_score}%, #1E293B {h_score}% 100%); display:flex; align-items:center; justify-content:center; flex-shrink:0;">
    <div style="width:76px; height:76px; border-radius:50%; background-color:#0F172A; display:flex; flex-direction:column; align-items:center; justify-content:center;">
    <span style="font-size:23px; font-weight:bold; color:#FFFFFF; line-height:1;">{h_score}</span><span style="font-size:13px; color:#64748B;">/100</span></div></div>
    <div><div style="color:{h_color}; font-size:18.5px; font-weight:bold; line-height:1.2;">{h_badge}</div>
    <div style="font-size:14.5px; color:#CBD5E1; line-height:1.4; margin-top:4px;">ประเมินจากอัตราส่วนทางการเงินจริง</div>
    <div style="color:{h_color}; font-size:15px; letter-spacing:2px; margin-top:6px;">{'★'*h_stars}{'☆'*(5-h_stars)}</div></div>
    </div></div>""", unsafe_allow_html=True)

    with r1_c2:
        roe = ctx.stock_info.get('roe', '-')
        npm = safe(ctx.fin_stock.iloc[-1].get('net_margin'), 0.0) if not ctx.fin_stock.empty else '-'
        de = ctx.stock_info.get('de_ratio', '-')
        cr = ctx.stock_info.get('current_ratio', '-')

        st.markdown(f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px; padding:16px; min-height:235px; display:flex; flex-direction:column; justify-content:space-between;">
    <div><div style="font-size:14.5px; font-weight:bold; color:#94A3B8; letter-spacing:0.5px; margin-bottom:8px;">EXPLAINABLE FINANCIAL SUMMARY ({ctx.selected_ticker})</div>
    <p style="font-size:15px; color:#CBD5E1; line-height:1.6; margin:0;">
    ผลการวิเคราะห์สุขภาพการเงินของ <b>{ctx.selected_ticker}</b> พบว่ามีอัตราส่วนผลตอบแทนต่อส่วนของผู้ถือหุ้น (ROE) ล่าสุดอยู่ที่ {roe}% และความสามารถในการทำกำไรสุทธิ (Net Margin) อยู่ที่ {npm}% ในขณะที่ภาระหนี้สินต่อทุน (D/E Ratio) อยู่ที่ {de} เท่า และสภาพคล่องหมุนเวียน (Current Ratio) อยู่ที่ {cr} เท่า
    </p></div>
    <div><span style="display:inline-flex; align-items:center; gap:6px; background-color:#151E2F; border:1px solid #1E293B; color:#38BDF8; font-size:14px; padding:5px 12px; border-radius:6px;">
    Financial Health Benchmark: {ctx.stock_info.get('sector','-')}</span></div>
    </div>""", unsafe_allow_html=True)

    with r1_c3:
        st.markdown("""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px 12px 0 0; padding:12px 16px 0 16px;">
    <div style="font-size:14.5px; font-weight:bold; color:#94A3B8; letter-spacing:0.5px;">COMPANY HEALTH SCORE TREND</div></div>""", unsafe_allow_html=True)

        hy = ctx.health_yearly_df[ctx.health_yearly_df['ticker'] == ctx.selected_ticker].sort_values('year') if not ctx.health_yearly_df.empty else pd.DataFrame()
        trend_x = hy['year'].astype(str).tolist() if not hy.empty else ['2023', '2024', '2025']
        trend_y = hy['health_score'].tolist() if not hy.empty else [h_score, h_score, h_score]

        fig_health_trend = go.Figure()
        fig_health_trend.add_trace(go.Scatter(
            x=trend_x, y=trend_y, mode='lines+markers+text', text=trend_y, textposition='top center',
            textfont=dict(size=12.5, color='#F8FAFC'), line=dict(color='#10B981', width=2),
            marker=dict(size=10, color='#10B981', line=dict(width=1.5, color='#FFFFFF'))
        ))
        
        # กราฟจะวาดตามคะแนนดิบ 0-100 ไม่ติดแคปที่ 25 หรือ 98 แล้ว
        fig_health_trend.update_layout(
            height=168, margin=dict(l=25, r=15, t=10, b=20), paper_bgcolor="#0F172A", plot_bgcolor="#0F172A",
            yaxis=dict(range=[0, 110], tickvals=[0, 25, 50, 75, 100], tickfont=dict(size=11.5, color="#64748B"), gridcolor="#1E293B", zeroline=False),
            xaxis=dict(tickfont=dict(size=12, color="#94A3B8"), gridcolor="#1E293B"), showlegend=False
        )
        show_chart(fig_health_trend, key="health_trend", expand_height=650)

    # ----------------------------------------------------
    # Issue 01: 4 DIMENSIONS OVERVIEW (ลบ 7 มิติสมมติทิ้ง)
    # ----------------------------------------------------
    st.markdown("<div style='margin-top:22px;'></div>", unsafe_allow_html=True)
    st.markdown("""<div style="font-size:15px; font-weight:bold; color:#F8FAFC; letter-spacing:0.5px; margin-bottom:8px;">
    CORE FINANCIAL DIMENSIONS <span style="font-size:14.5px; color:#94A3B8; font-weight:normal; margin-left:6px;">น้ำหนัก 4 องค์ประกอบหลักที่ใช้คำนวณ Health Score</span></div>""", unsafe_allow_html=True)

    def label_for(score):
        if score >= 75: return "EXCELLENT"
        if score >= 55: return "GOOD"
        if score >= 35: return "MODERATE"
        return "WEAK"

    dims = [
        ("1", "📊", "ROE SCORE", ctx.stock_info.get('dim_roe_weight', '30%'), int(ctx.stock_info.get('dim_roe_score', 0)), "#10B981"),
        ("2", "⚙️", "ROA SCORE", ctx.stock_info.get('dim_roa_weight', '25%'), int(ctx.stock_info.get('dim_roa_score', 0)), "#3B82F6"),
        ("3", "💧", "LIQUIDITY (Current Ratio)", ctx.stock_info.get('dim_liquidity_weight', '20%'), int(ctx.stock_info.get('dim_liquidity_score', 0)), "#06B6D4"),
        ("4", "🛡️", "FIN. STABILITY (D/E)", ctx.stock_info.get('dim_debt_weight', '25%'), int(ctx.stock_info.get('dim_debt_score', 0)), "#EAB308"),
    ]
    
    # ปรับเป็น Grid 4 คอลัมน์ให้รับกับ 4 องค์ประกอบ
    dim_html = "".join([f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:10px; padding:12px 10px; text-align:center;">
    <div style="display:flex; align-items:center; justify-content:center; gap:6px;"><span style="font-size:16px;">{icon}</span><span style="font-size:14px; font-weight:bold; color:#CBD5E1;">{label}</span></div>
    <div style="font-size:13px; color:#64748B; margin-top:2px;">Weight {w}</div>
    <div style="margin:12px auto; width:70px; height:70px; border-radius:50%; background:conic-gradient({color} 0% {score}%, #1E293B {score}% 100%); display:flex; align-items:center; justify-content:center;">
    <div style="width:56px; height:56px; border-radius:50%; background-color:#0F172A; display:flex; flex-direction:column; align-items:center; justify-content:center;">
    <span style="font-size:18px; font-weight:bold; color:#FFFFFF; line-height:1;">{score}</span><span style="font-size:12px; color:#64748B;">/100</span></div></div>
    <div style="color:{color}; font-size:14.5px; font-weight:bold;">{label_for(score)}</div>
    </div>""" for _, icon, label, w, score, color in dims])
    
    st.markdown(f"""<div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:12px;">{dim_html}</div>""", unsafe_allow_html=True)
    
    render_nav_footer("m1", prev_page=" 🏠 Overview", next_page=" ⚖️ Fair Value")
