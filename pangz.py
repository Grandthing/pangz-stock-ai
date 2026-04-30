import matplotlib as mpl
mpl.rcParams['font.family'] = 'Tahoma'

from main import fetch_stock_data, fetch_financials, reverse_dcf, score_stock, generate_report, save_report
from batch_analyzer import batch_analyze, display_comparison, pandas_summary, save_batch_report, ai_portfolio_recommendation
from data_manager import save_scores_csv, save_results_json
from price_chart import fetch_price_history, plot_price_chart, plot_comparison, find_buy_signals
from dca_backtest import dca_backtest, compare_strategies, plot_dca_chart

def show_menu():
    """แสดงเมนูหลัก"""
    print(f"""
╔══════════════════════════════════════════╗
║   🤖 PANGZ Intelligence Platform v2.0   ║
╠══════════════════════════════════════════╣
║                                          ║
║   1. วิเคราะห์หุ้น 1 ตัว (Full Report)   ║
║   2. วิเคราะห์หลายตัว (Batch + Ranking)  ║
║   3. Technical Analysis (Chart + Signal)  ║
║   4. DCA Backtest                         ║
║   5. Full Analysis (ทุกอย่างรวม)          ║
║   0. ออกจากโปรแกรม                        ║
║                                          ║
╚══════════════════════════════════════════╝
""")
    choice = input("  เลือกเมนู (0-5): ").strip()
    return choice
def menu_single_analysis():
    """เมนู 1: วิเคราะห์หุ้น 1 ตัว ครบวงจร"""
    symbol = input("\n  พิมพ์ชื่อหุ้น (เช่น MSFT): ").upper().strip()

    print(f"\n  กำลังวิเคราะห์ {symbol}...\n")

    # ดึงข้อมูลทั้งหมด
    print("  [1/6] ดึงข้อมูลพื้นฐาน...")
    stock_data, ticker, info = fetch_stock_data(symbol)
    print(f"        ✅ {stock_data['ชื่อบริษัท']}")

    print("  [2/6] ดึงงบการเงิน...")
    metrics = fetch_financials(ticker)
    print(f"        ✅ ได้ข้อมูล {len(metrics)} ปี")

    print("  [3/6] Reverse DCF...")
    dcf_result = reverse_dcf(info, metrics)
    if "error" not in dcf_result:
        print(f"        ✅ Implied Growth: {dcf_result['implied_growth']:.0%}")
    else:
        print(f"        ⚠️ {dcf_result['error']}")

    print("  [4/6] Scoring...")
    scores = score_stock(info, dcf_result)
    total = sum(s["score"] for s in scores.values())
    print(f"        ✅ Score: {total}/100")

    print("  [5/6] Technical Analysis...")
    signals = find_buy_signals(symbol)
    print(f"        ✅ ตำแหน่ง 52W: {signals['position_52w']:.0f}%")

    print("  [6/6] AI Report...")
    ai_report = generate_report(symbol, stock_data, metrics, dcf_result, scores)
    print(f"        ✅ รายงานเสร็จ")

    # บันทึก
    filename = save_report(symbol, stock_data, metrics, dcf_result, scores, ai_report)

    # สร้างกราฟ
    history = fetch_price_history(symbol)
    chart_file = plot_price_chart(symbol, history)

    # แสดงผลสรุป
    print(f"\n{'=' * 50}")
    print(f"  📊 สรุป: {symbol} — {stock_data['ชื่อบริษัท']}")
    print(f"{'=' * 50}\n")

    print(f"  ราคา:        ${stock_data['ราคาปัจจุบัน']}")
    print(f"  Score:        {total}/100")

    for k, v in scores.items():
        print(f"    {k:<18} {v['score']:>3}/20 → {v['reason']}")

    print(f"\n  52W Range:    ${signals['low_52w']:.2f} — ${signals['high_52w']:.2f}")
    print(f"  ตำแหน่ง:      {signals['position_52w']:.0f}%")

    for s in signals["signals"]:
        print(f"  → {s}")

    print(f"\n  📄 รายงาน: {filename}")
    print(f"  📈 กราฟ:   {chart_file}")

    # แสดง AI Report
    print(f"\n{'=' * 50}")
    print(f"  🤖 AI Analysis")
    print(f"{'=' * 50}\n")
    print(ai_report)
def menu_batch_analysis():
    """เมนู 2: วิเคราะห์หลายตัว"""
    user_input = input("\n  พิมพ์ชื่อหุ้น คั่นด้วยช่องว่าง: ").upper().strip()
    watchlist = user_input.split()

    if len(watchlist) == 0:
        print("  ❌ กรุณาพิมพ์อย่างน้อย 1 ตัว")
        return

    results = batch_analyze(watchlist)
    display_comparison(results)
    df = pandas_summary(results)

    # บันทึก
    save_scores_csv(results)
    save_results_json(results)
    save_batch_report(results)

    # AI Recommendation
    ai_report = ai_portfolio_recommendation(results)
    print(f"\n{'=' * 50}")
    print(f"  🤖 AI Portfolio Recommendation")
    print(f"{'=' * 50}\n")
    print(ai_report)
def menu_technical():
    """เมนู 3: Technical Analysis"""
    user_input = input("\n  พิมพ์ชื่อหุ้น คั่นด้วยช่องว่าง: ").upper().strip()
    watchlist = user_input.split()

    # กราฟเปรียบเทียบ
    plot_comparison(watchlist)

    # Technical Signals
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

            for s in signals["signals"]:
                print(f"  → {s}")
        except Exception as e:
            print(f"\n  --- {symbol} ---")
            print(f"  ❌ {e}")

    # สร้างกราฟรายตัว
    for symbol in watchlist:
        try:
            history = fetch_price_history(symbol)
            plot_price_chart(symbol, history)
        except Exception as e:
            print(f"  ❌ {symbol}: {e}")


def menu_dca_backtest():
    """เมนู 4: DCA Backtest"""
    user_input = input("\n  พิมพ์ชื่อหุ้น คั่นด้วยช่องว่าง: ").upper().strip()
    watchlist = user_input.split()

    amount = input("  ลงทุนเดือนละ (USD, default 10000): ").strip()
    monthly = int(amount) if amount else 10000

    period = input("  ย้อนหลังกี่ปี (1y/2y/5y, default 2y): ").strip()
    period = period if period else "2y"

    all_results = []

    for symbol in watchlist:
        try:
            result = compare_strategies(symbol, monthly, period)
            all_results.append(result)
        except Exception as e:
            print(f"\n  ❌ {symbol}: {e}")

    # สรุป
    if all_results:
        print(f"\n{'=' * 60}")
        print(f"  📊 สรุป DCA vs Lump Sum")
        print(f"{'=' * 60}\n")

        print(f"  {'Ticker':<8} {'DCA':>10} {'Lump Sum':>10} {'Winner':>10}")
        print(f"  {'-' * 40}")

        for r in all_results:
            dca_pct = f"{r['dca']['profit_pct']:.1f}%"
            lump_pct = f"{r['lump']['profit_pct']:.1f}%"
            print(f"  {r['dca']['symbol']:<8} {dca_pct:>10} {lump_pct:>10} {r['winner']:>10}")

        # สร้างกราฟ
        for r in all_results:
            plot_dca_chart(r["dca"]["symbol"], r["dca"])


def menu_full_analysis():
    """เมนู 5: ทุกอย่างรวม"""
    user_input = input("\n  พิมพ์ชื่อหุ้น คั่นด้วยช่องว่าง: ").upper().strip()
    watchlist = user_input.split()

    amount = input("  ลงทุนเดือนละ (USD, default 10000): ").strip()
    monthly = int(amount) if amount else 10000

    print(f"\n  🚀 Full Analysis: {', '.join(watchlist)}")
    print(f"  ⏳ อาจใช้เวลา 2-5 นาที...\n")

    # Batch Analysis + Ranking
    results = batch_analyze(watchlist)
    display_comparison(results)
    df = pandas_summary(results)

    # Technical Signals
    print(f"\n{'=' * 60}")
    print(f"  🎯 Technical Signals")
    print(f"{'=' * 60}")

    for symbol in watchlist:
        try:
            signals = find_buy_signals(symbol)
            print(f"\n  --- {symbol} ---")
            print(f"  ตำแหน่ง 52W: {signals['position_52w']:.0f}%")
            for s in signals["signals"]:
                print(f"  → {s}")
        except:
            pass

    # DCA Backtest
    print(f"\n{'=' * 60}")
    print(f"  📊 DCA Backtest")
    print(f"{'=' * 60}")

    for symbol in watchlist:
        try:
            compare_strategies(symbol, monthly, "2y")
        except:
            pass

    # สร้างกราฟทั้งหมด
    print(f"\n{'=' * 60}")
    print(f"  📈 สร้างกราฟ")
    print(f"{'=' * 60}\n")

    plot_comparison(watchlist)
    for symbol in watchlist:
        try:
            history = fetch_price_history(symbol)
            plot_price_chart(symbol, history)
        except:
            pass

    # บันทึกทุกอย่าง
    save_scores_csv(results)
    save_results_json(results)
    save_batch_report(results)

    # AI Recommendation
    ai_report = ai_portfolio_recommendation(results)
    print(f"\n{'=' * 60}")
    print(f"  🤖 AI Portfolio Recommendation")
    print(f"{'=' * 60}\n")
    print(ai_report)

    print(f"\n  ✅ Full Analysis เสร็จสมบูรณ์!")
if __name__ == "__main__":
    while True:
        choice = show_menu()

        try:
            if choice == "1":
                menu_single_analysis()
            elif choice == "2":
                menu_batch_analysis()
            elif choice == "3":
                menu_technical()
            elif choice == "4":
                menu_dca_backtest()
            elif choice == "5":
                menu_full_analysis()
            elif choice == "0":
                print("\n  👋 ขอบคุณที่ใช้งาน PANGZ Platform!\n")
                break
            else:
                print("\n  ❌ กรุณาเลือก 0-5")
        except Exception as e:
            print(f"\n  ❌ เกิดข้อผิดพลาด: {e}")

        input("\n  กด Enter เพื่อกลับเมนูหลัก...")