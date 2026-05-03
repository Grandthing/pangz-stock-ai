import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class TDSetup:
    """TD Setup (1-9 consecutive bars)"""
    type: str              # 'buy' or 'sell'
    count: int             # 1-9
    is_complete: bool      # ครบ 9 แล้วหรือยัง
    start_idx: int
    end_idx: int
    price: float           # ราคาที่จุดสุดท้าย


@dataclass
class TDCountdown:
    """TD Countdown (1-13, เริ่มหลัง Setup ครบ 9)"""
    type: str              # 'buy' or 'sell'
    count: int             # 1-13
    is_complete: bool


# ==========================================
#  Buy Setup: 9 consecutive closes < close 4 bars ago
# ==========================================

def find_setups(df: pd.DataFrame, setup_type: str = "buy") -> List[TDSetup]:
    """หา TD Setup ทั้งหมดในประวัติ"""
    setups = []
    closes = df["Close"].values

    if len(closes) < 5:
        return setups

    count = 0
    start_idx = None

    for i in range(4, len(closes)):
        # Buy Setup: ปิดต่ำกว่าปิด 4 วันก่อน
        # Sell Setup: ปิดสูงกว่าปิด 4 วันก่อน
        if setup_type == "buy":
            condition = closes[i] < closes[i - 4]
        else:
            condition = closes[i] > closes[i - 4]

        if condition:
            if count == 0:
                start_idx = i
            count += 1

            if count == 9:
                # Setup ครบ 9
                setups.append(TDSetup(
                    type=setup_type,
                    count=9,
                    is_complete=True,
                    start_idx=start_idx,
                    end_idx=i,
                    price=closes[i],
                ))
                count = 0
                start_idx = None
        else:
            # ขาดเงื่อนไข reset
            if count > 0 and count < 9:
                # Setup ไม่ครบ
                pass
            count = 0
            start_idx = None

    return setups


# ==========================================
#  Current Setup (กำลังนับอยู่)
# ==========================================

def get_current_setup(df: pd.DataFrame) -> Optional[TDSetup]:
    """หา Setup ที่กำลังนับอยู่ปัจจุบัน"""
    closes = df["Close"].values

    if len(closes) < 5:
        return None

    # ตรวจ Buy Setup
    buy_count = 0
    for i in range(len(closes) - 1, 3, -1):
        if closes[i] < closes[i - 4]:
            buy_count += 1
        else:
            break

    # ตรวจ Sell Setup
    sell_count = 0
    for i in range(len(closes) - 1, 3, -1):
        if closes[i] > closes[i - 4]:
            sell_count += 1
        else:
            break

    if buy_count > 0 and buy_count > sell_count:
        return TDSetup(
            type="buy",
            count=min(buy_count, 9),
            is_complete=buy_count >= 9,
            start_idx=len(closes) - buy_count,
            end_idx=len(closes) - 1,
            price=float(closes[-1]),
        )
    elif sell_count > 0:
        return TDSetup(
            type="sell",
            count=min(sell_count, 9),
            is_complete=sell_count >= 9,
            start_idx=len(closes) - sell_count,
            end_idx=len(closes) - 1,
            price=float(closes[-1]),
        )

    return None


# ==========================================
#  TDST Levels (Support/Resistance from Setup)
# ==========================================

def calculate_tdst(df: pd.DataFrame, setup: TDSetup) -> dict:
    """
    TDST Resistance = Highest High during Buy Setup
    TDST Support    = Lowest Low during Sell Setup
    """
    if setup is None:
        return {"support": None, "resistance": None}

    start = setup.start_idx
    end = setup.end_idx + 1

    if setup.type == "buy":
        # Buy Setup → TDST Resistance = high สูงสุดในช่วง Setup
        resistance = float(df["High"].iloc[start:end].max())
        return {"resistance": round(resistance, 2), "support": None}
    else:
        # Sell Setup → TDST Support = low ต่ำสุดในช่วง Setup
        support = float(df["Low"].iloc[start:end].min())
        return {"support": round(support, 2), "resistance": None}


# ==========================================
#  Master Function
# ==========================================

def analyze_td_sequential(df: pd.DataFrame) -> dict:
    """วิเคราะห์ TD Sequential ครบทั้งหมด"""

    # Setup ปัจจุบัน
    current_setup = get_current_setup(df)

    # หา Setup ทั้งหมดในประวัติ (1 ปีย้อนหลัง)
    recent_df = df.tail(252)
    buy_setups = find_setups(recent_df, "buy")
    sell_setups = find_setups(recent_df, "sell")

    # หา Setup สมบูรณ์ล่าสุด
    last_complete_setup = None
    if buy_setups and sell_setups:
        last_complete_setup = max(
            buy_setups + sell_setups,
            key=lambda s: s.end_idx
        )
    elif buy_setups:
        last_complete_setup = buy_setups[-1]
    elif sell_setups:
        last_complete_setup = sell_setups[-1]

    # TDST Levels จาก Setup ล่าสุด
    tdst = calculate_tdst(recent_df, last_complete_setup)

    # ตีความ
    if current_setup:
        if current_setup.type == "buy" and current_setup.is_complete:
            interpretation = f"⚠️ TD Buy Setup 9 ครบแล้ว! สัญญาณ Reversal ขาขึ้น ราคา ${current_setup.price:.2f}"
        elif current_setup.type == "sell" and current_setup.is_complete:
            interpretation = f"⚠️ TD Sell Setup 9 ครบแล้ว! สัญญาณ Reversal ขาลง ราคา ${current_setup.price:.2f}"
        elif current_setup.type == "buy":
            interpretation = f"📉 TD Buy Setup กำลังนับ {current_setup.count}/9 (ราคาลงต่อเนื่อง)"
        else:
            interpretation = f"📈 TD Sell Setup กำลังนับ {current_setup.count}/9 (ราคาขึ้นต่อเนื่อง)"
    else:
        interpretation = "ไม่มี Setup ที่กำลังนับ — ตลาด choppy หรือเปลี่ยนทิศทาง"

    return {
        "current_setup": current_setup,
        "last_complete_setup": last_complete_setup,
        "tdst": tdst,
        "buy_setups_history": buy_setups,
        "sell_setups_history": sell_setups,
        "interpretation": interpretation,
    }


# ==========================================
#  Test
# ==========================================

if __name__ == "__main__":
    import yfinance as yf

    ticker = "META"
    print(f"{'=' * 60}")
    print(f"  🔔 TD Sequential: {ticker}")
    print(f"{'=' * 60}\n")

    df = yf.Ticker(ticker).history(period="1y")
    result = analyze_td_sequential(df)

    print(f"  {result['interpretation']}\n")

    if result["current_setup"]:
        cs = result["current_setup"]
        print(f"  Current Setup:")
        print(f"    Type:     {cs.type.upper()}")
        print(f"    Count:    {cs.count}/9")
        print(f"    Complete: {cs.is_complete}")
        print(f"    Price:    ${cs.price:.2f}")

    if result["last_complete_setup"]:
        ls = result["last_complete_setup"]
        print(f"\n  Last Complete Setup:")
        print(f"    Type:     {ls.type.upper()} 9")
        print(f"    Price:    ${ls.price:.2f}")

    tdst = result["tdst"]
    print(f"\n  TDST Levels:")
    if tdst.get("support"):
        print(f"    Support:    ${tdst['support']}")
    if tdst.get("resistance"):
        print(f"    Resistance: ${tdst['resistance']}")

    print(f"\n  History (1 year):")
    print(f"    Buy Setups completed:  {len(result['buy_setups_history'])}")
    print(f"    Sell Setups completed: {len(result['sell_setups_history'])}")