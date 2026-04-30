import csv
import json
from datetime import datetime

# ==========================================
#  CSV: บันทึกและโหลดข้อมูลตาราง
# ==========================================

def save_scores_csv(results, filename=None):
    """บันทึกคะแนนหุ้นทั้งหมดเป็น CSV เปิดใน Excel ได้"""

    if filename is None:
        today = datetime.now().strftime("%Y-%m-%d")
        filename = f"reports/scores_{today}.csv"

    # กำหนดหัวคอลัมน์
    headers = [
        "Rank", "Ticker", "Name", "Price", "Score",
        "P/E", "P/E Score",
        "Growth", "Growth Score",
        "Margin", "Margin Score",
        "D/E", "D/E Score",
        "Implied Growth", "Valuation Score",
    ]

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for i, r in enumerate(results, 1):
            s = r["scores"]
            row = [
                i,
                r["symbol"],
                r["name"],
                r["price"],
                r["total_score"],
                r.get("pe", "N/A"),
                s["P/E Ratio"]["score"],
                r.get("growth", "N/A"),
                s["Revenue Growth"]["score"],
                r.get("margin", "N/A"),
                s["Profit Margin"]["score"],
                r.get("de", "N/A"),
                s["Debt/Equity"]["score"],
                r.get("implied_growth", "N/A"),
                s["Valuation"]["score"],
            ]
            writer.writerow(row)

    print(f"  📊 CSV saved: {filename}")
    return filename

# ==========================================
#  JSON: บันทึกและโหลดข้อมูลดิบ
# ==========================================

def save_results_json(results, filename=None):
    """บันทึกผลวิเคราะห์ทั้งหมดเป็น JSON"""

    if filename is None:
        today = datetime.now().strftime("%Y-%m-%d")
        filename = f"reports/results_{today}.json"

    # เตรียมข้อมูลสำหรับบันทึก
    save_data = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total_stocks": len(results),
        "stocks": []
    }

    for r in results:
        stock_entry = {
            "symbol": r["symbol"],
            "name": r["name"],
            "price": r["price"],
            "total_score": r["total_score"],
            "pe": r.get("pe"),
            "growth": r.get("growth"),
            "margin": r.get("margin"),
            "de": r.get("de"),
            "implied_growth": r.get("implied_growth"),
            "scores": {k: v["score"] for k, v in r["scores"].items()},
            "financials": r.get("metrics", []),
        }
        save_data["stocks"].append(stock_entry)

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)

    print(f"  💾 JSON saved: {filename}")
    return filename


def load_results_json(filename):
    """โหลดผลวิเคราะห์จาก JSON"""

    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"  📂 Loaded: {filename}")
    print(f"     วันที่: {data['date']}")
    print(f"     จำนวนหุ้น: {data['total_stocks']} ตัว")

    return data

# ==========================================
#  ทดสอบ
# ==========================================

if __name__ == "__main__":
    from main import fetch_stock_data, fetch_financials, reverse_dcf, score_stock

    # วิเคราะห์ 3 ตัว
    watchlist = ["MSFT", "NVDA", "META"]
    results = []

    for symbol in watchlist:
        print(f"  ดึงข้อมูล {symbol}...")
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
            "implied_growth": dcf.get("implied_growth"),
            "scores": scores,
            "total_score": total,
            "metrics": metrics,
        })

    # เรียงอันดับ
    results.sort(key=lambda x: x["total_score"], reverse=True)

    # บันทึก CSV
    csv_file = save_scores_csv(results)

    # บันทึก JSON
    json_file = save_results_json(results)

    # ทดสอบโหลด JSON กลับมา
    print("\n=== ทดสอบโหลด JSON ===\n")
    loaded = load_results_json(json_file)

    for stock in loaded["stocks"]:
        print(f"  {stock['symbol']}: {stock['total_score']}/100 (${stock['price']})")