import yfinance as yf
import ollama
from datetime import datetime

# ==========================================
#  ส่วนที่ 1: ดึงข้อมูลหุ้น
# ==========================================

def fetch_stock_data(symbol):
    """ดึงข้อมูลสำคัญของหุ้น"""
    ticker = yf.Ticker(symbol)
    info = ticker.info

    stock_data = {
        "ชื่อบริษัท": info.get("longName", "N/A"),
        "Sector": info.get("sector", "N/A"),
        "ราคาปัจจุบัน": info.get("currentPrice", 0),
        "Market Cap (B$)": round(info.get("marketCap", 0) / 1e9, 2),
        "P/E Ratio": info.get("trailingPE", None),
        "Forward P/E": info.get("forwardPE", None),
        "EPS": info.get("trailingEps", None),
        "Revenue Growth YoY": info.get("revenueGrowth", None),
        "Profit Margin": info.get("profitMargins", None),
        "Debt to Equity": info.get("debtToEquity", None),
        "ROE": info.get("returnOnEquity", None),
        "Dividend Yield": info.get("dividendYield", None),
        "52W High": info.get("fiftyTwoWeekHigh", None),
      "52W Low": info.get("fiftyTwoWeekLow", None),
    }

    # เพิ่ม Earnings Date
    try:
        cal = ticker.earnings_dates
        if cal is not None and not cal.empty:
            # หาวัน Earnings ถัดไป (อนาคต)
            from datetime import datetime
            now = datetime.now()
            future_dates = cal[cal.index > now.strftime("%Y-%m-%d")]
            if not future_dates.empty:
                next_earnings = future_dates.index[-1].strftime("%Y-%m-%d")
                stock_data["Earnings Date (Next)"] = next_earnings
            else:
                stock_data["Earnings Date (Next)"] = "N/A"

            # Earnings ล่าสุด (อดีต)
            past_dates = cal[cal.index <= now.strftime("%Y-%m-%d")]
            if not past_dates.empty:
                last_row = past_dates.iloc[0]
                stock_data["Last Earnings"] = past_dates.index[0].strftime("%Y-%m-%d")
                eps_actual = last_row.get("Reported EPS", None)
                eps_estimate = last_row.get("EPS Estimate", None)
                stock_data["EPS Actual"] = eps_actual
                stock_data["EPS Estimate"] = eps_estimate

                if eps_actual is not None and eps_estimate is not None and eps_estimate != 0:
                    surprise = ((eps_actual - eps_estimate) / abs(eps_estimate)) * 100
                    stock_data["EPS Surprise"] = f"{surprise:.1f}%"
    except Exception as e:
        stock_data["Earnings Date (Next)"] = "N/A"

    return stock_data, ticker, info
#  ส่วนที่ 2: ดึงงบการเงิน
# ==========================================

def fetch_financials(ticker):
    """ดึงงบการเงิน 4 ปีย้อนหลัง + แปลงสกุลเงินเป็น USD"""
    income = ticker.income_stmt
    balance = ticker.balance_sheet
    cashflow = ticker.cashflow

    # เช็คสกุลเงิน
    info = ticker.info
    financial_currency = info.get("financialCurrency", "USD")

    fx_rate = 1.0
    if financial_currency != "USD":
        try:
            import yfinance as yf
            fx_ticker = yf.Ticker(f"{financial_currency}USD=X")
            fx_history = fx_ticker.history(period="5d")
            if not fx_history.empty:
                fx_rate = float(fx_history["Close"].iloc[-1])
                print(f"  💱 Currency: {financial_currency} → USD (rate: {fx_rate:.6f})")
        except Exception as e:
            print(f"  ⚠️ FX error: {e}")

    years = income.columns
    yearly_data = []

    def safe_get(df, row_name, year):
        try:
            value = df.loc[row_name, year]
            if value is not None:
                return float(value) * fx_rate
        except:
            pass
        return None

    for year in years:
        year_label = str(year.year) if hasattr(year, 'year') else str(year)
        yearly_data.append({
            "year": year_label,
            "revenue": safe_get(income, "Total Revenue", year),
            "net_income": safe_get(income, "Net Income", year),
            "ebitda": safe_get(income, "EBITDA", year),
            "total_assets": safe_get(balance, "Total Assets", year),
            "total_debt": safe_get(balance, "Total Debt", year),
            "free_cashflow": safe_get(cashflow, "Free Cash Flow", year),
        })

    return yearly_data


# ==========================================
#  ส่วนที่ 3: Reverse DCF
# ==========================================

def reverse_dcf(info, yearly_data):
    """คำนวณ Implied Growth Rate จาก Reverse DCF"""
    current_price = info.get("currentPrice", 0)
    shares_out = info.get("sharesOutstanding", 0)
    market_cap = current_price * shares_out

    latest_fcf = yearly_data[0]["free_cashflow"]
    if latest_fcf is None or latest_fcf <= 0:
        return {"error": "Free Cash Flow ไม่มีข้อมูลหรือติดลบ"}

    discount_rate = 0.10
    terminal_growth = 0.03

# ลอง Growth ตั้งแต่ -20% ถึง +50% (ละเอียด 0.5%)
    best_growth = 0
    smallest_diff = float("inf")

    for test_growth in range(-40, 101):
        growth = test_growth / 200  # -20% ถึง +50% ทีละ 0.5%

        total_value = 0
        fcf = latest_fcf

        for year in range(1, 11):
            fcf = fcf * (1 + growth)
            present_value = fcf / (1 + discount_rate) ** year
            total_value += present_value

        terminal_value = fcf * (1 + terminal_growth) / (discount_rate - terminal_growth)
        terminal_pv = terminal_value / (1 + discount_rate) ** 10
        total_value += terminal_pv

        diff = abs(total_value - market_cap)
        if diff < smallest_diff:
            smallest_diff = diff
            best_growth = growth

    return {
        "current_price": current_price,
        "market_cap_B": round(market_cap / 1e9, 2),
        "latest_fcf_B": round(latest_fcf / 1e9, 2),
        "implied_growth": best_growth,
        "discount_rate": discount_rate,
        "terminal_growth": terminal_growth,
    }


# ==========================================
#  ส่วนที่ 4: Scoring System
# ==========================================

def score_stock(info, dcf_result):
    """ให้คะแนนหุ้น 0-100 จาก 5 เกณฑ์"""
    scores = {}

    pe = info.get("trailingPE", None)
    if pe is None:
        scores["P/E Ratio"] = {"score": 0, "reason": "ไม่มีข้อมูล"}
    elif pe < 15:
        scores["P/E Ratio"] = {"score": 20, "reason": f"P/E {pe:.1f} → ถูกมาก"}
    elif pe < 25:
        scores["P/E Ratio"] = {"score": 15, "reason": f"P/E {pe:.1f} → เหมาะสม"}
    elif pe < 35:
        scores["P/E Ratio"] = {"score": 10, "reason": f"P/E {pe:.1f} → ค่อนข้างแพง"}
    else:
        scores["P/E Ratio"] = {"score": 5, "reason": f"P/E {pe:.1f} → แพง"}

    growth = info.get("revenueGrowth", None)
    if growth is None:
        scores["Revenue Growth"] = {"score": 0, "reason": "ไม่มีข้อมูล"}
    elif growth > 0.25:
        scores["Revenue Growth"] = {"score": 20, "reason": f"{growth:.1%} → โตเร็วมาก"}
    elif growth > 0.15:
        scores["Revenue Growth"] = {"score": 15, "reason": f"{growth:.1%} → โตดี"}
    elif growth > 0.05:
        scores["Revenue Growth"] = {"score": 10, "reason": f"{growth:.1%} → โตปานกลาง"}
    else:
        scores["Revenue Growth"] = {"score": 5, "reason": f"{growth:.1%} → โตช้า"}

    margin = info.get("profitMargins", None)
    if margin is None:
        scores["Profit Margin"] = {"score": 0, "reason": "ไม่มีข้อมูล"}
    elif margin > 0.25:
        scores["Profit Margin"] = {"score": 20, "reason": f"{margin:.1%} → กำไรสูงมาก"}
    elif margin > 0.15:
        scores["Profit Margin"] = {"score": 15, "reason": f"{margin:.1%} → กำไรดี"}
    elif margin > 0.05:
        scores["Profit Margin"] = {"score": 10, "reason": f"{margin:.1%} → กำไรพอใช้"}
    else:
        scores["Profit Margin"] = {"score": 5, "reason": f"{margin:.1%} → กำไรบาง"}

    de = info.get("debtToEquity", None)
    if de is None:
        scores["Debt/Equity"] = {"score": 0, "reason": "ไม่มีข้อมูล"}
    elif de < 30:
        scores["Debt/Equity"] = {"score": 20, "reason": f"D/E {de:.1f}% → หนี้น้อย"}
    elif de < 60:
        scores["Debt/Equity"] = {"score": 15, "reason": f"D/E {de:.1f}% → หนี้ปานกลาง"}
    elif de < 100:
        scores["Debt/Equity"] = {"score": 10, "reason": f"D/E {de:.1f}% → หนี้ค่อนข้างสูง"}
    else:
        scores["Debt/Equity"] = {"score": 5, "reason": f"D/E {de:.1f}% → หนี้สูง"}

    if "error" not in dcf_result and growth is not None:
        implied = dcf_result["implied_growth"]
        gap = implied - growth
        if gap < 0:
            scores["Valuation"] = {"score": 20, "reason": f"ตลาดคาด {implied:.0%} < โตจริง {growth:.1%} → ราคาถูก!"}
        elif gap < 0.05:
            scores["Valuation"] = {"score": 15, "reason": f"ตลาดคาด {implied:.0%} ≈ โตจริง {growth:.1%} → เหมาะสม"}
        elif gap < 0.10:
            scores["Valuation"] = {"score": 10, "reason": f"ตลาดคาด {implied:.0%} > โตจริง {growth:.1%} → ค่อนข้างแพง"}
        else:
            scores["Valuation"] = {"score": 5, "reason": f"ตลาดคาด {implied:.0%} >> โตจริง {growth:.1%} → แพง"}
    else:
        scores["Valuation"] = {"score": 0, "reason": "คำนวณไม่ได้"}

    return scores
# ==========================================
#  ส่วนที่ 5: AI Full Report
# ==========================================

def generate_report(symbol, stock_data, metrics, dcf_result, scores):
    """ให้ AI เขียนรายงานวิเคราะห์ฉบับเต็ม"""

    # รวมคะแนน
    score_text = ""
    total = 0
    for criteria, result in scores.items():
        score_text += f"  {criteria}: {result['score']}/20 ({result['reason']})\n"
        total += result["score"]

    # รวมงบการเงิน
    fin_text = ""
    for d in metrics:
        rev = f"${d['revenue']/1e9:.2f}B" if d['revenue'] else "N/A"
        ni = f"${d['net_income']/1e9:.2f}B" if d['net_income'] else "N/A"
        fcf = f"${d['free_cashflow']/1e9:.2f}B" if d['free_cashflow'] else "N/A"
        fin_text += f"  {d['year']}: Revenue={rev}, Net Income={ni}, FCF={fcf}\n"

    # รวมข้อมูลพื้นฐาน
    basic_text = ""
    for key, value in stock_data.items():
        basic_text += f"  {key}: {value}\n"

    prompt = f"""คุณเป็นนักวิเคราะห์หุ้นมืออาชีพแนว Value Investing ที่เข้มงวดมาก
ใช้ข้อมูลจริงด้านล่างเท่านั้น ห้ามแต่งตัวเลขเพิ่ม ตอบเป็นภาษาไทย
ห้ามใช้ภาษาจีน ญี่ปุ่น หรือภาษาอื่นนอกจากไทยและอังกฤษเด็ดขาด
ใช้ศัพท์การเงินภาษาอังกฤษได้ เช่น Revenue, P/E, Free Cash Flow

=== หุ้น: {symbol} ===

ข้อมูลพื้นฐาน:
{basic_text}

งบการเงิน 4 ปีย้อนหลัง:
{fin_text}

Reverse DCF:
  ราคาปัจจุบัน: ${dcf_result.get('current_price', 'N/A')}
  Market Cap: ${dcf_result.get('market_cap_B', 'N/A')}B
  Free Cash Flow ล่าสุด: ${dcf_result.get('latest_fcf_B', 'N/A')}B
  Implied Growth Rate: {dcf_result.get('implied_growth', 0):.0%}

คะแนน ({total}/100):
{score_text}

กรุณาเขียนรายงานวิเคราะห์ตามหัวข้อนี้:

1. สรุปผู้บริหาร (3 บรรทัด)
2. วิเคราะห์งบการเงิน (Revenue, Net Income, Free Cash Flow แนวโน้ม)
3. วิเคราะห์ Valuation (Reverse DCF บอกอะไร, แพงหรือถูก)
4. ความเสี่ยงหลัก 2 ข้อ (เจาะจง ไม่ใช่ความเสี่ยงทั่วไป)
5. คำตัดสิน: ซื้อ / ถือ / ขาย / รอจังหวะ
   - ถ้า "รอจังหวะ" ราคาเท่าไหร่ถึงน่าซื้อ
   - ถ้า "ซื้อ" ควร DCA กี่งวด
"""

    response = ollama.chat(
        model="qwen2.5:14b",
        messages=[{"role": "user", "content": prompt}]
    )

    return response["message"]["content"]


# ==========================================
#  ส่วนที่ 6: บันทึกรายงานเป็นไฟล์
# ==========================================

def save_report(symbol, stock_data, metrics, dcf_result, scores, ai_report):
    """บันทึกรายงานทั้งหมดเป็นไฟล์ .txt"""

    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"stock_ai/reports/{symbol}_{today}.txt"

    with open(filename, "w", encoding="utf-8") as f:
        # หัวรายงาน
        f.write("=" * 60 + "\n")
        f.write(f"  Stock Analysis Report: {symbol}\n")
        f.write(f"  วันที่: {today}\n")
        f.write("=" * 60 + "\n\n")

        # ข้อมูลพื้นฐาน
        f.write("--- ข้อมูลพื้นฐาน ---\n\n")
        for key, value in stock_data.items():
            f.write(f"  {key}: {value}\n")

        # งบการเงิน
        f.write("\n--- งบการเงิน 4 ปีย้อนหลัง ---\n\n")
        for d in metrics:
            rev = f"${d['revenue']/1e9:.2f}B" if d['revenue'] else "N/A"
            ni = f"${d['net_income']/1e9:.2f}B" if d['net_income'] else "N/A"
            fcf = f"${d['free_cashflow']/1e9:.2f}B" if d['free_cashflow'] else "N/A"
            f.write(f"  {d['year']}: Revenue={rev}, Net Income={ni}, FCF={fcf}\n")

        # Reverse DCF
        f.write("\n--- Reverse DCF ---\n\n")
        if "error" not in dcf_result:
            f.write(f"  ราคาปัจจุบัน: ${dcf_result['current_price']:,.2f}\n")
            f.write(f"  Market Cap: ${dcf_result['market_cap_B']:,.2f}B\n")
            f.write(f"  Free Cash Flow: ${dcf_result['latest_fcf_B']:,.2f}B\n")
            f.write(f"  Implied Growth: {dcf_result['implied_growth']:.0%}\n")
        else:
            f.write(f"  {dcf_result['error']}\n")

        # คะแนน
        f.write("\n--- Stock Score ---\n\n")
        total = 0
        for criteria, result in scores.items():
            f.write(f"  {criteria:<18} {result['score']:>3}/20  → {result['reason']}\n")
            total += result["score"]
        f.write(f"\n  {'TOTAL':<18} {total:>3}/100\n")

        # AI Report
        f.write("\n--- AI Analysis ---\n\n")
        f.write(ai_report)
        f.write("\n")

    return filename

# ==========================================
#  ส่วนที่ 7: Main Program
# ==========================================

def analyze(symbol):
    """วิเคราะห์หุ้น 1 ตัวครบวงจร"""
    print(f"\n{'=' * 60}")
    print(f"  กำลังวิเคราะห์: {symbol}")
    print(f"{'=' * 60}\n")

    # ขั้น 1: ดึงข้อมูลพื้นฐาน
    print("  [1/5] ดึงข้อมูลพื้นฐาน...")
    stock_data, ticker, info = fetch_stock_data(symbol)
    print(f"        ✅ {stock_data['ชื่อบริษัท']}")

    # ขั้น 2: ดึงงบการเงิน
    print("  [2/5] ดึงงบการเงิน...")
    metrics = fetch_financials(ticker)
    print(f"        ✅ ได้ข้อมูล {len(metrics)} ปี")

    # ขั้น 3: Reverse DCF
    print("  [3/5] คำนวณ Reverse DCF...")
    dcf_result = reverse_dcf(info, metrics)
    if "error" not in dcf_result:
        print(f"        ✅ Implied Growth: {dcf_result['implied_growth']:.0%}")
    else:
        print(f"        ⚠️ {dcf_result['error']}")

    # ขั้น 4: Scoring
    print("  [4/5] ให้คะแนน...")
    scores = score_stock(info, dcf_result)
    total = sum(s["score"] for s in scores.values())
    print(f"        ✅ Score: {total}/100")

    # ขั้น 5: AI Report
    print("  [5/5] AI กำลังเขียนรายงาน...")
    ai_report = generate_report(symbol, stock_data, metrics, dcf_result, scores)
    print(f"        ✅ รายงานเสร็จแล้ว")

    # บันทึกไฟล์
    filename = save_report(symbol, stock_data, metrics, dcf_result, scores, ai_report)
    print(f"\n  📄 บันทึกรายงานที่: {filename}")

    # แสดงผลสรุป
    print(f"\n  --- สรุปเร็ว ---")
    print(f"  ราคา: ${stock_data['ราคาปัจจุบัน']}")
    print(f"  Score: {total}/100")
    for k, v in scores.items():
        print(f"    {k}: {v['score']}/20")

    return filename


# ==========================================
#  เริ่มโปรแกรม
# ==========================================

if __name__ == "__main__":
    watchlist = ["MSFT", "NVDA", "META", "SOFI", "AMKR"]

    # สร้างกราฟเปรียบเทียบ
    print("=== สร้างกราฟเปรียบเทียบ ===\n")
    plot_comparison(watchlist)

    # หาจุดซื้อทุกตัว
    print(f"\n{'=' * 60}")
    print(f"  🎯 Technical Buy Signals")
    print(f"{'=' * 60}")

    for symbol in watchlist:
        try:
            signals = find_buy_signals(symbol)

            print(f"\n  --- {symbol} ---")
            print(f"  ราคา:      ${signals['current_price']:.2f}")
            print(f"  52W Range: ${signals['low_52w']:.2f} — ${signals['high_52w']:.2f}")
            print(f"  ตำแหน่ง:   {signals['position_52w']:.0f}%")
            print(f"  SMA 50:    ${signals['sma50']:.2f}")
            print(f"  SMA 200:   ${signals['sma200']:.2f}")

            if signals["signals"]:
                for s in signals["signals"]:
                    print(f"  → {s}")
            else:
                print(f"  → ไม่มีสัญญาณพิเศษ")

        except Exception as e:
            print(f"\n  --- {symbol} ---")
            print(f"  ❌ Error: {e}")

    # สร้างกราฟรายตัว (เฉพาะ Top 3)
    print(f"\n{'=' * 60}")
    print(f"  📈 สร้างกราฟรายตัว (Top 3)")
    print(f"{'=' * 60}\n")

    for symbol in watchlist[:3]:
        history = fetch_price_history(symbol)
        plot_price_chart(symbol, history)

