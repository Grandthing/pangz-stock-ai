import streamlit as st

# ตั้งค่าหน้าเว็บ
st.set_page_config(
    page_title="PANGZ Intelligence Platform",
    page_icon="🤖",
    layout="wide",
)

# หัวข้อหลัก
st.title("🤖 PANGZ Intelligence Platform")
st.markdown("AI-powered stock analysis — runs 100% locally, zero cost")

# Sidebar เมนู
st.sidebar.title("📌 เมนู")
page = st.sidebar.radio(
    "เลือกฟีเจอร์:",
    ["🏠 หน้าแรก", "📊 วิเคราะห์หุ้น", "🏆 Batch Ranking", "📈 Technical Chart", "🔄 DCA Backtest", "🎯 Position Sizer", "📰 TA Analysis"]
)

# หน้าแรก
if page == "🏠 หน้าแรก":
    st.header("ยินดีต้อนรับ!")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("ฟีเจอร์ทั้งหมด", "6 อย่าง")
    with col2:
        st.metric("ค่าใช้จ่าย", "$0/เดือน")
    with col3:
        st.metric("AI Model", "Qwen 2.5:14b")

    st.markdown("---")
    st.markdown("""
    ### ✨ สิ่งที่ระบบทำได้
    - **วิเคราะห์พื้นฐาน** — งบการเงิน 4 ปี + Reverse DCF + Scoring
    - **Technical Analysis** — กราฟราคา + SMA 50/200 + Buy Signals
    - **DCA Backtest** — จำลอง DCA ย้อนหลัง + เปรียบเทียบ Lump Sum
    - **AI Report** — รายงานวิเคราะห์จาก Local LLM ภาษาไทย
    """)
elif page == "📊 วิเคราะห์หุ้น":
    st.header("📊 วิเคราะห์หุ้น")

    # ช่องพิมพ์ชื่อหุ้น
    symbol = st.text_input("พิมพ์ชื่อหุ้น (เช่น MSFT, NVDA)", value="MSFT").upper().strip()

    # ปุ่มเริ่มวิเคราะห์
    if st.button("🔍 เริ่มวิเคราะห์", type="primary"):

        if not symbol:
            st.error("กรุณาพิมพ์ชื่อหุ้น")
        else:
            try:
                from main import fetch_stock_data, fetch_financials, reverse_dcf, score_stock

                # แสดง Progress
                progress = st.progress(0, text="กำลังดึงข้อมูล...")

                # ขั้น 1: ข้อมูลพื้นฐาน
                progress.progress(20, text=f"ดึงข้อมูล {symbol}...")
                stock_data, ticker, info = fetch_stock_data(symbol)

                # ขั้น 2: งบการเงิน
                progress.progress(40, text="ดึงงบการเงิน...")
                metrics = fetch_financials(ticker)

                # ขั้น 3: Reverse DCF
                progress.progress(60, text="คำนวณ Reverse DCF...")
                dcf_result = reverse_dcf(info, metrics)

                # ขั้น 4: Scoring
                progress.progress(80, text="ให้คะแนน...")
                scores = score_stock(info, dcf_result)
                total = sum(s["score"] for s in scores.values())

                progress.progress(100, text="เสร็จสมบูรณ์!")

                # === แสดงผลลัพธ์ ===
                st.markdown("---")

                # ข้อมูลบริษัท
                st.subheader(f"{stock_data['ชื่อบริษัท']} ({symbol})")

                # Metrics แถวบน
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("ราคา", f"${stock_data['ราคาปัจจุบัน']}")
                with col2:
                    st.metric("Score", f"{total}/100")
                with col3:
                    pe = info.get("trailingPE")
                    st.metric("P/E Ratio", f"{pe:.1f}" if pe else "N/A")
                with col4:
                    growth = info.get("revenueGrowth")
                    st.metric("Revenue Growth", f"{growth:.1%}" if growth else "N/A")

                # Metrics แถวล่าง
                col5, col6, col7, col8 = st.columns(4)
                with col5:
                    margin = info.get("profitMargins")
                    st.metric("Profit Margin", f"{margin:.1%}" if margin else "N/A")
                with col6:
                    de = info.get("debtToEquity")
                    st.metric("Debt/Equity", f"{de:.1f}%" if de else "N/A")
                with col7:
                    if "error" not in dcf_result:
                        st.metric("Implied Growth", f"{dcf_result['implied_growth']:.0%}")
                    else:
                        st.metric("Implied Growth", "N/A")
                with col8:
                    mcap = stock_data.get("Market Cap (B$)", 0)
                    st.metric("Market Cap", f"${mcap}B")
                # แถว Earnings
                col_e1, col_e2, col_e3, col_e4 = st.columns(4)
                with col_e1:
                    st.metric("Earnings ถัดไป", stock_data.get("Earnings Date (Next)", "N/A"))
                with col_e2:
                    st.metric("Earnings ล่าสุด", stock_data.get("Last Earnings", "N/A"))
                with col_e3:
                    eps_a = stock_data.get("EPS Actual")
                    st.metric("EPS Actual", f"${eps_a:.2f}" if eps_a else "N/A")
                with col_e4:
                    surprise = stock_data.get("EPS Surprise", "N/A")
                    st.metric("EPS Surprise", surprise)

                st.markdown("---")

                # คะแนนรายเกณฑ์
                st.subheader("📋 Stock Score")

                for criteria, result in scores.items():
                    col_name, col_bar, col_reason = st.columns([2, 3, 5])
                    with col_name:
                        st.write(f"**{criteria}**")
                    with col_bar:
                        st.progress(result["score"] / 20)
                    with col_reason:
                        st.write(result["reason"])

                # คำตัดสิน
                st.markdown("---")
                if total >= 80:
                    st.success(f"🟢 Score {total}/100 — น่าสนใจมาก พิจารณาซื้อ")
                elif total >= 60:
                    st.warning(f"🟡 Score {total}/100 — พอใช้ได้ ถือต่อหรือรอจังหวะ")
                elif total >= 40:
                    st.warning(f"🟠 Score {total}/100 — ระวัง มีจุดอ่อนหลายด้าน")
                else:
                    st.error(f"🔴 Score {total}/100 — ไม่น่าสนใจ หาตัวอื่น")
# === งบการเงิน 4 ปี ===
                st.markdown("---")
                st.subheader("📑 งบการเงิน 4 ปีย้อนหลัง")

                def fmt_b(value):
                    if value is None:
                        return "N/A"
                    return f"${value / 1e9:.2f}B"

                fin_rows = []
                for d in metrics:
                    fin_rows.append({
                        "ปี": d["year"],
                        "Revenue": fmt_b(d["revenue"]),
                        "Net Income": fmt_b(d["net_income"]),
                        "EBITDA": fmt_b(d["ebitda"]),
                        "Total Debt": fmt_b(d["total_debt"]),
                        "Free CF": fmt_b(d["free_cashflow"]),
                    })

                import pandas as pd
                df_fin = pd.DataFrame(fin_rows)
                st.dataframe(df_fin, use_container_width=True, hide_index=True)

                # === Reverse DCF ===
                st.markdown("---")
                st.subheader("🧮 Reverse DCF")

                if "error" not in dcf_result:
                    col_dcf1, col_dcf2, col_dcf3 = st.columns(3)
                    with col_dcf1:
                        st.metric("Market Cap", f"${dcf_result['market_cap_B']:,.2f}B")
                    with col_dcf2:
                        st.metric("Free Cash Flow", f"${dcf_result['latest_fcf_B']:,.2f}B")
                    with col_dcf3:
                        implied = dcf_result["implied_growth"]
                        st.metric("Implied Growth", f"{implied:.0%}")

                    if implied > 0.25:
                        st.warning(f"⚠️ ตลาดคาดหวัง Growth {implied:.0%}/ปี → สูงมาก ระวังผิดหวัง")
                    elif implied > 0.15:
                        st.info(f"💡 ตลาดคาดหวัง Growth {implied:.0%}/ปี → สูงพอสมควร")
                    elif implied > 0.08:
                        st.success(f"✅ ตลาดคาดหวัง Growth {implied:.0%}/ปี → สมเหตุสมผล")
                    else:
                        st.success(f"🟢 ตลาดคาดหวัง Growth {implied:.0%}/ปี → ต่ำ อาจเป็นโอกาสซื้อ")
                else:
                    st.warning(f"⚠️ {dcf_result['error']}")

                # === AI Report ===
                st.markdown("---")
                st.subheader("🤖 AI Analysis Report")

                with st.spinner("AI กำลังเขียนรายงาน... (30-60 วินาที)"):
                    from main import generate_report
                    ai_report = generate_report(symbol, stock_data, metrics, dcf_result, scores)

                st.markdown(ai_report)
                

            except Exception as e:
                st.error(f"❌ เกิดข้อผิดพลาด: {e}")
elif page == "🏆 Batch Ranking":
    st.header("🏆 Batch Analysis & Ranking")

    symbols_input = st.text_input(
        "พิมพ์ชื่อหุ้น คั่นด้วยช่องว่าง",
        value="MSFT NVDA META SOFI AMKR"
    ).upper().strip()

    if st.button("🏆 วิเคราะห์ทั้งหมด", type="primary"):

        symbols = symbols_input.split()

        if len(symbols) == 0:
            st.error("กรุณาพิมพ์ชื่อหุ้นอย่างน้อย 1 ตัว")
        else:
            from main import fetch_stock_data, fetch_financials, reverse_dcf, score_stock
            import pandas as pd

            results = []
            progress = st.progress(0, text="เริ่มวิเคราะห์...")

            for i, symbol in enumerate(symbols):
                try:
                    pct = int((i / len(symbols)) * 100)
                    progress.progress(pct, text=f"กำลังวิเคราะห์ {symbol}... ({i+1}/{len(symbols)})")

                    stock_data, ticker, info = fetch_stock_data(symbol)
                    metrics = fetch_financials(ticker)
                    dcf = reverse_dcf(info, metrics)
                    scores = score_stock(info, dcf)
                    total = sum(s["score"] for s in scores.values())

                    results.append({
                        "symbol": symbol,
                        "name": stock_data["ชื่อบริษัท"],
                        "price": stock_data["ราคาปัจจุบัน"],
                        "pe": info.get("trailingPE"),
                        "growth": info.get("revenueGrowth"),
                        "margin": info.get("profitMargins"),
                        "de": info.get("debtToEquity"),
                        "implied": dcf.get("implied_growth"),
                        "scores": scores,
                        "total_score": total,
                    })

                except Exception as e:
                    st.warning(f"⚠️ {symbol}: {e}")

            progress.progress(100, text="เสร็จสมบูรณ์!")

            # เรียงอันดับ
            results.sort(key=lambda x: x["total_score"], reverse=True)

            st.markdown("---")

            # === ตารางอันดับ ===
            st.subheader("📊 อันดับรวม")

            rows = []
            for i, r in enumerate(results, 1):
                pe_str = f"{r['pe']:.1f}" if r['pe'] else "N/A"
                growth_str = f"{r['growth']:.1%}" if r['growth'] else "N/A"
                margin_str = f"{r['margin']:.1%}" if r['margin'] else "N/A"
                de_str = f"{r['de']:.1f}%" if r['de'] else "N/A"
                implied_str = f"{r['implied']:.0%}" if r['implied'] is not None else "N/A"

                rows.append({
                    "อันดับ": f"#{i}",
                    "Ticker": r["symbol"],
                    "ชื่อบริษัท": r["name"],
                    "ราคา": f"${r['price']}",
                    "Score": f"{r['total_score']}/100",
                    "P/E": pe_str,
                    "Growth": growth_str,
                    "Margin": margin_str,
                    "D/E": de_str,
                    "Implied": implied_str,
                })

            df_rank = pd.DataFrame(rows)
            st.dataframe(df_rank, use_container_width=True, hide_index=True)

            # === คะแนนรายเกณฑ์ ===
            st.markdown("---")
            st.subheader("📋 คะแนนรายเกณฑ์")

            score_rows = []
            for r in results:
                row = {"Ticker": r["symbol"], "Total": r["total_score"]}
                for criteria, result in r["scores"].items():
                    row[criteria] = f"{result['score']}/20"
                score_rows.append(row)

            df_scores = pd.DataFrame(score_rows)
            st.dataframe(df_scores, use_container_width=True, hide_index=True)

            # === สรุปสถิติ ===
            st.markdown("---")
            st.subheader("📈 Quick Stats")

            df_stats = pd.DataFrame([{
                "symbol": r["symbol"],
                "score": r["total_score"],
                "pe": r["pe"],
                "growth": r["growth"],
            } for r in results])

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("หุ้นทั้งหมด", f"{len(results)} ตัว")
            with col2:
                st.metric("Score เฉลี่ย", f"{df_stats['score'].mean():.1f}")
            with col3:
                good = len(df_stats[df_stats["score"] >= 70])
                st.metric("น่าสนใจ (≥70)", f"{good} ตัว")
            with col4:
                best = results[0]
                st.metric("🏆 Top Pick", f"{best['symbol']} ({best['total_score']})")

            # === แสดงเหตุผลคะแนนแต่ละตัว ===
            st.markdown("---")
            st.subheader("🔍 รายละเอียดแต่ละตัว")

            for r in results:
                score = r["total_score"]
                if score >= 80:
                    icon = "🟢"
                elif score >= 60:
                    icon = "🟡"
                else:
                    icon = "🔴"

                with st.expander(f"{icon} {r['symbol']} — {r['name']} ({score}/100)"):
                    for criteria, result in r["scores"].items():
                        col_name, col_bar, col_reason = st.columns([2, 3, 5])
                        with col_name:
                            st.write(f"**{criteria}**")
                        with col_bar:
                            st.progress(result["score"] / 20)
                        with col_reason:
                            st.write(result["reason"])

            # === AI Recommendation ===
            st.markdown("---")
            st.subheader("🤖 AI Portfolio Recommendation")

            with st.spinner("AI กำลังวิเคราะห์ Portfolio... (30-60 วินาที)"):
                import ollama

                summary = ""
                for i, r in enumerate(results, 1):
                    summary += f"#{i} {r['symbol']} ({r['name']})\n"
                    summary += f"   Score: {r['total_score']}/100\n"
                    summary += f"   Price: ${r['price']}, P/E: {r['pe']}\n"
                    summary += f"   Growth: {r['growth']}, Margin: {r['margin']}\n\n"

                prompt = f"""คุณเป็นนักวิเคราะห์หุ้นแนว Value Investing
ตอบเป็นภาษาไทย ห้ามใช้ภาษาอื่นนอกจากไทยและอังกฤษ
กระชับ ตรงประเด็น ใช้ข้อมูลจริงเท่านั้น

ข้อมูลหุ้นเรียงตามคะแนน:
{summary}

กรุณาเขียน Portfolio Recommendation:
1. Top Pick: ตัวไหนน่าสนใจที่สุด พร้อมเหตุผล 2 ข้อ
2. ตัวที่ควรรอ: ราคาเท่าไหร่ถึงน่าซื้อ
3. ตัวที่ควรระวัง: ตัวไหนมีความเสี่ยงสูงสุด
4. แผน DCA: ถ้ามีเงิน 100,000 บาท ควรแบ่งลงทุนยังไง
"""

                response = ollama.chat(
                    model="qwen2.5:14b",
                    messages=[{"role": "user", "content": prompt}]
                )

                st.markdown(response["message"]["content"])
elif page == "📈 Technical Chart":
    st.header("📈 Technical Analysis")

    # ช่องพิมพ์หุ้น
    symbols_input = st.text_input(
        "พิมพ์ชื่อหุ้น คั่นด้วยช่องว่าง (เช่น MSFT NVDA META)",
        value="MSFT NVDA META"
    ).upper().strip()

    period = st.selectbox("ย้อนหลัง", ["1y", "2y", "5y"], index=1)

    if st.button("📈 สร้างกราฟ", type="primary"):

        symbols = symbols_input.split()

        if not symbols:
            st.error("กรุณาพิมพ์ชื่อหุ้นอย่างน้อย 1 ตัว")
        else:
            import yfinance as yf
            import pandas as pd
            import matplotlib as mpl
            import matplotlib.pyplot as plt
            mpl.rcParams['font.family'] = 'Tahoma'

            # === กราฟเปรียบเทียบ ===
            st.subheader("📊 เปรียบเทียบผลตอบแทน")

            fig_compare, ax_compare = plt.subplots(figsize=(12, 5))

            for symbol in symbols:
                try:
                    ticker = yf.Ticker(symbol)
                    history = ticker.history(period=period)
                    first_price = history["Close"].iloc[0]
                    normalized = (history["Close"] / first_price - 1) * 100
                    ax_compare.plot(history.index, normalized, linewidth=1.5, label=symbol)
                except:
                    st.warning(f"⚠️ ดึง {symbol} ไม่ได้")

            ax_compare.axhline(y=0, color="gray", linewidth=0.5, linestyle=":")
            ax_compare.set_ylabel("Return (%)")
            ax_compare.legend()
            ax_compare.grid(True, alpha=0.3)
            ax_compare.set_title(f"Stock Comparison ({period})")

            st.pyplot(fig_compare)
            plt.close()

            st.markdown("---")

            # === กราฟรายตัว + Technical Signals ===
            for symbol in symbols:
                try:
                    st.subheader(f"📈 {symbol}")

                    ticker = yf.Ticker(symbol)
                    history = ticker.history(period=period)

                    # คำนวณ MA
                    history["SMA50"] = history["Close"].rolling(50).mean()
                    history["SMA200"] = history["Close"].rolling(200).mean()

                    # สร้างกราฟ
                    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7),
                                                     gridspec_kw={"height_ratios": [3, 1]})

                    current = history["Close"].iloc[-1]
                    ax1.plot(history.index, history["Close"], color="royalblue", linewidth=1.5, label="Price")
                    ax1.plot(history.index, history["SMA50"], color="orange", linewidth=1, label="SMA 50", linestyle="--")
                    ax1.plot(history.index, history["SMA200"], color="red", linewidth=1, label="SMA 200", linestyle="--")
                    ax1.set_title(f"{symbol} — ${current:.2f}", fontsize=14, fontweight="bold")
                    ax1.set_ylabel("Price (USD)")
                    ax1.legend(loc="upper left")
                    ax1.grid(True, alpha=0.3)

                    ax2.bar(history.index, history["Volume"], color="steelblue", alpha=0.5)
                    ax2.set_ylabel("Volume")
                    ax2.grid(True, alpha=0.3)

                    plt.tight_layout()
                    st.pyplot(fig)
                    plt.close()

                    # Technical Signals
                    sma50 = history["SMA50"].iloc[-1]
                    sma200 = history["SMA200"].iloc[-1]
                    high_52w = history["Close"].tail(252).max()
                    low_52w = history["Close"].tail(252).min()
                    position = (current - low_52w) / (high_52w - low_52w) * 100

                    # แสดง Metrics
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("SMA 50", f"${sma50:.2f}")
                    with col2:
                        st.metric("SMA 200", f"${sma200:.2f}")
                    with col3:
                        st.metric("52W Range", f"${low_52w:.0f} — ${high_52w:.0f}")
                    with col4:
                        st.metric("ตำแหน่ง 52W", f"{position:.0f}%")

                    # สัญญาณ
                    if sma50 > sma200:
                        st.success("✅ Golden Cross — แนวโน้มขาขึ้น")
                    else:
                        st.warning("⚠️ Death Cross — แนวโน้มขาลง")

                    if position > 90:
                        st.warning(f"⚠️ ราคาใกล้ 52W High ({position:.0f}%) — ระวังแพง")
                    elif position < 30:
                        st.info(f"💡 ราคาใกล้ 52W Low ({position:.0f}%) — อาจเป็นจุดซื้อ")

                    if current < sma200 * 0.95:
                        st.info("💡 ราคาต่ำกว่า SMA200 มากกว่า 5% — อาจเป็นจุดซื้อ")

                    st.markdown("---")

                except Exception as e:
                    st.error(f"❌ {symbol}: {e}")
elif page == "🔄 DCA Backtest":
    st.header("🔄 DCA Backtest")

    col_input1, col_input2, col_input3 = st.columns(3)

    with col_input1:
        symbol_dca = st.text_input("ชื่อหุ้น", value="MSFT").upper().strip()
    with col_input2:
        monthly_amount = st.number_input("ลงทุน/เดือน (USD)", value=10000, step=1000)
    with col_input3:
        dca_period = st.selectbox("ย้อนหลัง", ["1y", "2y", "5y"], index=1, key="dca_period")

    if st.button("🔄 เริ่ม Backtest", type="primary"):

        try:
            from dca_backtest import dca_backtest, lump_sum_backtest
            import matplotlib as mpl
            import matplotlib.pyplot as plt
            mpl.rcParams['font.family'] = 'Tahoma'

            progress = st.progress(0, text="กำลังคำนวณ DCA...")

            # DCA
            progress.progress(30, text="คำนวณ DCA...")
            dca = dca_backtest(symbol_dca, monthly_amount, dca_period)

            # Lump Sum
            progress.progress(60, text="คำนวณ Lump Sum...")
            lump = lump_sum_backtest(symbol_dca, dca["total_invested"], dca_period)

            progress.progress(100, text="เสร็จสมบูรณ์!")

            st.markdown("---")

            # เปรียบเทียบ
            st.subheader(f"⚔️ DCA vs Lump Sum: {symbol_dca}")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### DCA")
                st.metric("ลงทุนรวม", f"${dca['total_invested']:,.2f}")
                st.metric("มูลค่าปัจจุบัน", f"${dca['final_value']:,.2f}")
                st.metric("ต้นทุนเฉลี่ย", f"${dca['avg_cost']:,.2f}")
                if dca["profit"] >= 0:
                    st.success(f"กำไร: ${dca['profit']:,.2f} ({dca['profit_pct']:.1f}%)")
                else:
                    st.error(f"ขาดทุน: ${dca['profit']:,.2f} ({dca['profit_pct']:.1f}%)")

            with col2:
                st.markdown("### Lump Sum")
                st.metric("ลงทุนรวม", f"${lump['total_invested']:,.2f}")
                st.metric("มูลค่าปัจจุบัน", f"${lump['final_value']:,.2f}")
                st.metric("ซื้อที่ราคา", f"${lump['buy_price']:,.2f}")
                if lump["profit"] >= 0:
                    st.success(f"กำไร: ${lump['profit']:,.2f} ({lump['profit_pct']:.1f}%)")
                else:
                    st.error(f"ขาดทุน: ${lump['profit']:,.2f} ({lump['profit_pct']:.1f}%)")

            # ผู้ชนะ
            st.markdown("---")
            if dca["profit"] > lump["profit"]:
                st.success(f"🏆 DCA ชนะ! ต่างกัน ${dca['profit'] - lump['profit']:,.2f}")
            else:
                st.info(f"🏆 Lump Sum ชนะ! ต่างกัน ${lump['profit'] - dca['profit']:,.2f}")

            # กราฟ DCA Growth
            st.markdown("---")
            st.subheader("📈 DCA Growth Chart")

            records = dca["records"]
            months = [r["month"] for r in records]
            invested = [r["total_invested"] for r in records]
            values = [r["current_value"] for r in records]

            fig, ax = plt.subplots(figsize=(12, 5))

            ax.plot(months, invested, color="gray", linewidth=2, label="เงินลงทุนสะสม", linestyle="--")
            ax.fill_between(months, invested, values,
                             where=[v >= i for v, i in zip(values, invested)],
                             color="green", alpha=0.3, label="กำไร")
            ax.fill_between(months, invested, values,
                             where=[v < i for v, i in zip(values, invested)],
                             color="red", alpha=0.3, label="ขาดทุน")
            ax.plot(months, values, color="royalblue", linewidth=2, label="มูลค่าพอร์ต")

            ax.set_title(f"DCA: {symbol_dca} (${monthly_amount:,}/เดือน)", fontsize=14, fontweight="bold")
            ax.set_ylabel("USD")
            ax.legend()
            ax.grid(True, alpha=0.3)

            tick_positions = range(0, len(months), 3)
            ax.set_xticks(tick_positions)
            ax.set_xticklabels([months[i] for i in tick_positions], rotation=45)

            plt.tight_layout()
            st.pyplot(fig)
            plt.close()

        except Exception as e:
            st.error(f"❌ เกิดข้อผิดพลาด: {e}")
elif page == "🎯 Position Sizer":
    st.header("🎯 Position Sizing Calculator")
    st.markdown("คำนวณขนาด Position ที่เหมาะสม + เช็คความเสี่ยงพอร์ต")

    # === ข้อมูลพอร์ต ===
    st.sidebar.markdown("---")
    st.sidebar.subheader("💰 ข้อมูลพอร์ต")
    portfolio_value = st.sidebar.number_input("มูลค่าพอร์ต (USD)", value=100000, step=10000)
    cash_available = st.sidebar.number_input("เงินสดที่มี (USD)", value=25000, step=5000)

    # === Holdings ปัจจุบัน ===
    st.subheader("📂 Holdings ปัจจุบัน")
    st.markdown("ใส่หุ้นที่ถืออยู่ (1 บรรทัด = 1 ตัว, รูปแบบ: `TICKER มูลค่า`)")

    holdings_text = st.text_area(
        "Holdings",
        value="NVDA 8000\nLLY 7000\nJPM 6000\nXOM 4000",
        height=150,
    )

    # แปลง Text เป็น Holdings Dict
    holdings = {}
    for line in holdings_text.strip().split("\n"):
        parts = line.strip().split()
        if len(parts) >= 2:
            try:
                ticker = parts[0].upper()
                value = float(parts[1])
                holdings[ticker] = {"market_value": value}
            except:
                pass

    # แสดง Holdings ที่ Parse ได้
    if holdings:
        import pandas as pd
        from portfolio.sector_classifier import get_sector, get_sector_exposure

        holdings_rows = []
        for ticker, h in holdings.items():
            pct = (h["market_value"] / portfolio_value) * 100
            holdings_rows.append({
                "Ticker": ticker,
                "มูลค่า": f"${h['market_value']:,.0f}",
                "% ของพอร์ต": f"{pct:.1f}%",
                "Sector": get_sector(ticker),
            })

        df_holdings = pd.DataFrame(holdings_rows)
        st.dataframe(df_holdings, use_container_width=True, hide_index=True)

        # Sector Breakdown
        sector_exp = get_sector_exposure(holdings, portfolio_value)
        holdings_total = sum(h["market_value"] for h in holdings.values())
        cash_pct = (cash_available / portfolio_value) * 100

        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.metric("Holdings รวม", f"${holdings_total:,.0f}")
        with col_s2:
            st.metric("Cash", f"${cash_available:,.0f} ({cash_pct:.0f}%)")
        with col_s3:
            invested_pct = ((holdings_total + cash_available) / portfolio_value) * 100
            st.metric("รวมทั้งหมด", f"{invested_pct:.0f}%")

    st.markdown("---")

    # === คำนวณ Position ===
    st.subheader("🎯 คำนวณ Position ใหม่")

    col_in1, col_in2 = st.columns(2)

    with col_in1:
        new_ticker = st.text_input("หุ้นที่จะซื้อ", value="ADBE").upper().strip()
    with col_in2:
        conviction = st.slider("Conviction Score", min_value=1, max_value=10, value=7)

    # แสดง Conviction Guide
    with st.expander("📖 Conviction Score หมายถึงอะไร?"):
        st.markdown("""
        | คะแนน | ความหมาย | ขนาด Position |
        |---|---|---|
        | 9-10 | เข้าใจธุรกิจลึก + Valuation ถูก + มี Catalyst | 8-10% |
        | 7-8 | เข้าใจดี + ราคาเหมาะสม | 5-7% |
        | 5-6 | รู้จักพอสมควร + ราคาไม่แพง | 3-5% |
        | 3-4 | รู้จักผิวเผิน + เก็งกำไร | 2-3% |
        | 1-2 | แค่ติดตาม ยังไม่แน่ใจ | 1-2% |
        """)

    if st.button("🎯 คำนวณ Position Size", type="primary"):

        try:
            from portfolio.position_sizer import suggest_position_size

            with st.spinner("กำลังคำนวณ..."):
                result = suggest_position_size(
                    ticker=new_ticker,
                    portfolio_value=portfolio_value,
                    conviction=conviction,
                    holdings=holdings,
                    cash_available=cash_available,
                )

            st.markdown("---")

            # === ผลลัพธ์หลัก ===
            st.subheader(f"📊 ผลลัพธ์: {new_ticker}")

            col_r1, col_r2, col_r3, col_r4 = st.columns(4)
            with col_r1:
                st.metric("Conviction", f"{result['conviction']}/10")
            with col_r2:
                st.metric("Category", result["category"])
            with col_r3:
                st.metric("Max Position", f"{result['max_pct']}%")
            with col_r4:
                st.metric("แนะนำ", f"${result['recommended_usd']:,.0f} ({result['recommended_pct']}%)")

            # === Concentration Check ===
            st.markdown("---")
            check = result["concentration_check"]

            if check["suggestion"] == "BUY":
                st.success(f"✅ ซื้อได้! Position {result['recommended_pct']}% (${result['recommended_usd']:,.0f})")
            elif check["suggestion"] == "REDUCE_SIZE":
                st.warning(f"⚠️ ซื้อได้แต่ลดขนาด: {result['recommended_pct']}% (${result['recommended_usd']:,.0f})")
            else:
                st.error("❌ ไม่แนะนำให้ซื้อตอนนี้")

            # แสดง Violations & Warnings
            for v in check["violations"]:
                st.error(v)
            for w in check["warnings"]:
                st.warning(w)

            # Cash หลังซื้อ
            st.metric("Cash หลังซื้อ", f"{result['cash_after_pct']:.1f}%")

            # === Tranche Plan ===
            if result["tranches"]:
                st.markdown("---")
                st.subheader("📋 Tranche Plan (แผนเข้าซื้อ)")

                tranche_rows = []
                for t in result["tranches"]:
                    tranche_rows.append({
                        "งวด": f"T{t['tranche']}",
                        "สัดส่วน": t["allocation"],
                        "ราคาเป้า": f"${t['trigger_price']:,.2f}",
                        "Drop from High": t["drop_from_high"],
                        "จำนวนเงิน": f"${t['amount_usd']:,.0f}",
                        "จำนวนหุ้น": f"{t['est_shares']} หุ้น",
                    })

                df_tranches = pd.DataFrame(tranche_rows)
                st.dataframe(df_tranches, use_container_width=True, hide_index=True)

                st.info(f"""
                💡 **วิธีใช้ Tranche Plan:**
                - T1: ซื้องวดแรกเมื่อราคาลงถึง {result['tranches'][0]['trigger_price']}
                - T2: ซื้อเพิ่มเมื่อลงอีก
                - T3: ซื้อเต็มจำนวนเมื่อราคาถูกมาก
                - ถ้าราคาไม่ลง ไม่ต้องไล่ซื้อ รอจังหวะ
                """)

        except Exception as e:
            st.error(f"❌ เกิดข้อผิดพลาด: {e}")

elif page == "📰 TA Analysis":
    st.header("📰 Technical Analysis + Confluence")
    st.markdown("วิเคราะห์เทคนิค 6 Indicators + หาจุด Confluence อัตโนมัติ")

    # Init session state
    if "ta_result" not in st.session_state:
        st.session_state.ta_result = None
    if "ta_ai_report" not in st.session_state:
        st.session_state.ta_ai_report = None

    col_input1, col_input2 = st.columns([3, 1])
    with col_input1:
        ta_ticker = st.text_input("ชื่อหุ้น", value="META", key="ta_ticker_input").upper().strip()
    with col_input2:
        ta_period = st.selectbox("ย้อนหลัง", ["6mo", "1y", "2y"], index=1, key="ta_period_input")

    if st.button("📰 วิเคราะห์ TA", type="primary"):
        try:
            from ta_engine.indicators import get_all_indicators
            from ta_engine.confluence import detect_confluence, build_fib_table

            with st.spinner("กำลังวิเคราะห์..."):
                indicators = get_all_indicators(ta_ticker, ta_period)
                confluences = detect_confluence(indicators)

            # เก็บผลลัพธ์ใน Session State
            st.session_state.ta_result = {
                "ticker": ta_ticker,
                "indicators": indicators,
                "confluences": confluences,
            }
            st.session_state.ta_ai_report = None  # Reset AI Report

        except Exception as e:
            st.error(f"❌ เกิดข้อผิดพลาด: {e}")

    # === แสดงผลลัพธ์ (อ่านจาก session_state) ===
    if st.session_state.ta_result is not None:
        import matplotlib as mpl
        import matplotlib.pyplot as plt
        mpl.rcParams['font.family'] = 'Tahoma'
        from ta_engine.confluence import build_fib_table

        result = st.session_state.ta_result
        ticker_show = result["ticker"]
        indicators = result["indicators"]
        confluences = result["confluences"]

        st.markdown("---")

        # Overall Signal
        overall = indicators["overall"]
        if overall == "BULLISH":
            st.success(f"🟢 Overall: **{overall}** (Bullish: {indicators['bullish_count']}, Bearish: {indicators['bearish_count']})")
        elif overall == "BEARISH":
            st.error(f"🔴 Overall: **{overall}** (Bullish: {indicators['bullish_count']}, Bearish: {indicators['bearish_count']})")
        else:
            st.info(f"⚪ Overall: **{overall}** (Bullish: {indicators['bullish_count']}, Bearish: {indicators['bearish_count']})")

        # Price Metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("ราคา", f"${indicators['current_price']}", f"{indicators['change_pct']:+.2f}%")
        with col2:
            rsi = indicators["rsi"]
            st.metric("RSI", f"{rsi.values['current']}")
        with col3:
            macd = indicators["macd"]
            st.metric("MACD Histogram", f"{macd.values['histogram']:.4f}")
        with col4:
            bb = indicators["bb"]
            st.metric("BB %B", f"{bb.values['pct_b']:.1f}%")

        # Tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📈 กราฟ + Fibo",
            "⭐ Confluence",
            "📊 Indicators",
            "📐 Fib Table",
            "🤖 AI Report",
        ])

        # === Tab 1: กราฟ ===
        with tab1:
            df = indicators["df"]
            fib = indicators["fibonacci"]

            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8),
                                             gridspec_kw={"height_ratios": [3, 1]})

            ax1.plot(df.index, df["Close"], color="royalblue", linewidth=1.5, label="Price")

            for name, sma in indicators["sma"].items():
                if sma.values.get("current"):
                    sma_series = df["Close"].rolling(int(name.split("_")[1])).mean()
                    color = "orange" if "50" in name else "purple" if "100" in name else "red"
                    ax1.plot(df.index, sma_series, color=color, linewidth=1,
                            label=f"{name} (${sma.values['current']})", linestyle="--")

            if "levels" in fib.values:
                for level in fib.values["levels"]:
                    if not level["is_extension"]:
                        color = "green" if level["role"] == "SUP" else "red"
                        ax1.axhline(y=level["price"], color=color, linewidth=0.5,
                                   linestyle=":", alpha=0.7)

            for conf in confluences:
                color = "green" if conf.role == "SUP" else "red"
                ax1.axhline(y=conf.price, color=color, linewidth=2, linestyle="-", alpha=0.8)
                ax1.text(df.index[0], conf.price,
                        f" {'⭐' * conf.strength} ${conf.price:.0f}",
                        fontsize=8, fontweight="bold", color=color, va="center")

            ax1.set_title(f"{ticker_show} — ${indicators['current_price']} ({indicators['change_pct']:+.2f}%)",
                         fontsize=14, fontweight="bold")
            ax1.set_ylabel("Price (USD)")
            ax1.legend(loc="upper left", fontsize=8)
            ax1.grid(True, alpha=0.3)

            colors = ["green" if df["Close"].iloc[i] >= df["Close"].iloc[i-1] else "red"
                     for i in range(1, len(df))]
            colors.insert(0, "gray")
            ax2.bar(df.index, df["Volume"], color=colors, alpha=0.5)
            ax2.set_ylabel("Volume")
            ax2.grid(True, alpha=0.3)

            plt.tight_layout()
            st.pyplot(fig)
            plt.close()

        # === Tab 2: Confluence ===
        with tab2:
            if confluences:
                st.subheader(f"พบ {len(confluences)} จุด Confluence")
                for conf in confluences:
                    stars = "⭐" * conf.strength
                    if conf.role == "SUP":
                        st.success(f"{stars} **แนวรับ ${conf.price:,.2f}** ({conf.pct_from_current:+.1f}%) — {' + '.join(conf.components)}")
                    else:
                        st.error(f"{stars} **แนวต้าน ${conf.price:,.2f}** ({conf.pct_from_current:+.1f}%) — {' + '.join(conf.components)}")
            else:
                st.warning("ไม่พบ Confluence ที่ชัดเจน")

        # === Tab 3: Indicators ===
        with tab3:
            st.subheader("📏 Moving Averages")
            for name, sma in indicators["sma"].items():
                icon = "🟢" if sma.interpretation == "bullish" else "🔴" if sma.interpretation == "bearish" else "⚪"
                st.markdown(f"{icon} {sma.detail}")

            st.markdown("---")
            st.subheader("📊 RSI")
            rsi = indicators["rsi"]
            icon = "🟢" if rsi.interpretation == "bullish" else "🔴" if rsi.interpretation == "bearish" else "⚪"
            st.markdown(f"{icon} {rsi.detail}")

            st.markdown("---")
            st.subheader("📈 MACD")
            macd = indicators["macd"]
            icon = "🟢" if macd.interpretation == "bullish" else "🔴" if macd.interpretation == "bearish" else "⚪"
            st.markdown(f"{icon} {macd.detail}")

            st.markdown("---")
            st.subheader("🔔 Bollinger Bands")
            bb = indicators["bb"]
            icon = "🟢" if bb.interpretation == "bullish" else "🔴" if bb.interpretation == "bearish" else "⚪"
            st.markdown(f"{icon} {bb.detail}")

            st.markdown("---")
            st.subheader("📊 Volume")
            vol = indicators["volume"]
            icon = "🟢" if vol.interpretation == "bullish" else "🔴" if vol.interpretation == "bearish" else "⚪"
            st.markdown(f"{icon} {vol.detail}")

        # === Tab 4: Fib Table ===
        with tab4:
            st.subheader("📐 Fibonacci Levels")
            fib = indicators["fibonacci"]
            st.markdown(f"**{fib.detail}**")
            df_fib = build_fib_table(indicators, confluences)
            if not df_fib.empty:
                st.dataframe(df_fib, use_container_width=True, hide_index=True)

        # === Tab 5: AI Report ===
        with tab5:
            st.subheader("🤖 AI Technical Analysis")

            if st.button("✨ สร้าง AI Report", key="gen_ta_report"):
                with st.spinner("AI กำลังเขียนรายงาน TA... (30-60 วินาที)"):
                    import ollama

                    ta_summary = f"""ข้อมูล Technical Analysis ของ {ticker_show}:

ราคาปัจจุบัน: ${indicators['current_price']} ({indicators['change_pct']:+.2f}%)
Overall Signal: {indicators['overall']}

SMA:
"""
                    for name, sma in indicators["sma"].items():
                        ta_summary += f"  {sma.detail}\n"

                    ta_summary += f"""
RSI: {indicators['rsi'].detail}
MACD: {indicators['macd'].detail}
Bollinger: {indicators['bb'].detail}
Volume: {indicators['volume'].detail}
Fibonacci: {indicators['fibonacci'].detail}

Confluence Points:
"""
                    for conf in confluences:
                        ta_summary += f"  {conf.description}\n"

                    prompt = f"""คุณเป็นนักวิเคราะห์เทคนิคมืออาชีพ
ตอบเป็นภาษาไทย ห้ามใช้ภาษาจีนเด็ดขาด ใช้ศัพท์การเงินอังกฤษได้
เป็นกันเอง เหมือนเล่าให้เพื่อนฟัง ใช้ Emoji แบ่งหัวข้อ

{ta_summary}

เขียนบทความวิเคราะห์เทคนิคตามหัวข้อนี้:

🌐 สรุปภาพรวม: ราคาอยู่ตรงไหน ทิศทางเป็นยังไง
🌊 โครงสร้างเทรนด์: SMA บอกอะไร
📐 Fibonacci & Confluence: "ด่านเหล็ก" อยู่ที่ไหน
📊 โมเมนตัม: RSI + MACD + Volume
🎯 สรุป: Bull Case vs Bear Case + จุดเข้า/ออก + Stop Loss + R:R ratio
"""

                    response = ollama.chat(
                        model="qwen2.5:14b",
                        messages=[{"role": "user", "content": prompt}]
                    )

                    st.session_state.ta_ai_report = response["message"]["content"]

            # แสดง AI Report ถ้ามี
            if st.session_state.ta_ai_report:
                st.markdown(st.session_state.ta_ai_report)
        