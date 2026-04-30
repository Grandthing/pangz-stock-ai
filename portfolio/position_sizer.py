import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from portfolio.sector_classifier import get_sector, get_correlation_groups, get_sector_exposure, get_group_exposure

# === Conviction Framework ===

CONVICTION_GUIDE = {
    "criteria": [
        {"name": "เข้าใจธุรกิจ", "desc": "อ่าน 10-K / รู้จัก Product จริง", "max": 2},
        {"name": "Valuation มี Margin of Safety", "desc": "ราคาต่ำกว่ามูลค่าจริง", "max": 2},
        {"name": "มี Catalyst 6-12 เดือน", "desc": "เช่น Product ใหม่, Earnings โต", "max": 2},
        {"name": "Technical Setup ดี", "desc": "Uptrend, ราคาใกล้ Support", "max": 2},
        {"name": "ไม่มี Red Flag", "desc": "ไม่มีปัญหา Governance / Fraud", "max": 2},
    ],
    "mapping": {
        (9, 10): {"size_pct": (8, 10), "category": "High Conviction"},
        (7, 8): {"size_pct": (5, 7), "category": "Medium-High"},
        (5, 6): {"size_pct": (3, 5), "category": "Medium"},
        (3, 4): {"size_pct": (2, 3), "category": "Speculative"},
        (1, 2): {"size_pct": (1, 2), "category": "Tracker Only"},
    }
}


def get_conviction_category(conviction):
    """แปลง Conviction Score → ขนาด Position ที่แนะนำ"""
    if conviction >= 9:
        return {"size_pct": (8, 10), "category": "High Conviction"}
    elif conviction >= 7:
        return {"size_pct": (5, 7), "category": "Medium-High"}
    elif conviction >= 5:
        return {"size_pct": (3, 5), "category": "Medium"}
    elif conviction >= 3:
        return {"size_pct": (2, 3), "category": "Speculative"}
    elif conviction >= 1:
        return {"size_pct": (1, 2), "category": "Tracker Only"}
    else:
        return {"size_pct": (0, 0), "category": "Do Not Buy"}


def calculate_max_position(portfolio_value, conviction, asset_type="stock"):
    """คำนวณ Position สูงสุดที่ควรซื้อ"""

    # กฎ Max ตาม Asset Type
    asset_limits = {
        "stock": 10,
        "sector_etf": 15,
        "broad_etf": 50,
        "thematic_etf": 10,
    }

    max_by_asset = asset_limits.get(asset_type, 10)

    # กฎ Max ตาม Conviction
    conv_info = get_conviction_category(conviction)
    min_pct, max_pct = conv_info["size_pct"]

    # เอาค่าต่ำสุดระหว่าง Asset Limit กับ Conviction Limit
    final_max_pct = min(max_pct, max_by_asset)
    recommended_pct = min_pct + (final_max_pct - min_pct) * 0.7

    return {
        "max_pct": final_max_pct,
        "max_usd": portfolio_value * final_max_pct / 100,
        "recommended_pct": round(recommended_pct, 1),
        "recommended_usd": round(portfolio_value * recommended_pct / 100, 2),
        "conviction": conviction,
        "category": conv_info["category"],
        "asset_type": asset_type,
    }

def check_concentration(portfolio_value, holdings, proposed_ticker, proposed_usd, cash_available):
    """เช็คกฎความเสี่ยงทั้งหมดก่อนซื้อ"""

    warnings = []
    violations = []

    # === กฎที่ 1: Single Position ≤ 10% ===
    proposed_pct = (proposed_usd / portfolio_value) * 100

    # รวมกับที่ถืออยู่แล้ว (ถ้ามี)
    existing_value = 0
    if proposed_ticker in holdings:
        existing_value = holdings[proposed_ticker].get("market_value", 0)
    total_position_pct = ((existing_value + proposed_usd) / portfolio_value) * 100

    if total_position_pct > 10:
        violations.append(
            f"❌ {proposed_ticker} จะเป็น {total_position_pct:.1f}% ของพอร์ต (เกิน 10%)"
        )
    elif total_position_pct > 8:
        warnings.append(
            f"⚠️ {proposed_ticker} จะเป็น {total_position_pct:.1f}% ของพอร์ต (ใกล้ 10%)"
        )

    # === กฎที่ 2: Sector ≤ 30% ===
    proposed_sector = get_sector(proposed_ticker)
    sector_exposure = get_sector_exposure(holdings, portfolio_value)
    current_sector_pct = sector_exposure.get(proposed_sector, 0)
    new_sector_pct = current_sector_pct + proposed_pct

    if new_sector_pct > 30:
        violations.append(
            f"❌ Sector {proposed_sector} จะเป็น {new_sector_pct:.1f}% (เกิน 30%)"
        )
    elif new_sector_pct > 25:
        warnings.append(
            f"⚠️ Sector {proposed_sector} จะเป็น {new_sector_pct:.1f}% (ใกล้ 30%)"
        )

    # === กฎที่ 3: Cash ≥ 15% หลังซื้อ ===
    cash_after = cash_available - proposed_usd
    cash_pct_after = (cash_after / portfolio_value) * 100

    if cash_pct_after < 10:
        violations.append(
            f"❌ Cash จะเหลือ {cash_pct_after:.1f}% (ต่ำกว่า 10%)"
        )
    elif cash_pct_after < 15:
        warnings.append(
            f"⚠️ Cash จะเหลือ {cash_pct_after:.1f}% (ต่ำกว่า 15%)"
        )

    # === กฎที่ 4: Correlation Group ≤ 30% ===
    group_exposure = get_group_exposure(holdings, portfolio_value)
    proposed_groups = get_correlation_groups(proposed_ticker)

    for group in proposed_groups:
        current_group_pct = group_exposure.get(group, 0)
        new_group_pct = current_group_pct + proposed_pct

        if new_group_pct > 30:
            violations.append(
                f"❌ Correlation Group '{group}' จะเป็น {new_group_pct:.1f}% (เกิน 30%)"
            )
        elif new_group_pct > 25:
            warnings.append(
                f"⚠️ Correlation Group '{group}' จะเป็น {new_group_pct:.1f}% (ใกล้ 30%)"
            )

    # สรุป
    passed = len(violations) == 0

    if not passed:
        suggestion = "DO_NOT_BUY"
    elif len(warnings) > 0:
        suggestion = "REDUCE_SIZE"
    else:
        suggestion = "BUY"

    return {
        "passed": passed,
        "violations": violations,
        "warnings": warnings,
        "suggestion": suggestion,
        "position_pct": total_position_pct,
        "sector_pct": new_sector_pct,
        "cash_after_pct": cash_pct_after,
    }

def suggest_position_size(ticker, portfolio_value, conviction, holdings, cash_available, asset_type="stock"):
    """Function หลัก: แนะนำขนาด Position + เช็คกฎทั้งหมด"""

    # คำนวณ Max Position จาก Conviction
    max_pos = calculate_max_position(portfolio_value, conviction, asset_type)

    # เช็คว่าเงินพอไหม
    affordable = min(max_pos["recommended_usd"], cash_available * 0.85)

    # เช็ค Concentration
    conc_check = check_concentration(
        portfolio_value, holdings, ticker, affordable, cash_available
    )

    # ปรับขนาดถ้ามี Warning/Violation
    if conc_check["suggestion"] == "DO_NOT_BUY":
        final_usd = 0
        final_pct = 0
    elif conc_check["suggestion"] == "REDUCE_SIZE":
        final_usd = affordable * 0.7
        final_pct = (final_usd / portfolio_value) * 100
    else:
        final_usd = affordable
        final_pct = (final_usd / portfolio_value) * 100

    # สร้าง Tranche Plan
    tranches = []
    if final_usd > 0:
        splits = [0.30, 0.30, 0.40]
        drops = [0.10, 0.20, 0.30]

        try:
            import yfinance as yf
            info = yf.Ticker(ticker).info
            current_price = info.get("currentPrice", 0)
            high_52w = info.get("fiftyTwoWeekHigh", current_price)

            for i, (split, drop) in enumerate(zip(splits, drops), 1):
                tranche_usd = round(final_usd * split, 2)
                trigger_price = round(high_52w * (1 - drop), 2)
                shares = int(tranche_usd / trigger_price) if trigger_price > 0 else 0

                tranches.append({
                    "tranche": i,
                    "allocation": f"{split:.0%}",
                    "trigger_price": trigger_price,
                    "drop_from_high": f"-{drop:.0%}",
                    "amount_usd": tranche_usd,
                    "est_shares": shares,
                })
        except:
            pass

    return {
        "ticker": ticker,
        "conviction": conviction,
        "category": max_pos["category"],
        "max_pct": max_pos["max_pct"],
        "max_usd": max_pos["max_usd"],
        "recommended_pct": round(final_pct, 1),
        "recommended_usd": round(final_usd, 2),
        "tranches": tranches,
        "concentration_check": conc_check,
        "cash_after_pct": conc_check["cash_after_pct"],
    }

if __name__ == "__main__":
    portfolio_value = 100000
    cash = 25000

    # === Test 1: พอร์ตกระจายตัวดี → ควร PASS ===
    print("=" * 50)
    print("  Test 1: พอร์ตกระจายตัวดี")
    print("=" * 50)

    holdings_good = {
        "NVDA": {"market_value": 8000},
        "LLY": {"market_value": 7000},
        "JPM": {"market_value": 6000},
        "XOM": {"market_value": 4000},
    }

    result1 = suggest_position_size(
        ticker="ADBE",
        portfolio_value=portfolio_value,
        conviction=8,
        holdings=holdings_good,
        cash_available=cash,
    )

    print(f"\n  Ticker:         {result1['ticker']}")
    print(f"  Conviction:     {result1['conviction']}/10 ({result1['category']})")
    print(f"  Max Position:   {result1['max_pct']}% (${result1['max_usd']:,.0f})")
    print(f"  Recommended:    {result1['recommended_pct']}% (${result1['recommended_usd']:,.0f})")
    print(f"  Cash After:     {result1['cash_after_pct']:.1f}%")

    check1 = result1["concentration_check"]
    print(f"  Result:         {'✅ PASSED' if check1['passed'] else '❌ FAILED'}")
    print(f"  Suggestion:     {check1['suggestion']}")

    for w in check1["warnings"]:
        print(f"  {w}")

    if result1["tranches"]:
        print(f"\n  📋 Tranche Plan:")
        for t in result1["tranches"]:
            print(f"    T{t['tranche']} {t['allocation']} @ ${t['trigger_price']} ({t['drop_from_high']}) → ${t['amount_usd']:,.0f} ({t['est_shares']} shares)")

    # === Test 2: พอร์ต Tech เกิน → ควร FAIL ===
    print(f"\n{'=' * 50}")
    print("  Test 2: พอร์ต Tech หนักเกิน")
    print("=" * 50)

    holdings_heavy = {
        "NVDA": {"market_value": 8000},
        "META": {"market_value": 7000},
        "MSFT": {"market_value": 6000},
        "AMD": {"market_value": 5000},
    }

    result2 = suggest_position_size(
        ticker="ADBE",
        portfolio_value=portfolio_value,
        conviction=8,
        holdings=holdings_heavy,
        cash_available=cash,
    )

    print(f"\n  Ticker:         {result2['ticker']}")
    print(f"  Conviction:     {result2['conviction']}/10 ({result2['category']})")
    print(f"  Recommended:    {result2['recommended_pct']}% (${result2['recommended_usd']:,.0f})")

    check2 = result2["concentration_check"]
    print(f"  Result:         {'✅ PASSED' if check2['passed'] else '❌ FAILED'}")
    print(f"  Suggestion:     {check2['suggestion']}")

    for v in check2["violations"]:
        print(f"  {v}")

    # === Test 3: Conviction ต่ำ ===
    print(f"\n{'=' * 50}")
    print("  Test 3: Conviction ต่ำ (3/10)")
    print("=" * 50)

    result3 = suggest_position_size(
        ticker="SOFI",
        portfolio_value=portfolio_value,
        conviction=3,
        holdings=holdings_good,
        cash_available=cash,
    )

    print(f"\n  Ticker:         {result3['ticker']}")
    print(f"  Conviction:     {result3['conviction']}/10 ({result3['category']})")
    print(f"  Max Position:   {result3['max_pct']}% (${result3['max_usd']:,.0f})")
    print(f"  Recommended:    {result3['recommended_pct']}% (${result3['recommended_usd']:,.0f})")