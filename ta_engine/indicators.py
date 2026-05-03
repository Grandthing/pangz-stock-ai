import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yfinance as yf
import pandas as pd
from ta.trend import SMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
from dataclasses import dataclass
from typing import Dict


# ==========================================
#  Data Classes
# ==========================================

@dataclass
class IndicatorResult:
    """ผลลัพธ์ของ Indicator แต่ละตัว"""
    name: str
    values: Dict
    interpretation: str    # 'bullish', 'bearish', 'neutral'
    detail: str


# ==========================================
#  Data Fetcher
# ==========================================

def fetch_ohlcv(ticker: str, period: str = "1y") -> pd.DataFrame:
    """ดึงข้อมูล OHLCV จาก Yahoo Finance"""
    tk = yf.Ticker(ticker)
    df = tk.history(period=period)

    if df.empty:
        raise ValueError(f"ไม่พบข้อมูลของ {ticker}")

    return df


# ==========================================
#  SMA — Simple Moving Average
# ==========================================

def calculate_sma(df: pd.DataFrame, periods: list = [50, 100, 200]) -> Dict[str, IndicatorResult]:
    """คำนวณ SMA หลาย period พร้อม slope detection"""
    results = {}
    current_price = round(float(df["Close"].iloc[-1]), 2)

    for period in periods:
        col_name = f"SMA_{period}"

        if len(df) < period:
            results[col_name] = IndicatorResult(
                name=col_name,
                values={"current": None},
                interpretation="neutral",
                detail=f"ข้อมูลไม่พอสำหรับ SMA {period}"
            )
            continue

        # คำนวณ SMA ด้วย ta library
        sma_indicator = SMAIndicator(close=df["Close"], window=period)
        sma_series = sma_indicator.sma_indicator()
        current_sma = round(float(sma_series.iloc[-1]), 2)

        # Slope: เทียบ SMA วันนี้กับ 30 วันก่อน
        sma_clean = sma_series.dropna()
        if len(sma_clean) > 30:
            sma_30d_ago = float(sma_clean.iloc[-30])
            slope_pct = round(((current_sma / sma_30d_ago) - 1) * 100, 2)
        else:
            slope_pct = 0.0

        # Distance: ราคาห่างจาก SMA กี่ %
        distance_pct = round(((current_price / current_sma) - 1) * 100, 2)

        # ตีความ
        if current_price > current_sma and slope_pct > 0:
            interpretation = "bullish"
            detail = f"ราคา ${current_price} อยู่เหนือ {col_name} ${current_sma} (+{distance_pct}%) เส้นชี้ขึ้น"
        elif current_price > current_sma and slope_pct <= 0:
            interpretation = "neutral"
            detail = f"ราคาอยู่เหนือ {col_name} ${current_sma} แต่เส้นเริ่มแบน"
        elif current_price < current_sma and slope_pct < 0:
            interpretation = "bearish"
            detail = f"ราคา ${current_price} อยู่ใต้ {col_name} ${current_sma} ({distance_pct}%) เส้นชี้ลง"
        else:
            interpretation = "neutral"
            detail = f"ราคาอยู่ใต้ {col_name} ${current_sma} แต่เส้นเริ่มหัวขึ้น"

        results[col_name] = IndicatorResult(
            name=col_name,
            values={
                "current": current_sma,
                "price": current_price,
                "slope_pct": slope_pct,
                "distance_pct": distance_pct,
            },
            interpretation=interpretation,
            detail=detail,
        )

    return results


# ==========================================
#  RSI — Relative Strength Index
# ==========================================

def calculate_rsi(df: pd.DataFrame, period: int = 14) -> IndicatorResult:
    """RSI + Zone Detection"""

    rsi_indicator = RSIIndicator(close=df["Close"], window=period)
    rsi_series = rsi_indicator.rsi()

    current_rsi = round(float(rsi_series.iloc[-1]), 2)
    prev_rsi = round(float(rsi_series.iloc[-2]), 2)

    # Zone Detection
    if current_rsi >= 70:
        interpretation = "bearish"
        detail = f"RSI {current_rsi} → Overbought (เกิน 70) อาจปรับฐาน"
    elif current_rsi <= 30:
        interpretation = "bullish"
        detail = f"RSI {current_rsi} → Oversold (ต่ำกว่า 30) อาจเด้งกลับ"
    elif current_rsi >= 60:
        interpretation = "bullish"
        detail = f"RSI {current_rsi} → โซนแข็งแกร่ง แรงซื้อยังมี"
    elif current_rsi <= 40:
        interpretation = "bearish"
        detail = f"RSI {current_rsi} → โซนอ่อนแอ แรงขายยังมี"
    else:
        interpretation = "neutral"
        detail = f"RSI {current_rsi} → โซนกลาง ไม่มีสัญญาณชัดเจน"

    # แนวโน้ม RSI
    if current_rsi > prev_rsi:
        detail += f" (RSI เพิ่มขึ้นจาก {prev_rsi})"
    else:
        detail += f" (RSI ลดลงจาก {prev_rsi})"

    return IndicatorResult(
        name="RSI",
        values={
            "current": current_rsi,
            "previous": prev_rsi,
            "direction": "up" if current_rsi > prev_rsi else "down",
        },
        interpretation=interpretation,
        detail=detail,
    )


# ==========================================
#  MACD
# ==========================================

def calculate_macd(df: pd.DataFrame) -> IndicatorResult:
    """MACD + Signal + Histogram"""

    macd_indicator = MACD(close=df["Close"], window_slow=26, window_fast=12, window_sign=9)

    macd_val = round(float(macd_indicator.macd().iloc[-1]), 4)
    signal_val = round(float(macd_indicator.macd_signal().iloc[-1]), 4)
    hist_val = round(float(macd_indicator.macd_diff().iloc[-1]), 4)
    prev_hist = round(float(macd_indicator.macd_diff().iloc[-2]), 4)

    # Crossover Detection
    cross_up = prev_hist <= 0 and hist_val > 0
    cross_down = prev_hist >= 0 and hist_val < 0

    # ตีความ
    if macd_val > signal_val and hist_val > prev_hist:
        interpretation = "bullish"
        detail = f"MACD ({macd_val:.2f}) > Signal ({signal_val:.2f}) Histogram เพิ่มขึ้น → แรงซื้อแข็ง"
    elif macd_val > signal_val:
        interpretation = "bullish"
        detail = f"MACD > Signal แต่ Histogram เริ่มลด → แรงซื้อชะลอ"
    elif macd_val < signal_val and hist_val < prev_hist:
        interpretation = "bearish"
        detail = f"MACD ({macd_val:.2f}) < Signal ({signal_val:.2f}) Histogram ลดลง → แรงขายแข็ง"
    elif macd_val < signal_val:
        interpretation = "bearish"
        detail = f"MACD < Signal แต่ Histogram เริ่มเพิ่ม → แรงขายชะลอ อาจกลับตัว"
    else:
        interpretation = "neutral"
        detail = f"MACD ≈ Signal → รอสัญญาณ Crossover"

    if cross_up:
        detail += " | เพิ่งเกิด Bullish Crossover!"
    elif cross_down:
        detail += " | เพิ่งเกิด Bearish Crossover!"

    return IndicatorResult(
        name="MACD",
        values={
            "macd": macd_val,
            "signal": signal_val,
            "histogram": hist_val,
            "prev_histogram": prev_hist,
            "hist_increasing": hist_val > prev_hist,
            "cross_up": cross_up,
            "cross_down": cross_down,
        },
        interpretation=interpretation,
        detail=detail,
    )


# ==========================================
#  Bollinger Bands
# ==========================================

def calculate_bollinger(df: pd.DataFrame, period: int = 20) -> IndicatorResult:
    """Bollinger Bands + Squeeze Detection"""

    bb = BollingerBands(close=df["Close"], window=period, window_dev=2)

    upper = round(float(bb.bollinger_hband().iloc[-1]), 2)
    middle = round(float(bb.bollinger_mavg().iloc[-1]), 2)
    lower = round(float(bb.bollinger_lband().iloc[-1]), 2)
    current_price = round(float(df["Close"].iloc[-1]), 2)

    # %B Position
    pct_b_series = bb.bollinger_pband()
    pct_b = round(float(pct_b_series.iloc[-1]) * 100, 1)

    # Bandwidth + Squeeze
    bw_series = bb.bollinger_wband()
    current_bw = float(bw_series.iloc[-1])
    avg_bw = float(bw_series.tail(50).mean())
    is_squeeze = current_bw < avg_bw * 0.8
    bandwidth = round(current_bw * 100, 2)

    # ตีความ
    if current_price > upper:
        interpretation = "bearish"
        detail = f"ราคา ${current_price} ทะลุ Upper Band ${upper} → Overbought"
    elif current_price < lower:
        interpretation = "bullish"
        detail = f"ราคา ${current_price} หลุด Lower Band ${lower} → Oversold"
    elif pct_b > 80:
        interpretation = "neutral"
        detail = f"ราคาใกล้ Upper Band (%B={pct_b}%) → ระวังแรงขาย"
    elif pct_b < 20:
        interpretation = "neutral"
        detail = f"ราคาใกล้ Lower Band (%B={pct_b}%) → อาจมีแรงซื้อ"
    else:
        interpretation = "neutral"
        detail = f"ราคาอยู่กลาง Band (%B={pct_b}%)"

    if is_squeeze:
        detail += " | ⚡ Bollinger Squeeze! Band แคบมาก อาจระเบิดเร็วๆ นี้"

    return IndicatorResult(
        name="Bollinger",
        values={
            "upper": upper,
            "middle": middle,
            "lower": lower,
            "bandwidth": bandwidth,
            "pct_b": pct_b,
            "is_squeeze": is_squeeze,
        },
        interpretation=interpretation,
        detail=detail,
    )


# ==========================================
#  Volume Context
# ==========================================

def calculate_volume(df: pd.DataFrame) -> IndicatorResult:
    """Volume เทียบค่าเฉลี่ย 20 วัน"""

    current_vol = int(df["Volume"].iloc[-1])
    avg_vol_20 = int(df["Volume"].tail(20).mean())
    ratio = round(current_vol / avg_vol_20, 2) if avg_vol_20 > 0 else 0

    price_change = float(df["Close"].iloc[-1]) - float(df["Close"].iloc[-2])
    price_change_pct = round((price_change / float(df["Close"].iloc[-2])) * 100, 2)

    if ratio > 1.5 and price_change > 0:
        interpretation = "bullish"
        detail = f"Volume สูง {ratio:.1f}x + ราคาขึ้น → แรงซื้อหนัก"
    elif ratio > 1.5 and price_change < 0:
        interpretation = "bearish"
        detail = f"Volume สูง {ratio:.1f}x + ราคาลง → แรงขายหนัก"
    elif ratio < 0.5:
        interpretation = "neutral"
        detail = f"Volume ต่ำมาก ({ratio:.1f}x) → ตลาดเงียบ"
    else:
        interpretation = "neutral"
        detail = f"Volume ปกติ ({ratio:.1f}x ของเฉลี่ย 20 วัน)"

    return IndicatorResult(
        name="Volume",
        values={
            "current": current_vol,
            "avg_20d": avg_vol_20,
            "ratio": ratio,
            "price_change_pct": price_change_pct,
        },
        interpretation=interpretation,
        detail=detail,
    )


# ==========================================
#  Fibonacci Auto-Detection
# ==========================================

def calculate_fibonacci(df: pd.DataFrame, lookback_days: int = 90) -> IndicatorResult:
    """หา Swing High/Low อัตโนมัติ + คำนวณ Fibonacci Levels"""

    # ใช้ข้อมูลย้อนหลังตาม lookback
    recent = df.tail(lookback_days)
    current_price = round(float(df["Close"].iloc[-1]), 2)

    # หา Swing High & Swing Low
    swing_high = round(float(recent["High"].max()), 2)
    swing_low = round(float(recent["Low"].min()), 2)
    swing_high_date = recent["High"].idxmax().strftime("%Y-%m-%d")
    swing_low_date = recent["Low"].idxmin().strftime("%Y-%m-%d")

    # ตรวจว่า Swing มากพอไหม (อย่างน้อย 10%)
    swing_range = swing_high - swing_low
    swing_pct = round((swing_range / swing_low) * 100, 1)

    if swing_pct < 5:
        return IndicatorResult(
            name="Fibonacci",
            values={"error": "Swing range น้อยกว่า 5% ไม่มี Signal ชัดเจน"},
            interpretation="neutral",
            detail="ราคาเคลื่อนไหวน้อยเกินกว่าจะหา Fibonacci ได้"
        )

    # กำหนดทิศทาง
    high_idx = recent["High"].idxmax()
    low_idx = recent["Low"].idxmin()
    direction = "downtrend" if high_idx < low_idx else "uptrend"

    # Fibonacci Retracement Levels
    fib_ratios = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
    fib_labels = ["0%", "23.6%", "38.2%", "50%", "61.8%", "78.6%", "100%"]

    # Extension Levels
    ext_ratios = [1.272, 1.618, 2.0, 2.618]
    ext_labels = ["127.2%", "161.8%", "200%", "261.8%"]

    levels = []

    if direction == "downtrend":
        # Retracement ขาลง: วัดจาก High ลง Low
        for ratio, label in zip(fib_ratios, fib_labels):
            price = round(swing_low + (swing_range * ratio), 2)
            dist = round(((price / current_price) - 1) * 100, 2)
            role = "SUP" if price < current_price else "RES"
            levels.append({
                "label": label,
                "price": price,
                "distance_pct": dist,
                "role": role,
                "is_extension": False,
            })

        # Extensions
        for ratio, label in zip(ext_ratios, ext_labels):
            price = round(swing_high + (swing_range * (ratio - 1)), 2)
            dist = round(((price / current_price) - 1) * 100, 2)
            levels.append({
                "label": label,
                "price": price,
                "distance_pct": dist,
                "role": "RES",
                "is_extension": True,
            })
    else:
        # Retracement ขาขึ้น: วัดจาก Low ขึ้น High
        for ratio, label in zip(fib_ratios, fib_labels):
            price = round(swing_high - (swing_range * ratio), 2)
            dist = round(((price / current_price) - 1) * 100, 2)
            role = "SUP" if price < current_price else "RES"
            levels.append({
                "label": label,
                "price": price,
                "distance_pct": dist,
                "role": role,
                "is_extension": False,
            })

        # Extensions
        for ratio, label in zip(ext_ratios, ext_labels):
            price = round(swing_low - (swing_range * (ratio - 1)), 2)
            dist = round(((price / current_price) - 1) * 100, 2)
            levels.append({
                "label": label,
                "price": price,
                "distance_pct": dist,
                "role": "SUP",
                "is_extension": True,
            })

    # หา Current Zone
    retracement_levels = [l for l in levels if not l["is_extension"]]
    current_zone = "above_all"
    for i in range(len(retracement_levels) - 1):
        upper = retracement_levels[i]["price"]
        lower = retracement_levels[i + 1]["price"]
        high_p = max(upper, lower)
        low_p = min(upper, lower)
        if low_p <= current_price <= high_p:
            current_zone = f"between_{retracement_levels[i]['label']}_and_{retracement_levels[i+1]['label']}"
            break

    # ตีความ
    if direction == "downtrend":
        detail = f"ขาลง: Swing High ${swing_high} ({swing_high_date}) → Low ${swing_low} ({swing_low_date}) | ราคาอยู่ Zone {current_zone}"
    else:
        detail = f"ขาขึ้น: Swing Low ${swing_low} ({swing_low_date}) → High ${swing_high} ({swing_high_date}) | ราคาอยู่ Zone {current_zone}"

    # หา Support/Resistance ที่ใกล้ที่สุด
    supports = [l for l in levels if l["role"] == "SUP" and not l["is_extension"]]
    resistances = [l for l in levels if l["role"] == "RES" and not l["is_extension"]]

    nearest_sup = min(supports, key=lambda x: abs(x["distance_pct"])) if supports else None
    nearest_res = min(resistances, key=lambda x: abs(x["distance_pct"])) if resistances else None

    if nearest_sup:
        detail += f" | Support ใกล้สุด: ${nearest_sup['price']} ({nearest_sup['label']})"
    if nearest_res:
        detail += f" | Resistance ใกล้สุด: ${nearest_res['price']} ({nearest_res['label']})"

    interpretation = "bearish" if direction == "downtrend" else "bullish"

    return IndicatorResult(
        name="Fibonacci",
        values={
            "swing_high": swing_high,
            "swing_high_date": swing_high_date,
            "swing_low": swing_low,
            "swing_low_date": swing_low_date,
            "direction": direction,
            "swing_pct": swing_pct,
            "current_zone": current_zone,
            "levels": levels,
            "nearest_support": nearest_sup,
            "nearest_resistance": nearest_res,
        },
        interpretation=interpretation,
        detail=detail,
    )


# ==========================================
#  Master Function: รวมทุก Indicator
# ==========================================

def get_all_indicators(ticker: str, period: str = "1y") -> dict:
    """ดึงข้อมูล + คำนวณทุก Indicator"""

    df = fetch_ohlcv(ticker, period)
    current_price = round(float(df["Close"].iloc[-1]), 2)
    prev_price = round(float(df["Close"].iloc[-2]), 2)
    change_pct = round(((current_price / prev_price) - 1) * 100, 2)

    sma = calculate_sma(df)
    rsi = calculate_rsi(df)
    macd = calculate_macd(df)
    bb = calculate_bollinger(df)
    vol = calculate_volume(df)
    fib = calculate_fibonacci(df)
    # TD Sequential
    from ta_engine.td_sequential import analyze_td_sequential
    td = analyze_td_sequential(df)

    # Overall Score
    signals = [
        sma.get("SMA_200", IndicatorResult("", {}, "neutral", "")).interpretation,
        rsi.interpretation,
        macd.interpretation,
        bb.interpretation,
        vol.interpretation,
    ]

    bullish_count = signals.count("bullish")
    bearish_count = signals.count("bearish")

    if bullish_count >= 3:
        overall = "BULLISH"
    elif bearish_count >= 3:
        overall = "BEARISH"
    else:
        overall = "NEUTRAL"

    return {
        "ticker": ticker,
        "current_price": current_price,
        "change_pct": change_pct,
        "overall": overall,
        "bullish_count": bullish_count,
        "bearish_count": bearish_count,
        "sma": sma,
        "rsi": rsi,
        "macd": macd,
        "bb": bb,
        "volume": vol,
       "fibonacci": fib,
        "td_sequential": td,
        "df": df,
    }


# ==========================================
#  Test
# ==========================================

if __name__ == "__main__":
    ticker = "META"
    print(f"{'=' * 60}")
    print(f"  📊 Technical Indicators: {ticker}")
    print(f"{'=' * 60}\n")

    result = get_all_indicators(ticker)

    print(f"  ราคาปัจจุบัน: ${result['current_price']} ({result['change_pct']:+.2f}%)")
    print(f"  Overall: {result['overall']} (Bull: {result['bullish_count']}, Bear: {result['bearish_count']})")

    # SMA
    print(f"\n  --- SMA ---")
    for name, sma in result["sma"].items():
        icon = "🟢" if sma.interpretation == "bullish" else "🔴" if sma.interpretation == "bearish" else "⚪"
        print(f"  {icon} {sma.detail}")

    # RSI
    rsi = result["rsi"]
    icon = "🟢" if rsi.interpretation == "bullish" else "🔴" if rsi.interpretation == "bearish" else "⚪"
    print(f"\n  --- RSI ---")
    print(f"  {icon} {rsi.detail}")

    # MACD
    macd = result["macd"]
    icon = "🟢" if macd.interpretation == "bullish" else "🔴" if macd.interpretation == "bearish" else "⚪"
    print(f"\n  --- MACD ---")
    print(f"  {icon} {macd.detail}")

    # Bollinger
    bb = result["bb"]
    icon = "🟢" if bb.interpretation == "bullish" else "🔴" if bb.interpretation == "bearish" else "⚪"
    print(f"\n  --- Bollinger Bands ---")
    print(f"  {icon} {bb.detail}")
    print(f"      Upper: ${bb.values['upper']} | Mid: ${bb.values['middle']} | Lower: ${bb.values['lower']}")

    # Volume
    vol = result["volume"]
    icon = "🟢" if vol.interpretation == "bullish" else "🔴" if vol.interpretation == "bearish" else "⚪"
    print(f"\n  --- Volume ---")
    print(f"  {icon} {vol.detail}")

    # Fibonacci
    fib = result["fibonacci"]
    icon = "🟢" if fib.interpretation == "bullish" else "🔴" if fib.interpretation == "bearish" else "⚪"
    print(f"\n  --- Fibonacci ---")
    print(f"  {icon} {fib.detail}")

    if "levels" in fib.values:
        print(f"\n  📐 Fibonacci Levels:")
        print(f"  {'Level':<10} {'Price':>10} {'Dist%':>8} {'Role':>5}")
        print(f"  {'-' * 35}")
        for level in fib.values["levels"]:
            ext = " (Ext)" if level["is_extension"] else ""
            print(f"  {level['label']:<10} ${level['price']:>9.2f} {level['distance_pct']:>7.1f}% {level['role']:>5}{ext}")