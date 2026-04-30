import pandas as pd
from main import fetch_stock_data, fetch_financials, reverse_dcf, score_stock

# ==========================================
#  ขั้น 1: สร้าง DataFrame จากข้อมูลหุ้น
# ==========================================

watchlist = ["MSFT", "NVDA", "META", "SOFI", "AMKR"]
rows = []

print("=== ดึงข้อมูล ===\n")

for symbol in watchlist:
    try:
        print(f"  {symbol}...", end=" ")
        stock_data, ticker, info = fetch_stock_data(symbol)
        metrics = fetch_financials(ticker)
        dcf = reverse_dcf(info, metrics)
        scores = score_stock(info, dcf)
        total = sum(s["score"] for s in scores.values())

        rows.append({
            "Ticker": symbol,
            "Name": stock_data["ชื่อบริษัท"],
            "Price": stock_data["ราคาปัจจุบัน"],
            "P/E": info.get("trailingPE"),
            "Growth": info.get("revenueGrowth"),
            "Margin": info.get("profitMargins"),
            "D/E": info.get("debtToEquity"),
            "Implied": dcf.get("implied_growth"),
            "Score": total,
        })
        print(f"✅ {total}/100")
    except Exception as e:
        print(f"❌ {e}")

# สร้าง DataFrame
df = pd.DataFrame(rows)

print("\n=== DataFrame ===\n")
print(df)

# ==========================================
#  ขั้น 2: pandas ทำสิ่งที่ Loop ทำไม่ได้
# ==========================================

# เรียงตาม Score สูง → ต่ำ
df_sorted = df.sort_values("Score", ascending=False)
print("\n=== เรียงตาม Score ===\n")
print(df_sorted[["Ticker", "Score", "Price", "P/E"]].to_string(index=False))

# กรองเฉพาะหุ้นที่ Score >= 70
print("\n=== หุ้นที่ Score >= 70 ===\n")
good_stocks = df[df["Score"] >= 70]
print(good_stocks[["Ticker", "Score"]].to_string(index=False))

# หาค่าเฉลี่ย
print("\n=== สถิติภาพรวม ===\n")
print(f"  Score เฉลี่ย:    {df['Score'].mean():.1f}")
print(f"  Score สูงสุด:   {df['Score'].max()} ({df.loc[df['Score'].idxmax(), 'Ticker']})")
print(f"  Score ต่ำสุด:   {df['Score'].min()} ({df.loc[df['Score'].idxmin(), 'Ticker']})")
print(f"  P/E เฉลี่ย:     {df['P/E'].mean():.1f}")
print(f"  Growth เฉลี่ย:  {df['Growth'].mean():.1%}")

# ==========================================
#  ขั้น 3: บันทึกเป็น Excel ด้วย pandas
# ==========================================

from datetime import datetime

today = datetime.now().strftime("%Y-%m-%d")
excel_file = f"reports/analysis_{today}.csv"

df_sorted.to_csv(excel_file, index=False, encoding="utf-8-sig")
print(f"\n  📊 บันทึก: {excel_file}")