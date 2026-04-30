from data_manager import save_scores_csv, save_results_json, load_results_json
import pandas as pd

from main import fetch_stock_data, fetch_financials, reverse_dcf, score_stock
from datetime import datetime

# ==========================================
#  Batch Analysis: วิเคราะห์หลายตัวพร้อมกัน
# ==========================================

def batch_analyze(watchlist):
    """วิเคราะห์หุ้นทั้ง Watchlist แล้วจัดอันดับ"""
    results = []

    print(f"\n🤖 PANGZ Batch Analyzer")
    print(f"   วิเคราะห์ {len(watchlist)} ตัว...")
    print("=" * 50)

    for i, symbol in enumerate(watchlist, 1):
        print(f"\n  [{i}/{len(watchlist)}] กำลังวิเคราะห์ {symbol}...")

        try:
            # ดึงข้อมูล
            stock_data, ticker, info = fetch_stock_data(symbol)
            print(f"          ✅ ดึงข้อมูลพื้นฐาน")

            # ดึงงบการเงิน
            metrics = fetch_financials(ticker)
            print(f"          ✅ ดึงงบการเงิน")

            # Reverse DCF
            dcf_result = reverse_dcf(info, metrics)
            print(f"          ✅ Reverse DCF")

            # Scoring
            scores = score_stock(info, dcf_result)
            total = sum(s["score"] for s in scores.values())
            print(f"          ✅ Score: {total}/100")

            # เก็บผลลัพธ์
            results.append({
                "symbol": symbol,
                "name": stock_data["ชื่อบริษัท"],
                "price": stock_data["ราคาปัจจุบัน"],
                "pe": info.get("trailingPE", None),
                "growth": info.get("revenueGrowth", None),
                "margin": info.get("profitMargins", None),
                "de": info.get("debtToEquity", None),
                "implied_growth": dcf_result.get("implied_growth", None),
                "scores": scores,
                "total_score": total,
                "dcf_result": dcf_result,
                "stock_data": stock_data,
                "metrics": metrics,
            })

        except Exception as e:
            print(f"          ❌ Error: {e}")

    # จัดอันดับตาม Score สูง → ต่ำ
    results.sort(key=lambda x: x["total_score"], reverse=True)

    return results

def display_comparison(results):
    """แสดงตารางเปรียบเทียบหุ้นทั้งหมด"""

    print(f"\n{'=' * 80}")
    print(f"  📊 Stock Comparison & Ranking")
    print(f"{'=' * 80}\n")

    # หัวตาราง
    print(f"{'Rank':<6} {'Ticker':<8} {'Score':>6} {'Price':>10} {'P/E':>8} {'Growth':>8} {'Margin':>8} {'D/E':>8} {'Implied':>8}")
    print("-" * 80)

    for i, r in enumerate(results, 1):
        # จัดการค่า None
        pe_str = f"{r['pe']:.1f}" if r['pe'] else "N/A"
        growth_str = f"{r['growth']:.1%}" if r['growth'] else "N/A"
        margin_str = f"{r['margin']:.1%}" if r['margin'] else "N/A"
        de_str = f"{r['de']:.1f}" if r['de'] else "N/A"
        implied_str = f"{r['implied_growth']:.0%}" if r['implied_growth'] else "N/A"
        price_str = f"${r['price']:,.2f}" if r['price'] else "N/A"

        print(f"  #{i:<4} {r['symbol']:<8} {r['total_score']:>4}/100 {price_str:>10} {pe_str:>8} {growth_str:>8} {margin_str:>8} {de_str:>8} {implied_str:>8}")

    # แสดงรายละเอียดคะแนนแต่ละเกณฑ์
    print(f"\n{'=' * 80}")
    print(f"  📋 รายละเอียดคะแนน")
    print(f"{'=' * 80}\n")

    print(f"{'Ticker':<8} {'P/E':>8} {'Growth':>8} {'Margin':>8} {'D/E':>8} {'Value':>8} {'TOTAL':>8}")
    print("-" * 56)

    for r in results:
        s = r["scores"]
        print(f"{r['symbol']:<8}", end="")
        for criteria in ["P/E Ratio", "Revenue Growth", "Profit Margin", "Debt/Equity", "Valuation"]:
            print(f"{s[criteria]['score']:>7}/20", end="")
        print(f"{r['total_score']:>7}/100")


def save_batch_report(results):
    """บันทึกรายงานเปรียบเทียบทั้งหมดเป็นไฟล์"""

    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"reports/BATCH_{today}.txt"

    with open(filename, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write(f"  PANGZ Stock Comparison Report\n")
        f.write(f"  วันที่: {today}\n")
        f.write(f"  จำนวนหุ้น: {len(results)} ตัว\n")
        f.write("=" * 70 + "\n\n")

        # ตารางอันดับ
        f.write("--- อันดับรวม ---\n\n")
        for i, r in enumerate(results, 1):
            f.write(f"  #{i} {r['symbol']:<8} {r['total_score']}/100  ({r['name']})\n")

        # รายละเอียดแต่ละตัว
        for r in results:
            f.write(f"\n{'=' * 50}\n")
            f.write(f"  {r['symbol']} — {r['name']}\n")
            f.write(f"{'=' * 50}\n\n")

            f.write(f"  ราคา: ${r['price']}\n")
            f.write(f"  Score: {r['total_score']}/100\n\n")

            for criteria, result in r["scores"].items():
                f.write(f"  {criteria:<18} {result['score']:>3}/20 → {result['reason']}\n")

            # งบการเงิน
            f.write(f"\n  งบการเงิน:\n")
            for d in r["metrics"]:
                rev = f"${d['revenue']/1e9:.2f}B" if d['revenue'] else "N/A"
                ni = f"${d['net_income']/1e9:.2f}B" if d['net_income'] else "N/A"
                fcf = f"${d['free_cashflow']/1e9:.2f}B" if d['free_cashflow'] else "N/A"
                f.write(f"    {d['year']}: Revenue={rev}, NI={ni}, FCF={fcf}\n")

            # DCF
            if "error" not in r["dcf_result"]:
                f.write(f"\n  Reverse DCF:\n")
                f.write(f"    Implied Growth: {r['dcf_result']['implied_growth']:.0%}\n")

    return filename

import ollama

def ai_portfolio_recommendation(results):
    """ให้ AI แนะนำภาพรวม Portfolio"""

    summary = ""
    for i, r in enumerate(results, 1):
        summary += f"#{i} {r['symbol']} ({r['name']})\n"
        summary += f"   Score: {r['total_score']}/100\n"
        summary += f"   Price: ${r['price']}, P/E: {r['pe']}\n"
        summary += f"   Growth: {r['growth']}, Margin: {r['margin']}\n"
        if "error" not in r["dcf_result"]:
            summary += f"   Implied Growth: {r['dcf_result']['implied_growth']:.0%}\n"
        summary += "\n"

    prompt = f"""คุณเป็นนักวิเคราะห์หุ้นแนว Value Investing
ตอบเป็นภาษาไทย ห้ามใช้ภาษาอื่นนอกจากไทยและอังกฤษ
ใช้ข้อมูลจริงเท่านั้น กระชับ ตรงประเด็น

ข้อมูลหุ้นเรียงตามคะแนน:
{summary}

กรุณาเขียน Portfolio Recommendation:

1. สรุป Top Pick: ตัวไหนน่าสนใจที่สุดตอนนี้ พร้อมเหตุผล 2 ข้อ
2. ตัวที่ควรรอ: ตัวไหนควรรอจังหวะ ราคาเท่าไหร่ถึงน่าซื้อ
3. ตัวที่ควรระวัง: ตัวไหนมีความเสี่ยงสูงสุด
4. แผน DCA แนะนำ: ถ้ามีเงิน 100,000 บาท ควรแบ่งลงทุนยังไง
"""

    print("\n  🤖 AI กำลังเขียน Portfolio Recommendation...\n")

    response = ollama.chat(
        model="qwen2.5:14b",
        messages=[{"role": "user", "content": prompt}]
    )

    return response["message"]["content"]


# ==========================================
#  เริ่มโปรแกรม
# ==========================================

def pandas_summary(results):
    """สรุปภาพรวมด้วย pandas"""

    rows = []
    for r in results:
        rows.append({
            "Ticker": r["symbol"],
            "Score": r["total_score"],
            "Price": r["price"],
            "P/E": r.get("pe"),
            "Growth": r.get("growth"),
            "Margin": r.get("margin"),
            "Implied": r.get("implied_growth"),
        })

    df = pd.DataFrame(rows)

    print(f"\n{'=' * 60}")
    print(f"  📈 Quick Stats")
    print(f"{'=' * 60}\n")

    print(f"  หุ้นทั้งหมด:    {len(df)} ตัว")
    print(f"  Score เฉลี่ย:    {df['Score'].mean():.1f}/100")
    print(f"  น่าสนใจ (≥70):  {len(df[df['Score'] >= 70])} ตัว")
    print(f"  ระวัง (<60):     {len(df[df['Score'] < 60])} ตัว")

    # หา Top Pick
    best = df.loc[df["Score"].idxmax()]
    print(f"\n  🏆 Top Pick: {best['Ticker']} ({best['Score']}/100)")

    # หาถูกที่สุด (P/E ต่ำสุดในกลุ่ม Score >= 70)
    good = df[df["Score"] >= 70]
    if len(good) > 0:
        cheapest = good.loc[good["P/E"].idxmin()]
        print(f"  💰 ถูกสุดในกลุ่มดี: {cheapest['Ticker']} (P/E {cheapest['P/E']:.1f})")

    return df

if __name__ == "__main__":
    print("\n🤖 PANGZ Batch Analyzer v2.0")
    print("=" * 40)

    user_input = input("\nพิมพ์ชื่อหุ้น คั่นด้วยช่องว่าง\n(เช่น MSFT NVDA META SOFI AMKR): ").upper().strip()

    watchlist = user_input.split()

    if len(watchlist) == 0:
        print("❌ กรุณาพิมพ์ชื่อหุ้นอย่างน้อย 1 ตัว")
    else:
        # วิเคราะห์
        results = batch_analyze(watchlist)

        # แสดงตาราง Comparison
        display_comparison(results)

        # สรุปด้วย pandas
        df = pandas_summary(results)

        # บันทึกทุกอย่างอัตโนมัติ
        print(f"\n{'=' * 60}")
        print(f"  💾 กำลังบันทึก...")
        print(f"{'=' * 60}\n")

        csv_file = save_scores_csv(results)
        json_file = save_results_json(results)
        report_file = save_batch_report(results)

        # AI Recommendation
        ai_report = ai_portfolio_recommendation(results)
        print(f"\n{'=' * 60}")
        print(f"  🤖 AI Portfolio Recommendation")
        print(f"{'=' * 60}\n")
        print(ai_report)

        # สรุปไฟล์ทั้งหมด
        print(f"\n{'=' * 60}")
        print(f"  📁 ไฟล์ที่บันทึก")
        print(f"{'=' * 60}\n")
        print(f"  📊 CSV (เปิดใน Excel):  {csv_file}")
        print(f"  💾 JSON (โหลดกลับได้):  {json_file}")
        print(f"  📄 Report (อ่านรายงาน): {report_file}")
        print(f"\n  ✅ เสร็จสมบูรณ์!")