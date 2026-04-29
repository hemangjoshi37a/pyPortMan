"""
Sector-wise P&L Attribution Manager for pyPortMan
Track performance by industry sector
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session

from models import Account, Holding, SectorPnL

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# Stock to sector mapping (simplified - in production, use a proper database or API)
STOCK_SECTOR_MAPPING = {
    # Banking & Finance
    "HDFCBANK": "Banking",
    "ICICIBANK": "Banking",
    "SBIN": "Banking",
    "KOTAKBANK": "Banking",
    "AXISBANK": "Banking",
    "INDUSINDBK": "Banking",
    "BAJFINANCE": "Financial Services",
    "HDFC": "Financial Services",

    # IT
    "INFY": "IT",
    "TCS": "IT",
    "WIPRO": "IT",
    "HCLTECH": "IT",
    "TECHM": "IT",
    "LT": "IT",

    # Oil & Gas
    "RELIANCE": "Oil & Gas",
    "ONGC": "Oil & Gas",
    "GAIL": "Oil & Gas",
    "BPCL": "Oil & Gas",
    "IOC": "Oil & Gas",

    # Pharma
    "SUNPHARMA": "Pharma",
    "DRREDDY": "Pharma",
    "CIPLA": "Pharma",
    "AUROPHARMA": "Pharma",
    "DIVISLAB": "Pharma",

    # FMCG
    "HINDUNILVR": "FMCG",
    "ITC": "FMCG",
    "NESTLEIND": "FMCG",
    "BRITANNIA": "FMCG",
    "HINDUSTAN UNILEVER": "FMCG",

    # Auto
    "MARUTI": "Auto",
    "TATAMOTORS": "Auto",
    "M&M": "Auto",
    "BAJAJ-AUTO": "Auto",
    "EICHERMOT": "Auto",
    "HEROMOTOCO": "Auto",

    # Metals
    "TATASTEEL": "Metals",
    "JSWSTEEL": "Metals",
    "HINDALCO": "Metals",
    "TATAMETALI": "Metals",

    # Telecom
    "BHARTIARTL": "Telecom",
    "VODAFONE IDEA": "Telecom",

    # Power
    "NTPC": "Power",
    "POWERGRID": "Power",
    "TATAPOWER": "Power",

    # Infrastructure
    "L&T": "Infrastructure",
    "DLF": "Infrastructure",
    "ADANIPORTS": "Infrastructure",

    # Consumer Durables
    "WHIRLPOOL": "Consumer Durables",
    "VOLTAS": "Consumer Durables",

    # Chemicals
    "UPL": "Chemicals",
    "PIIND": "Chemicals",
    "DEEPAKNTR": "Chemicals",
}


class SectorPnLManager:
    """Manager for sector-wise P&L attribution"""

    def __init__(self, db: Session):
        self.db = db

    def get_sector(self, stock: str) -> str:
        """
        Get sector for a stock symbol
        """
        return STOCK_SECTOR_MAPPING.get(stock.upper(), "Others")

    def calculate_sector_pnl(self, account_id: int) -> List[Dict[str, Any]]:
        """
        Calculate sector-wise P&L for an account
        """
        holdings = self.db.query(Holding).filter(
            Holding.account_id == account_id
        ).all()

        sector_data = {}

        for holding in holdings:
            sector = self.get_sector(holding.stock)

            if sector not in sector_data:
                sector_data[sector] = {
                    "sector": sector,
                    "stocks": [],
                    "investment_value": 0,
                    "current_value": 0,
                    "pnl": 0,
                    "count": 0
                }

            sector_data[sector]["stocks"].append(holding.stock)
            sector_data[sector]["investment_value"] += holding.qty * holding.avg_price
            sector_data[sector]["current_value"] += holding.current_value
            sector_data[sector]["pnl"] += holding.pnl
            sector_data[sector]["count"] += 1

        # Calculate percentages
        total_investment = sum(s["investment_value"] for s in sector_data.values())
        total_value = sum(s["current_value"] for s in sector_data.values())

        result = []
        for sector, data in sector_data.items():
            data["pnl_percent"] = (data["pnl"] / data["investment_value"] * 100) if data["investment_value"] > 0 else 0
            data["weight"] = (data["current_value"] / total_value * 100) if total_value > 0 else 0
            result.append(data)

        # Sort by weight descending
        result.sort(key=lambda x: x["weight"], reverse=True)

        return result

    def save_sector_pnl(self, account_id: int) -> List[SectorPnL]:
        """
        Save sector-wise P&L data to database
        """
        sector_pnl_data = self.calculate_sector_pnl(account_id)

        # Delete old records for this account
        self.db.query(SectorPnL).filter(
            SectorPnL.account_id == account_id
        ).delete()

        # Insert new records
        records = []
        for data in sector_pnl_data:
            for stock in data["stocks"]:
                # Get individual stock data
                holding = self.db.query(Holding).filter(
                    Holding.account_id == account_id,
                    Holding.stock == stock
                ).first()

                if holding:
                    record = SectorPnL(
                        account_id=account_id,
                        sector=data["sector"],
                        stock=stock,
                        investment_value=holding.qty * holding.avg_price,
                        current_value=holding.current_value,
                        pnl=holding.pnl,
                        pnl_percent=holding.pnl_percent,
                        weight=data["weight"],
                        recorded_at=datetime.utcnow()
                    )
                    self.db.add(record)
                    records.append(record)

        self.db.commit()

        logger.info(f"Saved sector P&L for account {account_id}")
        return records

    def get_sector_pnl_history(
        self,
        account_id: int,
        days: int = 30
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get historical sector-wise P&L data
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        records = self.db.query(SectorPnL).filter(
            SectorPnL.account_id == account_id,
            SectorPnL.recorded_at >= cutoff
        ).order_by(
            SectorPnL.recorded_at.asc()
        ).all()

        # Group by sector
        sector_history = {}

        for record in records:
            sector = record.sector
            if sector not in sector_history:
                sector_history[sector] = []

            sector_history[sector].append({
                "date": record.recorded_at.isoformat(),
                "pnl": record.pnl,
                "pnl_percent": record.pnl_percent,
                "weight": record.weight,
                "current_value": record.current_value
            })

        return sector_history

    def get_sector_comparison(
        self,
        account_id: int,
        sector: str
    ) -> Dict[str, Any]:
        """
        Get detailed comparison for a specific sector
        """
        holdings = self.db.query(Holding).filter(
            Holding.account_id == account_id
        ).all()

        sector_holdings = [h for h in holdings if self.get_sector(h.stock) == sector]

        if not sector_holdings:
            raise ValueError(f"No holdings found for sector {sector}")

        total_investment = sum(h.qty * h.avg_price for h in sector_holdings)
        total_value = sum(h.current_value for h in sector_holdings)
        total_pnl = sum(h.pnl for h in sector_holdings)

        # Find best and worst performers
        best = max(sector_holdings, key=lambda h: h.pnl_percent)
        worst = min(sector_holdings, key=lambda h: h.pnl_percent)

        return {
            "sector": sector,
            "stock_count": len(sector_holdings),
            "stocks": [h.stock for h in sector_holdings],
            "total_investment": total_investment,
            "total_value": total_value,
            "total_pnl": total_pnl,
            "pnl_percent": (total_pnl / total_investment * 100) if total_investment > 0 else 0,
            "best_performer": {
                "stock": best.stock,
                "pnl": best.pnl,
                "pnl_percent": best.pnl_percent
            },
            "worst_performer": {
                "stock": worst.stock,
                "pnl": worst.pnl,
                "pnl_percent": worst.pnl_percent
            }
        }

    def get_sector_summary(self, account_id: int) -> Dict[str, Any]:
        """
        Get summary of sector-wise P&L
        """
        sector_pnl = self.calculate_sector_pnl(account_id)

        total_investment = sum(s["investment_value"] for s in sector_pnl)
        total_value = sum(s["current_value"] for s in sector_pnl)
        total_pnl = sum(s["pnl"] for s in sector_pnl)

        # Find best and worst sectors
        if sector_pnl:
            best_sector = max(sector_pnl, key=lambda s: s["pnl_percent"])
            worst_sector = min(sector_pnl, key=lambda s: s["pnl_percent"])
        else:
            best_sector = None
            worst_sector = None

        return {
            "total_investment": total_investment,
            "total_value": total_value,
            "total_pnl": total_pnl,
            "pnl_percent": (total_pnl / total_investment * 100) if total_investment > 0 else 0,
            "sector_count": len(sector_pnl),
            "best_sector": best_sector["sector"] if best_sector else None,
            "best_sector_pnl_pct": best_sector["pnl_percent"] if best_sector else 0,
            "worst_sector": worst_sector["sector"] if worst_sector else None,
            "worst_sector_pnl_pct": worst_sector["pnl_percent"] if worst_sector else 0,
            "sectors": sector_pnl
        }

    def get_sector_attribution(self, account_id: int) -> Dict[str, Any]:
        """
        Analyze portfolio performance attribution by sector
        """
        sector_pnl = self.calculate_sector_pnl(account_id)

        total_pnl = sum(s["pnl"] for s in sector_pnl)
        total_value = sum(s["current_value"] for s in sector_pnl)

        attribution = []
        for sector in sector_pnl:
            contribution = (sector["pnl"] / total_pnl * 100) if total_pnl != 0 else 0
            attribution.append({
                "sector": sector["sector"],
                "pnl": sector["pnl"],
                "pnl_percent": sector["pnl_percent"],
                "weight": sector["weight"],
                "contribution_to_total": contribution,
                "stock_count": sector["count"]
            })

        # Sort by contribution
        attribution.sort(key=lambda x: abs(x["contribution_to_total"]), reverse=True)

        return {
            "total_pnl": total_pnl,
            "total_value": total_value,
            "attribution": attribution
        }
