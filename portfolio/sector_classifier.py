# === Sector & Correlation Group Database ===

SECTOR_DATABASE = {
    # AI Infrastructure
    "NVDA": {"sector": "Technology", "sub": "Semiconductors", "groups": ["AI_INFRA", "SEMIS"]},
    "AMD": {"sector": "Technology", "sub": "Semiconductors", "groups": ["AI_INFRA", "SEMIS"]},
    "AVGO": {"sector": "Technology", "sub": "Semiconductors", "groups": ["AI_INFRA", "SEMIS"]},
    "TSM": {"sector": "Technology", "sub": "Semiconductors", "groups": ["AI_INFRA", "SEMIS"]},
    "AMKR": {"sector": "Technology", "sub": "Semiconductors", "groups": ["AI_INFRA", "SEMIS"]},

    # Tech Megacap
    "MSFT": {"sector": "Technology", "sub": "Software", "groups": ["TECH_MEGA", "CLOUD", "AI_BENEFICIARY"]},
    "AAPL": {"sector": "Technology", "sub": "Hardware", "groups": ["TECH_MEGA", "CONSUMER_TECH"]},
    "GOOGL": {"sector": "Communication", "sub": "Interactive Media", "groups": ["TECH_MEGA", "AD_DEPENDENT", "AI_BENEFICIARY"]},
    "META": {"sector": "Communication", "sub": "Interactive Media", "groups": ["TECH_MEGA", "AD_DEPENDENT", "AI_BENEFICIARY"]},
    "AMZN": {"sector": "Consumer Disc", "sub": "E-commerce", "groups": ["TECH_MEGA", "CLOUD"]},

    # Software
    "ADBE": {"sector": "Technology", "sub": "Software", "groups": ["SOFTWARE", "AI_BENEFICIARY"]},
    "CRM": {"sector": "Technology", "sub": "Software", "groups": ["SOFTWARE", "CLOUD"]},
    "NOW": {"sector": "Technology", "sub": "Software", "groups": ["SOFTWARE", "CLOUD"]},

    # Fintech
    "SOFI": {"sector": "Financials", "sub": "Fintech", "groups": ["FINTECH"]},
    "HOOD": {"sector": "Financials", "sub": "Fintech", "groups": ["FINTECH"]},
    "COIN": {"sector": "Financials", "sub": "Fintech", "groups": ["FINTECH", "CRYPTO"]},

    # Cybersecurity
    "QLYS": {"sector": "Technology", "sub": "Cybersecurity", "groups": ["CYBER"]},
    "CRWD": {"sector": "Technology", "sub": "Cybersecurity", "groups": ["CYBER"]},
    "PANW": {"sector": "Technology", "sub": "Cybersecurity", "groups": ["CYBER"]},

    # Healthcare
    "LLY": {"sector": "Healthcare", "sub": "Pharma", "groups": ["PHARMA", "GLP1"]},
    "UNH": {"sector": "Healthcare", "sub": "Insurance", "groups": ["HEALTH_INSURANCE"]},
    "VEEV": {"sector": "Healthcare", "sub": "Health Tech", "groups": ["HEALTH_TECH", "SOFTWARE"]},

    # Bitcoin / Mining
    "IREN": {"sector": "Technology", "sub": "Crypto Mining", "groups": ["CRYPTO", "BITCOIN_PROXY"]},

    # Financials
    "JPM": {"sector": "Financials", "sub": "Banks", "groups": ["BANKS"]},
    "V": {"sector": "Financials", "sub": "Payments", "groups": ["PAYMENTS"]},

    # Energy
    "XOM": {"sector": "Energy", "sub": "Oil & Gas", "groups": ["OIL_GAS"]},
    "NEE": {"sector": "Energy", "sub": "Renewables", "groups": ["RENEWABLES"]},

    # EV
    "TSLA": {"sector": "Consumer Disc", "sub": "EV", "groups": ["EV", "AI_BENEFICIARY"]},
}


def get_sector(ticker):
    """ดึง Sector ของหุ้น"""
    if ticker in SECTOR_DATABASE:
        return SECTOR_DATABASE[ticker]["sector"]

    # ถ้าไม่มีใน Database ดึงจาก yfinance
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info
        return info.get("sector", "Unknown")
    except:
        return "Unknown"


def get_correlation_groups(ticker):
    """ดึง Correlation Groups (หุ้นที่เคลื่อนไหวคล้ายกัน)"""
    if ticker in SECTOR_DATABASE:
        return SECTOR_DATABASE[ticker]["groups"]
    return ["OTHER"]


def get_sector_exposure(holdings, portfolio_value=None):
    """คำนวณ % ของแต่ละ Sector ในพอร์ต"""
    sector_totals = {}

    # ใช้ portfolio_value ถ้ามี ไม่งั้นใช้ผลรวม holdings
    if portfolio_value is None:
        total_value = sum(h.get("market_value", 0) for h in holdings.values())
    else:
        total_value = portfolio_value

    if total_value == 0:
        return {}

    for ticker, holding in holdings.items():
        sector = get_sector(ticker)
        value = holding.get("market_value", 0)
        pct = (value / total_value) * 100

        if sector in sector_totals:
            sector_totals[sector] += pct
        else:
            sector_totals[sector] = pct

    return sector_totals


def get_group_exposure(holdings, portfolio_value=None):
    """คำนวณ % ของแต่ละ Correlation Group ในพอร์ต"""
    group_totals = {}

    if portfolio_value is None:
        total_value = sum(h.get("market_value", 0) for h in holdings.values())
    else:
        total_value = portfolio_value

    if total_value == 0:
        return {}

    for ticker, holding in holdings.items():
        groups = get_correlation_groups(ticker)
        value = holding.get("market_value", 0)
        pct = (value / total_value) * 100

        for group in groups:
            if group in group_totals:
                group_totals[group] += pct
            else:
                group_totals[group] = pct

    return group_totals

