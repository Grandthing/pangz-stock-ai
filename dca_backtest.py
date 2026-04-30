import yfinance as yf
import pandas as pd
from datetime import datetime

def dca_backtest(symbol, monthly_amount, period="2y"):
    """จำลอง DCA ย้อนหลัง — ซื้อทุกต้นเดือน"""

    # ดึงราคาย้อนหลัง
    ticker = yf.Ticker(symbol)
    history = ticker.history(period=period)

    # เลือกเฉพาะวันแรกของแต่ละเดือน
    history["YearMonth"] = history.index.to_period("M")
    monthly_prices = history.groupby("YearMonth").first()

    # จำลอง DCA
    total_invested = 0
    total_shares = 0
    records = []

    for month, row in monthly_prices.iterrows():
        price = row["Close"]
        shares_bought = monthly_amount / price
        total_invested += monthly_amount
        total_shares += shares_bought
        current_value = total_shares * price
        profit = current_value - total_invested
        profit_pct = (profit / total_invested) * 100

        records.append({
            "month": str(month),
            "price": round(price, 2),
            "shares_bought": round(shares_bought, 4),
            "total_shares": round(total_shares, 4),
            "total_invested": round(total_invested, 2),
            "current_value": round(current_value, 2),
            "profit": round(profit, 2),
            "profit_pct": round(profit_pct, 2),
        })

    # ราคาปัจจุบัน
    latest_price = history["Close"].iloc[-1]
    final_value = total_shares * latest_price
    final_profit = final_value - total_invested
    final_profit_pct = (final_profit / total_invested) * 100
    avg_cost = total_invested / total_shares

    summary = {
        "symbol": symbol,
        "period": period,
        "monthly_amount": monthly_amount,
        "months": len(records),
        "total_invested": round(total_invested, 2),
        "total_shares": round(total_shares, 4),
        "avg_cost": round(avg_cost, 2),
        "latest_price": round(latest_price, 2),
        "final_value": round(final_value, 2),
        "profit": round(final_profit, 2),
        "profit_pct": round(final_profit_pct, 2),
        "records": records,
    }

    return summary


def lump_sum_backtest(symbol, total_amount, period="2y"):
    """จำลองซื้อครั้งเดียวตั้งแต่วันแรก"""

    ticker = yf.Ticker(symbol)
    history = ticker.history(period=period)

    # ซื้อวันแรก
    first_price = history["Close"].iloc[0]
    shares = total_amount / first_price

    # มูลค่าปัจจุบัน
    latest_price = history["Close"].iloc[-1]
    final_value = shares * latest_price
    profit = final_value - total_amount
    profit_pct = (profit / total_amount) * 100

    return {
        "symbol": symbol,
        "buy_date": history.index[0].strftime("%Y-%m-%d"),
        "buy_price": round(first_price, 2),
        "total_invested": total_amount,
        "shares": round(shares, 4),
        "latest_price": round(latest_price, 2),
        "final_value": round(final_value, 2),
        "profit": round(profit, 2),
        "profit_pct": round(profit_pct, 2),
    }


def compare_strategies(symbol, monthly_amount, period="2y"):
    """เปรียบเทียบ DCA vs Lump Sum"""

    # DCA
    dca = dca_backtest(symbol, monthly_amount, period)

    # Lump Sum ด้วยเงินรวมเท่ากัน
    lump = lump_sum_backtest(symbol, dca["total_invested"], period)

    print(f"\n{'=' * 60}")
    print(f"  ⚔️ DCA vs Lump Sum: {symbol} ({period})")
    print(f"{'=' * 60}\n")

    print(f"  {'':>20} {'DCA':>15} {'Lump Sum':>15}")
    print(f"  {'-' * 50}")
    print(f"  {'ลงทุนรวม':>20} ${dca['total_invested']:>13,.2f} ${lump['total_invested']:>13,.2f}")
    print(f"  {'ต้นทุนเฉลี่ย':>20} ${dca['avg_cost']:>13,.2f} ${lump['buy_price']:>13,.2f}")
    print(f"  {'หุ้นที่ได้':>20} {dca['total_shares']:>13,.4f} {lump['shares']:>13,.4f}")
    print(f"  {'มูลค่าปัจจุบัน':>20} ${dca['final_value']:>13,.2f} ${lump['final_value']:>13,.2f}")
    print(f"  {'กำไร/ขาดทุน':>20} ${dca['profit']:>13,.2f} ${lump['profit']:>13,.2f}")
    print(f"  {'กำไร %':>20} {dca['profit_pct']:>12.1f}% {lump['profit_pct']:>12.1f}%")

    # ใครชนะ?
    if dca["profit"] > lump["profit"]:
        winner = "DCA"
        diff = dca["profit"] - lump["profit"]
    else:
        winner = "Lump Sum"
        diff = lump["profit"] - dca["profit"]

    print(f"\n  🏆 ผู้ชนะ: {winner} (ต่างกัน ${diff:,.2f})")

    return {"dca": dca, "lump": lump, "winner": winner}

import matplotlib.pyplot as plt
import matplotlib as mpl # === 1. เพิ่ม import mpl ===

# === 2. เพิ่มโค้ดตั้งค่าฟอนต์ภาษาไทย (สำหรับ Windows) ===
mpl.rcParams['font.family'] = 'Tahoma' 
# ===============================================

def plot_dca_chart(symbol, dca_result):
    """สร้างกราฟแสดง DCA Growth เทียบกับเงินลงทุน"""

    records = dca_result["records"]

    months = [r["month"] for r in records]
    invested = [r["total_invested"] for r in records]
    values = [r["current_value"] for r in records]

    fig, ax = plt.subplots(figsize=(12, 6))

    # เส้นเงินลงทุนสะสม
    ax.plot(months, invested, color="gray", linewidth=2,
            label="เงินลงทุนสะสม", linestyle="--")

    # เส้นมูลค่าจริง
    ax.fill_between(months, invested, values,
                     where=[v >= i for v, i in zip(values, invested)],
                     color="green", alpha=0.3, label="กำไร")
    ax.fill_between(months, invested, values,
                     where=[v < i for v, i in zip(values, invested)],
                     color="red", alpha=0.3, label="ขาดทุน")
    ax.plot(months, values, color="royalblue", linewidth=2,
            label="มูลค่าพอร์ต")

    ax.set_title(f"DCA Backtest: {symbol} (${dca_result['monthly_amount']:,}/เดือน)",
                 fontsize=14, fontweight="bold")
    ax.set_ylabel("USD")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # แสดงทุกๆ 3 เดือน ไม่ให้ Label แน่นเกินไป
    tick_positions = range(0, len(months), 3)
    ax.set_xticks(tick_positions)
    ax.set_xticklabels([months[i] for i in tick_positions], rotation=45)

    plt.tight_layout()

    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"reports/{symbol}_dca_{today}.png"
    plt.savefig(filename, dpi=150, bbox_inches="tight")
    plt.close()

    print(f"  📈 DCA chart saved: {filename}")
    return filename

if __name__ == "__main__":
    watchlist = ["MSFT", "NVDA", "META", "SOFI", "AMKR"]
    monthly = 10000

    all_results = []

    for symbol in watchlist:
        try:
            result = compare_strategies(symbol, monthly, "2y")
            all_results.append(result)
        except Exception as e:
            print(f"\n  ❌ {symbol}: {e}")

    # สรุปภาพรวม
    print(f"\n{'=' * 60}")
    print(f"  📊 สรุปภาพรวม DCA vs Lump Sum")
    print(f"{'=' * 60}\n")

    print(f"  {'Ticker':<8} {'DCA':>10} {'Lump Sum':>10} {'Winner':>10}")
    print(f"  {'-' * 40}")

    for r in all_results:
        dca_pct = f"{r['dca']['profit_pct']:.1f}%"
        lump_pct = f"{r['lump']['profit_pct']:.1f}%"
        print(f"  {r['dca']['symbol']:<8} {dca_pct:>10} {lump_pct:>10} {r['winner']:>10}")

    dca_wins = sum(1 for r in all_results if r["winner"] == "DCA")
    lump_wins = len(all_results) - dca_wins
    print(f"\n  DCA ชนะ {dca_wins} ตัว / Lump Sum ชนะ {lump_wins} ตัว")

    # สร้างกราฟ DCA ทุกตัว
    print(f"\n{'=' * 60}")
    print(f"  📈 สร้างกราฟ DCA")
    print(f"{'=' * 60}\n")

    for r in all_results:
        plot_dca_chart(r["dca"]["symbol"], r["dca"])