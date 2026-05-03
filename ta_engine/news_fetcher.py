import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yfinance as yf
from datetime import datetime, timedelta
from typing import List, Dict


def fetch_news(ticker: str, max_news: int = 10) -> List[Dict]:
    """ดึงข่าวล่าสุดของหุ้นจาก Yahoo Finance"""
    try:
        tk = yf.Ticker(ticker)
        news = tk.news

        if not news:
            return []

        results = []
        for item in news[:max_news]:
            # yfinance news structure อาจมีหลาย format
            content = item.get("content", item)

            title = content.get("title", "")
            summary = content.get("summary", "")
            pub_date = content.get("pubDate", "") or content.get("providerPublishTime", "")
            publisher = content.get("provider", {})
            if isinstance(publisher, dict):
                publisher = publisher.get("displayName", "Unknown")
            url = content.get("canonicalUrl", {})
            if isinstance(url, dict):
                url = url.get("url", "")

            # แปลงเวลา
            if isinstance(pub_date, (int, float)):
                pub_date = datetime.fromtimestamp(pub_date).strftime("%Y-%m-%d %H:%M")
            elif isinstance(pub_date, str) and "T" in pub_date:
                pub_date = pub_date.split("T")[0]

            if title:
                results.append({
                    "title": title,
                    "summary": summary[:500] if summary else "",
                    "publisher": publisher,
                    "date": pub_date,
                    "url": url,
                })

        return results

    except Exception as e:
        print(f"  ⚠️ News fetch error: {e}")
        return []


def fetch_earnings_info(ticker: str) -> Dict:
    """ดึงข้อมูล Earnings ล่าสุด + ถัดไป (หลายวิธี)"""
    try:
        tk = yf.Ticker(ticker)
        info = tk.info

        result = {
            "next_earnings": None,
            "last_earnings": None,
            "eps_actual": None,
            "eps_estimate": None,
            "eps_surprise_pct": None,
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
        }

        # วิธีที่ 1: Calendar (อาจมีหรือไม่มี)
        try:
            cal = tk.calendar
            if cal is not None:
                if isinstance(cal, dict):
                    earn_date = cal.get("Earnings Date")
                    if earn_date:
                        if isinstance(earn_date, list) and len(earn_date) > 0:
                            result["next_earnings"] = str(earn_date[0])[:10]
                        else:
                            result["next_earnings"] = str(earn_date)[:10]
        except Exception:
            pass

        # วิธีที่ 2: earnings_dates DataFrame
        if not result["next_earnings"]:
            try:
                ed = tk.earnings_dates
                if ed is not None and not ed.empty:
                    now = datetime.now()
                    # Index เป็น Timestamp ที่มี timezone
                    ed_naive = ed.copy()
                    ed_naive.index = ed_naive.index.tz_localize(None) if ed_naive.index.tz else ed_naive.index

                    future = ed_naive[ed_naive.index > now]
                    if not future.empty:
                        result["next_earnings"] = future.index[-1].strftime("%Y-%m-%d")

                    past = ed_naive[ed_naive.index <= now]
                    if not past.empty:
                        last_row = past.iloc[0]
                        result["last_earnings"] = past.index[0].strftime("%Y-%m-%d")
                        result["eps_actual"] = last_row.get("Reported EPS")
                        result["eps_estimate"] = last_row.get("EPS Estimate")

                        if result["eps_actual"] is not None and result["eps_estimate"] is not None:
                            try:
                                actual = float(result["eps_actual"])
                                est = float(result["eps_estimate"])
                                if est != 0:
                                    surprise = ((actual - est) / abs(est)) * 100
                                    result["eps_surprise_pct"] = round(surprise, 1)
                            except:
                                pass
            except Exception:
                pass

        # วิธีที่ 3: ดึงจาก info แทน (Fallback)
        if not result["next_earnings"]:
            ts = info.get("earningsTimestamp")
            if ts:
                try:
                    result["next_earnings"] = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
                except:
                    pass

        # EPS จาก info ถ้ายังไม่มี
        if result["eps_actual"] is None:
            result["eps_actual"] = info.get("trailingEps")

        return result

    except Exception as e:
        print(f"  ⚠️ Earnings fetch error: {e}")
        return {}


def summarize_news_with_ai(news: List[Dict], ticker: str, current_change_pct: float = 0) -> str:
    """ใช้ AI สรุปข่าวให้เป็นภาษาไทยกระชับ"""
    if not news:
        return "ไม่พบข่าวล่าสุด"

    try:
        import ollama

        # รวบรวมข่าว
        news_text = ""
        for i, n in enumerate(news[:8], 1):
            news_text += f"\n{i}. [{n['date']}] {n['publisher']}\n"
            news_text += f"   หัวข้อ: {n['title']}\n"
            if n['summary']:
                news_text += f"   สรุป: {n['summary'][:300]}\n"

        change_context = ""
        if current_change_pct != 0:
            if current_change_pct > 0:
                change_context = f"วันนี้ราคาขึ้น +{current_change_pct:.2f}%"
            else:
                change_context = f"วันนี้ราคาลง {current_change_pct:.2f}%"

        prompt = f"""คุณเป็นนักข่าวการเงินมืออาชีพ
สรุปข่าวสำคัญของหุ้น {ticker} ให้เป็นภาษาไทย กระชับ ตรงประเด็น
{change_context}

ข่าวที่มี:
{news_text}

โปรดสรุปให้ครอบคลุม:
1. ข่าวที่กระทบราคามากที่สุด (1-2 ข่าว)
2. Catalyst เชิงบวกถ้ามี
3. Risk เชิงลบถ้ามี
4. ถ้ามีข่าว Earnings — บอกผลและ market reaction

ห้ามใช้ภาษาจีนเด็ดขาด ใช้ศัพท์การเงินอังกฤษได้ (เช่น CapEx, Revenue, Guidance)
ความยาว: 5-8 ประโยค กระชับ ไม่ต้องมีหัวข้อย่อย
"""

        response = ollama.chat(
            model="qwen2.5:14b",
            messages=[{"role": "user", "content": prompt}]
        )

        return response["message"]["content"]

    except Exception as e:
        return f"สรุปข่าวไม่ได้: {e}"


def get_news_context(ticker: str, current_change_pct: float = 0) -> Dict:
    """รวบรวม Context ข่าวทั้งหมด"""
    news = fetch_news(ticker, max_news=10)
    earnings = fetch_earnings_info(ticker)
    summary = summarize_news_with_ai(news, ticker, current_change_pct) if news else "ไม่มีข่าวล่าสุด"

    return {
        "news_count": len(news),
        "raw_news": news,
        "earnings": earnings,
        "summary": summary,
    }


# ==========================================
#  Test
# ==========================================

if __name__ == "__main__":
    ticker = "META"
    print(f"{'=' * 60}")
    print(f"  📰 News Context: {ticker}")
    print(f"{'=' * 60}\n")

    # ดึงข่าว
    news = fetch_news(ticker, max_news=5)
    print(f"  พบข่าว {len(news)} รายการ\n")

    for i, n in enumerate(news, 1):
        print(f"  [{i}] {n['publisher']} ({n['date']})")
        print(f"      {n['title']}")
        if n['summary']:
            print(f"      {n['summary'][:150]}...")
        print()

    # Earnings
    earnings = fetch_earnings_info(ticker)
    print(f"  📅 Earnings Info:")
    print(f"     Next:        {earnings.get('next_earnings')}")
    print(f"     Last:        {earnings.get('last_earnings')}")
    print(f"     EPS Actual:  {earnings.get('eps_actual')}")
    print(f"     EPS Est:     {earnings.get('eps_estimate')}")
    print(f"     Surprise:    {earnings.get('eps_surprise_pct')}%")

    # AI สรุป (ถ้ามีข่าว)
    if news:
        print(f"\n  🤖 AI สรุปข่าว...")
        summary = summarize_news_with_ai(news, ticker, current_change_pct=-8.55)
        print(f"\n{summary}")