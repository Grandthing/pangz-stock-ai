import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import dataclass
from typing import List
import pandas as pd


@dataclass
class ConfluencePoint:
    """จุด Confluence — ราคาที่มีหลาย Indicator ซ้อนกัน"""
    price: float
    pct_from_current: float
    role: str              # 'SUP' or 'RES'
    components: List[str]  # เช่น ['Fib 38.2%', 'SMA 50']
    strength: int          # 1-3 ดาว
    description: str


def detect_confluence(indicators: dict, threshold_pct: float = 1.5) -> List[ConfluencePoint]:
    """
    หาจุดที่หลาย Indicator อยู่ใกล้กัน (ภายใน threshold_pct%)

    threshold_pct = 1.5 หมายถึง ถ้า 2 ระดับราคาห่างกันไม่เกิน 1.5%
                    ถือว่าเป็น Confluence
    """

    current_price = indicators["current_price"]

    # รวบรวมระดับราคาสำคัญทั้งหมด
    price_levels = []

    # 1. SMA Levels
    for name, sma in indicators["sma"].items():
        if sma.values.get("current"):
            price_levels.append({
                "price": sma.values["current"],
                "label": name,
                "source": "SMA",
            })

    # 2. Bollinger Bands
    bb = indicators["bb"]
    if bb.values.get("upper"):
        price_levels.append({"price": bb.values["upper"], "label": "BB Upper", "source": "Bollinger"})
        price_levels.append({"price": bb.values["middle"], "label": "BB Middle", "source": "Bollinger"})
        price_levels.append({"price": bb.values["lower"], "label": "BB Lower", "source": "Bollinger"})

    # 3. Fibonacci Levels
    fib = indicators["fibonacci"]
    if "levels" in fib.values:
        for level in fib.values["levels"]:
            price_levels.append({
                "price": level["price"],
                "label": f"Fib {level['label']}",
                "source": "Fibonacci",
            })

    # หา Confluence: จับคู่ทุกระดับราคาที่ใกล้กัน
    confluences = []
    used = set()

    for i, level_a in enumerate(price_levels):
        if i in used:
            continue

        cluster = [level_a]
        cluster_indices = {i}

        for j, level_b in enumerate(price_levels):
            if j <= i or j in used:
                continue

            # เช็คว่าอยู่ใกล้กันไหม
            if level_a["price"] == 0:
                continue

            diff_pct = abs(level_a["price"] - level_b["price"]) / level_a["price"] * 100

            if diff_pct <= threshold_pct:
                # ต้องมาจากคนละ Source (SMA+Fib ดี, SMA+SMA ไม่นับ)
                if level_b["source"] != level_a["source"]:
                    cluster.append(level_b)
                    cluster_indices.add(j)

        # ต้องมีอย่างน้อย 2 components จากต่าง Source
        if len(cluster) >= 2:
            used.update(cluster_indices)

            avg_price = round(sum(c["price"] for c in cluster) / len(cluster), 2)
            pct_from_current = round(((avg_price / current_price) - 1) * 100, 2)
            role = "SUP" if avg_price < current_price else "RES"
            components = [c["label"] for c in cluster]
            strength = min(len(cluster), 3)

            # สร้างคำอธิบาย
            comp_text = " + ".join(components)
            stars = "⭐" * strength

            if role == "SUP":
                desc = f"{stars} แนวรับที่ ${avg_price} ({comp_text}) ห่าง {pct_from_current:.1f}%"
            else:
                desc = f"{stars} แนวต้านที่ ${avg_price} ({comp_text}) ห่าง +{pct_from_current:.1f}%"

            confluences.append(ConfluencePoint(
                price=avg_price,
                pct_from_current=pct_from_current,
                role=role,
                components=components,
                strength=strength,
                description=desc,
            ))

    # เรียงตามระยะห่างจากราคาปัจจุบัน
    confluences.sort(key=lambda x: abs(x.pct_from_current))

    return confluences


def build_fib_table(indicators: dict, confluences: List[ConfluencePoint]) -> pd.DataFrame:
    """สร้างตาราง Fib + Confluence แบบสวยงาม"""

    fib = indicators["fibonacci"]
    current_price = indicators["current_price"]

    if "levels" not in fib.values:
        return pd.DataFrame()

    rows = []
    for level in fib.values["levels"]:
        # เช็คว่า Level นี้มี Confluence ไหม
        confluence_text = ""
        strength = 0

        for conf in confluences:
            diff = abs(conf.price - level["price"]) / level["price"] * 100
            if diff < 1.5:
                confluence_text = " + ".join(
                    [c for c in conf.components if "Fib" not in c]
                )
                strength = conf.strength
                break

        stars = "⭐" * strength if strength > 0 else ""
        ext = "Ext" if level["is_extension"] else ""

        rows.append({
            "Level": level["label"],
            "ราคา": f"${level['price']:,.2f}",
            "ห่าง %": f"{level['distance_pct']:+.1f}%",
            "S/R": level["role"],
            "Confluence": confluence_text,
            "Strength": stars,
            "Type": ext,
        })

    return pd.DataFrame(rows)


# ==========================================
#  Test
# ==========================================

if __name__ == "__main__":
    from indicators import get_all_indicators

    ticker = "META"
    print(f"{'=' * 60}")
    print(f"  ⭐ Confluence Detection: {ticker}")
    print(f"{'=' * 60}\n")

    indicators = get_all_indicators(ticker)
    confluences = detect_confluence(indicators)

    if confluences:
        print(f"  พบ {len(confluences)} จุด Confluence:\n")
        for conf in confluences:
            print(f"  {conf.description}")

        # Fib Table
        print(f"\n  📐 Fibonacci + Confluence Table:\n")
        df = build_fib_table(indicators, confluences)
        print(df.to_string(index=False))
    else:
        print("  ไม่พบ Confluence ที่ชัดเจน")