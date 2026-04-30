import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import os  # === เพิ่ม import os ตรงนี้ ===

def fetch_price_history(symbol, period="2y"):
    """ดึงราคาหุ้นย้อนหลัง"""
    ticker = yf.Ticker(symbol)
    history = ticker.history(period=period)

    print(f"  ดึงราคา {symbol} ย้อนหลัง {period}")
    print(f"  ข้อมูล {len(history)} วัน")
    print(f"  ตั้งแต่ {history.index[0].strftime('%Y-%m-%d')}")
    print(f"  ถึง     {history.index[-1].strftime('%Y-%m-%d')}")

    return history

def plot_price_chart(symbol, history):
    """สร้างกราฟราคาหุ้น + Moving Average"""

    # คำนวณ Moving Average
    history["SMA50"] = history["Close"].rolling(window=50).mean()
    history["SMA200"] = history["Close"].rolling(window=200).mean()

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8),
                                     gridspec_kw={"height_ratios": [3, 1]})

    # --- กราฟบน: ราคา + MA ---
    ax1.plot(history.index, history["Close"],
             color="royalblue", linewidth=1.5, label="Price")
    ax1.plot(history.index, history["SMA50"],
             color="orange", linewidth=1, label="SMA 50", linestyle="--")
    ax1.plot(history.index, history["SMA200"],
             color="red", linewidth=1, label="SMA 200", linestyle="--")

    # ราคาปัจจุบัน
    current_price = history["Close"].iloc[-1]
    sma50 = history["SMA50"].iloc[-1]
    sma200 = history["SMA200"].iloc[-1]

    ax1.axhline(y=current_price, color="gray", linewidth=0.5, linestyle=":")
    ax1.set_title(f"{symbol} — ${current_price:.2f}", fontsize=16, fontweight="bold")
    ax1.set_ylabel("Price (USD)")
    ax1.legend(loc="upper left")
    ax1.grid(True, alpha=0.3)

    # --- กราฟล่าง: Volume ---
    ax2.bar(history.index, history["Volume"], color="steelblue", alpha=0.5)
    ax2.set_ylabel("Volume")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()

    # บันทึก
    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"reports/{symbol}_chart_{today}.png"
    plt.savefig(filename, dpi=150, bbox_inches="tight")
    plt.close()

    # สรุปสถานะ
    print(f"\n  📈 Chart saved: {filename}")
    print(f"  ราคาปัจจุบัน: ${current_price:.2f}")
    print(f"  SMA 50:       ${sma50:.2f}")
    print(f"  SMA 200:      ${sma200:.2f}")

    if current_price > sma200:
        print(f"  แนวโน้ม:      ขาขึ้น (ราคาอยู่เหนือ SMA 200)")
    else:
        print(f"  แนวโน้ม:      ขาลง (ราคาอยู่ใต้ SMA 200)")

    if sma50 > sma200:
        print(f"  สัญญาณ:       Golden Cross (SMA50 > SMA200)")
    else:
        print(f"  สัญญาณ:       Death Cross (SMA50 < SMA200)")

    return filename

def plot_comparison(symbols, period="1y"):
    """เปรียบเทียบราคาหุ้นหลายตัว (Normalized)"""

    fig, ax = plt.subplots(figsize=(12, 6))

    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            history = ticker.history(period=period)

            # Normalize: เปลี่ยนราคาเป็น % เทียบกับวันแรก
            first_price = history["Close"].iloc[0]
            normalized = (history["Close"] / first_price - 1) * 100

            ax.plot(history.index, normalized, linewidth=1.5, label=symbol)
        except Exception as e:
            print(f"  ❌ {symbol}: {e}")

    ax.axhline(y=0, color="gray", linewidth=0.5, linestyle=":")
    ax.set_title(f"Stock Comparison ({period})", fontsize=16, fontweight="bold")
    ax.set_ylabel("Return (%)")
    ax.legend()
    ax.grid(True, alpha=0.3)

    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"reports/comparison_{today}.png"
    plt.savefig(filename, dpi=150, bbox_inches="tight")
    plt.close()

    print(f"\n  📊 Comparison chart saved: {filename}")
    return filename

def find_buy_signals(symbol, period="2y"):
    """หาจุดซื้อจาก Technical Analysis"""

    ticker = yf.Ticker(symbol)
    history = ticker.history(period=period)

    # คำนวณ MA
    history["SMA50"] = history["Close"].rolling(50).mean()
    history["SMA200"] = history["Close"].rolling(200).mean()

    # ค่าล่าสุด
    current = history["Close"].iloc[-1]
    sma50 = history["SMA50"].iloc[-1]
    sma200 = history["SMA200"].iloc[-1]
    high_52w = history["Close"].tail(252).max()
    low_52w = history["Close"].tail(252).min()

    # คำนวณตำแหน่งราคาใน 52 Week Range
    position = (current - low_52w) / (high_52w - low_52w) * 100

    # วิเคราะห์ Technical
    signals = {
        "symbol": symbol,
        "current_price": current,
        "sma50": sma50,
        "sma200": sma200,
        "high_52w": high_52w,
        "low_52w": low_52w,
        "position_52w": position,
        "above_sma200": current > sma200,
        "golden_cross": sma50 > sma200,
        "signals": [],
    }

    # สัญญาณซื้อ
    if current < sma200 * 0.95:
        signals["signals"].append("ราคาต่ำกว่า SMA200 มากกว่า 5% → อาจเป็นจุดซื้อ")

    if position < 30:
        signals["signals"].append(f"ราคาอยู่ใกล้ 52W Low ({position:.0f}%) → น่าสนใจ")

    if sma50 > sma200:
        signals["signals"].append("Golden Cross → แนวโน้มขาขึ้น")

    # สัญญาณเตือน
    if position > 90:
        signals["signals"].append(f"ราคาใกล้ 52W High ({position:.0f}%) → ระวังแพง")

    if current > sma50 * 1.10:
        signals["signals"].append("ราคาสูงกว่า SMA50 มากกว่า 10% → อาจ Overextended")

    if sma50 < sma200:
        signals["signals"].append("Death Cross → แนวโน้มขาลง")

    return signals

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
