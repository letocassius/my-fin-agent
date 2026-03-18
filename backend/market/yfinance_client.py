"""Yahoo Finance client for market data retrieval.

Provides helpers for current price, OHLCV history, technical indicators,
financial statements, and trend classification — all backed by ``yfinance``.
"""

from __future__ import annotations

import logging

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

PERIOD_MAP = {
    "1d": "1d",
    "5d": "5d",
    "7d": "5d",  # yfinance doesn't have 7d, use 5d (trading days)
    "1mo": "1mo",
    "30d": "1mo",
    "3mo": "3mo",
    "6mo": "6mo",
    "1y": "1y",
    "2y": "2y",
    "5y": "5y",
    "ytd": "ytd",
    "max": "max",
}

INTERVAL_MAP = {
    "1d": "1m",
    "5d": "5m",
    "7d": "5m",
    "1mo": "1d",
    "30d": "1d",
    "3mo": "1d",
    "6mo": "1wk",
    "1y": "1wk",
    "2y": "1wk",
    "5y": "1mo",
    "ytd": "1d",
    "max": "1mo",
}


def get_current_price(ticker: str) -> dict:
    """
    Fetch current price and key statistics for a ticker.

    Returns a dict with: ticker, price, change, change_pct, volume,
    market_cap, currency, exchange, company_name, previous_close,
    day_high, day_low, fifty_two_week_high, fifty_two_week_low
    """
    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info

        # Try fast_info first (more reliable for current price)
        fast = stock.fast_info

        price = None
        try:
            price = fast.last_price
        except Exception:
            pass

        if price is None:
            price = info.get("currentPrice") or info.get("regularMarketPrice")

        if price is None:
            # Fall back to recent history
            hist = stock.history(period="1d", interval="1m")
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])

        if price is None:
            return {"error": f"Could not retrieve price for {ticker}"}

        previous_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
        if previous_close is None:
            try:
                previous_close = fast.previous_close
            except Exception:
                previous_close = None

        change = None
        change_pct = None
        if previous_close and previous_close > 0:
            change = round(price - previous_close, 4)
            change_pct = round((change / previous_close) * 100, 4)

        market_cap = info.get("marketCap")
        try:
            if market_cap is None:
                market_cap = fast.market_cap
        except Exception:
            pass

        volume = info.get("volume") or info.get("regularMarketVolume")
        try:
            if volume is None:
                volume = fast.three_month_average_volume
        except Exception:
            pass

        return {
            "ticker": ticker.upper(),
            "company_name": info.get("longName") or info.get("shortName", ticker.upper()),
            "price": round(float(price), 4),
            "previous_close": round(float(previous_close), 4) if previous_close else None,
            "change": round(float(change), 4) if change is not None else None,
            "change_pct": round(float(change_pct), 4) if change_pct is not None else None,
            "volume": int(volume) if volume else None,
            "market_cap": int(market_cap) if market_cap else None,
            "currency": info.get("currency", "USD"),
            "exchange": info.get("exchange", ""),
            "day_high": round(float(info["dayHigh"]), 4) if info.get("dayHigh") else None,
            "day_low": round(float(info["dayLow"]), 4) if info.get("dayLow") else None,
            "fifty_two_week_high": round(float(info["fiftyTwoWeekHigh"]), 4) if info.get("fiftyTwoWeekHigh") else None,
            "fifty_two_week_low": round(float(info["fiftyTwoWeekLow"]), 4) if info.get("fiftyTwoWeekLow") else None,
            "pe_ratio": round(float(info["trailingPE"]), 2) if info.get("trailingPE") else None,
            "forward_pe": round(float(info["forwardPE"]), 2) if info.get("forwardPE") else None,
            "eps": round(float(info["trailingEps"]), 4) if info.get("trailingEps") else None,
            "dividend_yield": round(float(info["dividendYield"]) * 100, 4) if info.get("dividendYield") else None,
            "sector": info.get("sector"),
            "industry": info.get("industry"),
        }

    except Exception as e:
        logger.exception(f"Error fetching price for {ticker}")
        return {"error": f"Failed to fetch data for {ticker}: {str(e)}"}


def get_price_history(ticker: str, period: str = "1mo") -> dict:
    """
    Fetch OHLCV price history for a ticker.

    Returns a dict with: ticker, period, data (list of OHLCV dicts),
    start_price, end_price, period_change, period_change_pct, trend
    """
    try:
        yf_period = PERIOD_MAP.get(period, "1mo")
        yf_interval = INTERVAL_MAP.get(period, "1d")

        stock = yf.Ticker(ticker.upper())
        hist = stock.history(period=yf_period, interval=yf_interval)

        if hist.empty:
            return {"error": f"No historical data found for {ticker}"}

        data = []
        for timestamp, row in hist.iterrows():
            data.append({
                "date": timestamp.strftime("%Y-%m-%d %H:%M") if yf_interval in ("1m", "5m") else timestamp.strftime("%Y-%m-%d"),
                "open": round(float(row["Open"]), 4),
                "high": round(float(row["High"]), 4),
                "low": round(float(row["Low"]), 4),
                "close": round(float(row["Close"]), 4),
                "volume": int(row["Volume"]) if row["Volume"] else 0,
            })

        if len(data) < 2:
            return {"error": f"Insufficient historical data for {ticker}"}

        start_price = data[0]["close"]
        end_price = data[-1]["close"]
        period_change = round(end_price - start_price, 4)
        period_change_pct = round((period_change / start_price) * 100, 4) if start_price > 0 else 0

        closes = [d["close"] for d in data]
        trend = classify_trend(closes)

        return {
            "ticker": ticker.upper(),
            "period": period,
            "interval": yf_interval,
            "data_points": len(data),
            "start_date": data[0]["date"],
            "end_date": data[-1]["date"],
            "start_price": start_price,
            "end_price": end_price,
            "period_high": round(max(d["high"] for d in data), 4),
            "period_low": round(min(d["low"] for d in data), 4),
            "period_change": period_change,
            "period_change_pct": period_change_pct,
            "trend": trend,
            "data": data,
        }

    except Exception as e:
        logger.exception(f"Error fetching history for {ticker}")
        return {"error": f"Failed to fetch history for {ticker}: {str(e)}"}


def get_stock_info(ticker: str) -> dict:
    """
    Fetch detailed company information for a ticker.
    """
    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info

        return {
            "ticker": ticker.upper(),
            "company_name": info.get("longName") or info.get("shortName", ticker.upper()),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "country": info.get("country"),
            "website": info.get("website"),
            "description": info.get("longBusinessSummary"),
            "employees": info.get("fullTimeEmployees"),
            "market_cap": info.get("marketCap"),
            "revenue": info.get("totalRevenue"),
            "gross_margins": round(float(info["grossMargins"]) * 100, 2) if info.get("grossMargins") else None,
            "operating_margins": round(float(info["operatingMargins"]) * 100, 2) if info.get("operatingMargins") else None,
            "profit_margins": round(float(info["profitMargins"]) * 100, 2) if info.get("profitMargins") else None,
            "return_on_equity": round(float(info["returnOnEquity"]) * 100, 2) if info.get("returnOnEquity") else None,
            "debt_to_equity": round(float(info["debtToEquity"]), 2) if info.get("debtToEquity") else None,
            "current_ratio": round(float(info["currentRatio"]), 2) if info.get("currentRatio") else None,
            "beta": round(float(info["beta"]), 2) if info.get("beta") else None,
            "analyst_target_price": info.get("targetMeanPrice"),
            "recommendation": info.get("recommendationKey"),
        }

    except Exception as e:
        logger.exception(f"Error fetching info for {ticker}")
        return {"error": f"Failed to fetch info for {ticker}: {str(e)}"}


def get_technical_indicators(ticker: str, period: str = "3mo") -> dict:
    """
    Compute SMA-20/50, RSI-14, MACD (12/26/9), and Bollinger Bands (20, 2σ).

    Uses 6 months of daily history for sufficient lookback. Each indicator
    includes a signal interpretation string.
    """
    try:
        stock = yf.Ticker(ticker.upper())
        hist = stock.history(period="6mo", interval="1d")

        if hist.empty:
            return {"error": f"No historical data for {ticker}"}

        closes = hist["Close"].dropna()

        if len(closes) < 20:
            return {"error": f"Insufficient data for technical indicators ({len(closes)} rows)"}

        as_of = closes.index[-1].strftime("%Y-%m-%d")
        current_price = round(float(closes.iloc[-1]), 4)

        # SMA-20
        sma_20_series = closes.rolling(20).mean()
        sma_20 = round(float(sma_20_series.iloc[-1]), 4) if not pd.isna(sma_20_series.iloc[-1]) else None

        # SMA-50 (requires >= 52 rows to be meaningful)
        sma_50 = None
        if len(closes) >= 52:
            sma_50_series = closes.rolling(50).mean()
            val = sma_50_series.iloc[-1]
            sma_50 = round(float(val), 4) if not pd.isna(val) else None

        sma_20_signal = None
        if sma_20 is not None:
            sma_20_signal = "above" if current_price > sma_20 else "below"

        sma_50_signal = None
        if sma_50 is not None:
            sma_50_signal = "above" if current_price > sma_50 else "below"

        # RSI-14 using Wilder's WSMA (ewm with com=13)
        delta = closes.diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_gain = gain.ewm(com=13, adjust=False).mean()
        avg_loss = loss.ewm(com=13, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, float("nan"))
        rsi_series = 100 - (100 / (1 + rs))
        rsi_14 = round(float(rsi_series.iloc[-1]), 2) if not pd.isna(rsi_series.iloc[-1]) else None

        rsi_signal = None
        if rsi_14 is not None:
            if rsi_14 >= 70:
                rsi_signal = "overbought"
            elif rsi_14 <= 30:
                rsi_signal = "oversold"
            else:
                rsi_signal = "neutral"

        # MACD (12, 26, 9) — all EWMs with adjust=False
        ema12 = closes.ewm(span=12, adjust=False).mean()
        ema26 = closes.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        histogram = macd_line - signal_line

        macd = round(float(macd_line.iloc[-1]), 4) if not pd.isna(macd_line.iloc[-1]) else None
        macd_signal_line = round(float(signal_line.iloc[-1]), 4) if not pd.isna(signal_line.iloc[-1]) else None
        macd_histogram = round(float(histogram.iloc[-1]), 4) if not pd.isna(histogram.iloc[-1]) else None

        macd_crossover = None
        if macd is not None and macd_signal_line is not None:
            if len(histogram) >= 2:
                prev = float(histogram.iloc[-2])
                curr = float(histogram.iloc[-1])
                if prev < 0 and curr >= 0:
                    macd_crossover = "bullish"
                elif prev > 0 and curr <= 0:
                    macd_crossover = "bearish"
                else:
                    macd_crossover = "bullish" if curr > 0 else "bearish"

        # Bollinger Bands (20, 2σ) — rolling std uses ddof=1 by default
        bb_middle_series = closes.rolling(20).mean()
        bb_std_series = closes.rolling(20).std()
        bb_middle = round(float(bb_middle_series.iloc[-1]), 4) if not pd.isna(bb_middle_series.iloc[-1]) else None
        bb_std = float(bb_std_series.iloc[-1]) if not pd.isna(bb_std_series.iloc[-1]) else None

        bb_upper = round(bb_middle + 2 * bb_std, 4) if bb_middle and bb_std else None
        bb_lower = round(bb_middle - 2 * bb_std, 4) if bb_middle and bb_std else None
        bb_width_pct = round(((bb_upper - bb_lower) / bb_middle) * 100, 2) if bb_middle and bb_upper and bb_lower else None

        bb_signal = None
        if bb_upper and bb_lower and bb_middle:
            if current_price >= bb_upper:
                bb_signal = "near_upper_band"
            elif current_price <= bb_lower:
                bb_signal = "near_lower_band"
            else:
                bb_signal = "within_bands"

        return {
            "ticker": ticker.upper(),
            "as_of": as_of,
            "current_price": current_price,
            "sma_20": sma_20,
            "sma_50": sma_50,
            "sma_20_signal": sma_20_signal,
            "sma_50_signal": sma_50_signal,
            "rsi_14": rsi_14,
            "rsi_signal": rsi_signal,
            "macd": macd,
            "macd_signal_line": macd_signal_line,
            "macd_histogram": macd_histogram,
            "macd_crossover": macd_crossover,
            "bb_upper": bb_upper,
            "bb_middle": bb_middle,
            "bb_lower": bb_lower,
            "bb_width_pct": bb_width_pct,
            "bb_signal": bb_signal,
            "source": "yfinance",
        }

    except Exception as e:
        logger.exception(f"Error computing technical indicators for {ticker}")
        return {"error": f"Failed to compute technical indicators for {ticker}: {str(e)}"}


def _df_to_dict(df, rows_of_interest: list[str]) -> dict:
    """Extract specified rows from a DataFrame as {metric: {period_str: value}}."""
    result = {}
    if df is None or df.empty:
        return result
    for row in rows_of_interest:
        if row in df.index:
            row_data = {}
            for col in df.columns:
                try:
                    period_str = col.strftime("%Y-%m-%d") if hasattr(col, "strftime") else str(col)
                    val = df.loc[row, col]
                    row_data[period_str] = float(val) if pd.notna(val) else None
                except Exception:
                    pass
            result[row] = row_data
    return result


def get_financial_statements(ticker: str, quarterly: bool = False) -> dict:
    """
    Fetch income statement, balance sheet, and cash flow from yfinance.

    Set quarterly=True for recent quarterly data instead of annual.
    Returns only key metrics to keep context manageable.
    """
    try:
        stock = yf.Ticker(ticker.upper())

        if quarterly:
            income_df = stock.quarterly_financials
            balance_df = stock.quarterly_balance_sheet
            cashflow_df = stock.quarterly_cashflow
            period_type = "quarterly"
        else:
            income_df = stock.financials
            balance_df = stock.balance_sheet
            cashflow_df = stock.cashflow
            period_type = "annual"

        income_rows = [
            "Total Revenue", "Gross Profit", "Operating Income",
            "Net Income", "EBITDA", "Basic EPS", "Diluted EPS",
        ]
        balance_rows = [
            "Total Assets", "Total Liabilities Net Minority Interest",
            "Stockholders Equity", "Cash And Cash Equivalents", "Total Debt",
        ]
        cashflow_rows = [
            "Operating Cash Flow", "Free Cash Flow", "Capital Expenditure",
        ]

        return {
            "ticker": ticker.upper(),
            "period_type": period_type,
            "income_statement": _df_to_dict(income_df, income_rows),
            "balance_sheet": _df_to_dict(balance_df, balance_rows),
            "cash_flow": _df_to_dict(cashflow_df, cashflow_rows),
            "source": "yfinance",
        }

    except Exception as e:
        logger.exception(f"Error fetching financial statements for {ticker}")
        return {"error": f"Failed to fetch financial statements for {ticker}: {str(e)}"}


def classify_trend(prices: list[float]) -> str:
    """
    Classify price trend as 'uptrend', 'downtrend', or 'sideways'.

    Uses a combination of linear regression slope and percentage change
    to determine trend direction.
    """
    if not prices or len(prices) < 3:
        return "sideways"

    n = len(prices)
    start = prices[0]
    end = prices[-1]

    if start <= 0:
        return "sideways"

    pct_change = (end - start) / start * 100

    # Calculate linear regression slope (normalized)
    x_mean = (n - 1) / 2
    y_mean = sum(prices) / n

    numerator = sum((i - x_mean) * (prices[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return "sideways"

    slope = numerator / denominator
    # Normalize slope as percentage of mean price
    normalized_slope = (slope / y_mean) * 100

    # Classify based on both overall change and slope direction
    if pct_change > 3 and normalized_slope > 0:
        return "uptrend"
    elif pct_change < -3 and normalized_slope < 0:
        return "downtrend"
    else:
        return "sideways"
