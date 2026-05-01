import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yfinance as yf
import pandas as pd


# ==========================================
#  เกณฑ์ที่ 1: Fundamentals (0-10)
# ==========================================

def check_fundamentals(ticker):
    """เช็คพื้นฐาน: Revenue Growth, FCF, Margin, Debt, Profitability"""
    try:
        info = yf.Ticker(ticker).info
        score = 0
        details = {}

        # 1. Revenue Growth > 10%
        growth = info.get("revenueGrowth", 0) or 0
        details["revenue_growth"] = growth
        if growth > 0.25:
            score += 2.5
        elif growth > 0.10:
            score += 2
        elif growth > 0.05:
            score += 1
        
        # 2. Profitable (Net Income > 0)
        margin = info.get("profitMargins", 0) or 0
        details["profit_margin"] = margin
        if margin > 0.20:
            score += 2.5
        elif margin > 0.10:
            score += 2
        elif margin > 0:
            score += 1

        # 3. FCF > 0
        fcf = info.get("freeCashflow", 0) or 0
        details["fcf"] = fcf
        if fcf > 0:
            score += 2
        else:
            score += 0

        # 4. Debt/Equity < 100
        de = info.get("debtToEquity", 999) or 999
        details["debt_to_equity"] = de
        if de < 30:
            score += 2
        elif de < 60:
            score += 1.5
        elif de < 100:
            score += 1

        # 5. ROE > 10%
        roe = info.get("returnOnEquity", 0) or 0
        details["roe"] = roe
        if roe > 0.20:
            score += 1
        elif roe > 0.10:
            score += 0.5

        return {
            "score": round(min(score, 10), 1),
            "details": details,
            "passed": score >= 5,
        }

    except Exception as e:
        return {"score": 0, "details": {"error": str(e)}, "passed": False}


# ==========================================
#  เกณฑ์ที่ 2: Volatility (0-10)
# ==========================================

def check_volatility(ticker):
    """เช็ค Volatility: Beta, ATR%, Max Drawdown"""
    try:
        tk = yf.Ticker(ticker)
        info = tk.info
        history = tk.history(period="1y")

        score = 0
        details = {}

        # 1. Beta (1.0-1.8 = ideal)
        beta = info.get("beta", None)
        details["beta"] = beta
        if beta is not None:
            if 0.8 <= beta <= 1.8:
                score += 3
            elif 0.5 <= beta <= 2.5:
                score += 2
            else:
                score += 1

        # 2. ATR % (Average True Range as % of price)
        if not history.empty:
            high = history["High"]
            low = history["Low"]
            close = history["Close"]
            tr = (high - low).rolling(14).mean()
            atr_pct = (tr / close).iloc[-1] * 100

            details["atr_pct"] = round(atr_pct, 2)
            if 1 <= atr_pct <= 3:
                score += 4
            elif atr_pct < 1:
                score += 3  # ผันผวนน้อยเกิน อาจไม่มี Upside
            elif atr_pct <= 5:
                score += 2
            else:
                score += 1  # ผันผวนสูงมาก

        # 3. Max Drawdown (52 weeks)
        if not history.empty:
            rolling_max = history["Close"].cummax()
            drawdown = (history["Close"] / rolling_max - 1) * 100
            max_dd = drawdown.min()

            details["max_drawdown"] = round(max_dd, 1)
            if max_dd > -15:
                score += 3
            elif max_dd > -25:
                score += 2
            elif max_dd > -40:
                score += 1

        return {
            "score": round(min(score, 10), 1),
            "details": details,
            "passed": score >= 5,
        }

    except Exception as e:
        return {"score": 0, "details": {"error": str(e)}, "passed": False}


# ==========================================
#  เกณฑ์ที่ 3: Trend (0-10)
# ==========================================

def check_trend(ticker):
    """เช็คแนวโน้ม: MA50>MA200, Higher Highs, RS vs SPY"""
    try:
        tk = yf.Ticker(ticker)
        history = tk.history(period="2y")

        score = 0
        details = {}

        if history.empty or len(history) < 200:
            return {"score": 0, "details": {"error": "ข้อมูลไม่พอ"}, "passed": False}

        close = history["Close"]

        # 1. Price > MA200
        ma200 = close.rolling(200).mean().iloc[-1]
        current = close.iloc[-1]
        details["price_vs_ma200"] = round((current / ma200 - 1) * 100, 1)
        if current > ma200:
            score += 3

        # 2. MA50 > MA200 (Golden Cross)
        ma50 = close.rolling(50).mean().iloc[-1]
        details["golden_cross"] = ma50 > ma200
        if ma50 > ma200:
            score += 3

        # 3. Relative Strength vs SPY (6 months)
        spy = yf.Ticker("SPY").history(period="6mo")
        stock_6m = tk.history(period="6mo")

        if not spy.empty and not stock_6m.empty:
            spy_return = (spy["Close"].iloc[-1] / spy["Close"].iloc[0] - 1) * 100
            stock_return = (stock_6m["Close"].iloc[-1] / stock_6m["Close"].iloc[0] - 1) * 100
            rs = stock_return - spy_return

            details["rs_vs_spy"] = round(rs, 1)
            details["stock_6m_return"] = round(stock_return, 1)
            details["spy_6m_return"] = round(spy_return, 1)

            if rs > 10:
                score += 4
            elif rs > 0:
                score += 3
            elif rs > -10:
                score += 1

        return {
            "score": round(min(score, 10), 1),
            "details": details,
            "passed": score >= 5,
        }

    except Exception as e:
        return {"score": 0, "details": {"error": str(e)}, "passed": False}


# ==========================================
#  เกณฑ์ที่ 4: Liquidity (0-10)
# ==========================================

def check_liquidity(ticker):
    """เช็คสภาพคล่อง: Volume, Market Cap"""
    try:
        info = yf.Ticker(ticker).info

        score = 0
        details = {}

        # 1. Market Cap > $5B
        mcap = info.get("marketCap", 0) or 0
        mcap_b = mcap / 1e9
        details["market_cap_B"] = round(mcap_b, 2)

        if mcap_b > 100:
            score += 5  # Mega Cap
        elif mcap_b > 20:
            score += 4  # Large Cap
        elif mcap_b > 5:
            score += 3  # Mid-Large Cap
        elif mcap_b > 1:
            score += 2  # Mid Cap
        else:
            score += 1  # Small Cap

        # 2. Average Volume
        avg_vol = info.get("averageVolume", 0) or 0
        current_price = info.get("currentPrice", 0) or 0
        daily_dollar_vol = avg_vol * current_price / 1e6  # in millions

        details["avg_daily_vol_M"] = round(daily_dollar_vol, 1)

        if daily_dollar_vol > 500:
            score += 5
        elif daily_dollar_vol > 100:
            score += 4
        elif daily_dollar_vol > 50:
            score += 3
        elif daily_dollar_vol > 10:
            score += 2
        else:
            score += 1

        return {
            "score": round(min(score, 10), 1),
            "details": details,
            "passed": score >= 5,
        }

    except Exception as e:
        return {"score": 0, "details": {"error": str(e)}, "passed": False}


# ==========================================
#  เกณฑ์ที่ 5: Sector Tailwind (0-10)
# ==========================================

SECTOR_SCORES = {
    "AI_INFRA": 10,
    "SEMIS": 9,
    "CLOUD": 9,
    "AI_BENEFICIARY": 9,
    "CYBER": 8,
    "HEALTH_TECH": 8,
    "FINTECH": 7,
    "PHARMA": 7,
    "GLP1": 9,
    "PAYMENTS": 7,
    "SOFTWARE": 7,
    "TECH_MEGA": 8,
    "RENEWABLES": 7,
    "EV": 6,
    "AD_DEPENDENT": 6,
    "BANKS": 5,
    "OIL_GAS": 4,
    "CONSUMER_TECH": 6,
    "CRYPTO": 5,
    "BITCOIN_PROXY": 5,
    "HEALTH_INSURANCE": 6,
    "OTHER": 5,
}

def check_sector_tailwind(ticker):
    """เช็คว่า Sector มีแนวโน้มระยะยาวดีไหม"""
    try:
        from portfolio.sector_classifier import get_correlation_groups

        groups = get_correlation_groups(ticker)
        details = {"groups": groups}

        if not groups:
            return {"score": 5, "details": details, "passed": True}

        # ใช้คะแนนสูงสุดจากทุก Group
        best_score = max(SECTOR_SCORES.get(g, 5) for g in groups)
        details["best_group"] = max(groups, key=lambda g: SECTOR_SCORES.get(g, 5))
        details["sector_score"] = best_score

        return {
            "score": best_score,
            "details": details,
            "passed": best_score >= 5,
        }

    except Exception as e:
        return {"score": 5, "details": {"error": str(e)}, "passed": True}
if __name__ == "__main__":
    test_ticker = "NVDA"
    print(f"=== Quality Screen: {test_ticker} ===\n")

    print("  [1/5] Fundamentals...")
    f = check_fundamentals(test_ticker)
    print(f"         Score: {f['score']}/10 {'✅' if f['passed'] else '❌'}")

    print("  [2/5] Volatility...")
    v = check_volatility(test_ticker)
    print(f"         Score: {v['score']}/10 {'✅' if v['passed'] else '❌'}")

    print("  [3/5] Trend...")
    t = check_trend(test_ticker)
    print(f"         Score: {t['score']}/10 {'✅' if t['passed'] else '❌'}")

    print("  [4/5] Liquidity...")
    l = check_liquidity(test_ticker)
    print(f"         Score: {l['score']}/10 {'✅' if l['passed'] else '❌'}")

    print("  [5/5] Sector Tailwind...")
    s = check_sector_tailwind(test_ticker)
    print(f"         Score: {s['score']}/10 {'✅' if s['passed'] else '❌'}")

    total = f['score'] + v['score'] + t['score'] + l['score'] + s['score']
    avg = total / 5
    print(f"\n  Total: {total}/50 (Avg: {avg:.1f}/10)")