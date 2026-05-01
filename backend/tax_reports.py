"""
Tax Reports Manager for pyPortMan
Generate tax-ready statements for monthly/quarterly reporting
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
import json

from models import Account, Holding, Order, TaxReport

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


class TaxReportManager:
    """Manager for tax reports"""

    def __init__(self, db: Session):
        self.db = db

    def generate_tax_report(
        self,
        account_id: int,
        report_type: str = "MONTHLY",
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None
    ) -> TaxReport:
        """
        Generate tax report for a given period
        report_type: MONTHLY, QUARTERLY, YEARLY
        """
        # Determine period dates
        now = datetime.utcnow()

        if report_type == "MONTHLY":
            if not period_start:
                period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if not period_end:
                # Last day of current month
                next_month = period_start.replace(day=28) + timedelta(days=4)
                period_end = next_month - timedelta(days=next_month.day)
                period_end = period_end.replace(hour=23, minute=59, second=59)

        elif report_type == "QUARTERLY":
            if not period_start:
                # Start of current quarter
                quarter = (now.month - 1) // 3 + 1
                period_start = datetime(now.year, (quarter - 1) * 3 + 1, 1)
            if not period_end:
                # End of current quarter
                period_end = datetime(
                    now.year,
                    period_start.month + 2,
                    31,
                    23, 59, 59
                )

        elif report_type == "YEARLY":
            if not period_start:
                period_start = datetime(now.year, 4, 1)  # Indian financial year starts April 1
            if not period_end:
                period_end = datetime(now.year + 1, 3, 31, 23, 59, 59)

        # Get holdings
        holdings = self.db.query(Holding).filter(
            Holding.account_id == account_id
        ).all()

        # Get completed orders in the period
        orders = self.db.query(Order).filter(
            Order.account_id == account_id,
            Order.placed_at >= period_start,
            Order.placed_at <= period_end,
            Order.status == "COMPLETE"
        ).all()

        # Calculate tax data
        report_data = self._calculate_tax_data(holdings, orders, period_start, period_end)

        # Save report
        report = TaxReport(
            account_id=account_id,
            report_type=report_type,
            period_start=period_start,
            period_end=period_end,
            report_data=json.dumps(report_data)
        )

        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)

        logger.info(f"Generated {report_type} tax report for account {account_id}")
        return report

    def _calculate_tax_data(
        self,
        holdings: List[Holding],
        orders: List[Order],
        period_start: datetime,
        period_end: datetime
    ) -> Dict[str, Any]:
        """
        Calculate tax data from holdings and orders
        """
        # Holdings summary
        holdings_summary = []
        total_investment = 0
        total_current_value = 0

        for holding in holdings:
            investment = holding.qty * holding.avg_price
            total_investment += investment
            total_current_value += holding.current_value

            holdings_summary.append({
                "stock": holding.stock,
                "isin": holding.isin,
                "quantity": holding.qty,
                "avg_price": holding.avg_price,
                "current_price": holding.ltp,
                "investment_value": investment,
                "current_value": holding.current_value,
                "pnl": holding.pnl,
                "pnl_percent": holding.pnl_percent
            })

        # Orders summary (trades)
        trades_summary = []
        short_term_trades = []  # < 1 year
        long_term_trades = []  # >= 1 year

        for order in orders:
            # Simplified trade data (in production, use actual trade data)
            holding_period_days = (datetime.utcnow() - order.placed_at).days

            trade_data = {
                "stock": order.stock,
                "exchange": order.exchange,
                "transaction_type": order.transaction_type,
                "quantity": order.qty,
                "price": order.price,
                "value": order.qty * order.price,
                "date": order.placed_at.isoformat(),
                "order_id": order.order_id
            }

            trades_summary.append(trade_data)

            if holding_period_days < 365:
                short_term_trades.append(trade_data)
            else:
                long_term_trades.append(trade_data)

        # Calculate totals
        total_pnl = sum(h.pnl for h in holdings)
        total_short_term_pnl = sum(t.get("pnl", 0) for t in short_term_trades)
        total_long_term_pnl = sum(t.get("pnl", 0) for t in long_term_trades)

        return {
            "report_period": {
                "start": period_start.isoformat(),
                "end": period_end.isoformat()
            },
            "portfolio_summary": {
                "total_investment": total_investment,
                "total_current_value": total_current_value,
                "total_pnl": total_pnl,
                "pnl_percent": (total_pnl / total_investment * 100) if total_investment > 0 else 0,
                "holdings_count": len(holdings)
            },
            "holdings": holdings_summary,
            "trades": {
                "total_trades": len(trades_summary),
                "short_term_trades": len(short_term_trades),
                "long_term_trades": len(long_term_trades),
                "short_term_pnl": total_short_term_pnl,
                "long_term_pnl": total_long_term_pnl
            },
            "tax_implications": {
                "short_term_gains": max(0, total_short_term_pnl),
                "short_term_losses": min(0, total_short_term_pnl),
                "long_term_gains": max(0, total_long_term_pnl),
                "long_term_losses": min(0, total_long_term_pnl),
                "note": "Short-term gains taxed at 15%, Long-term gains taxed at 10% (above ₹1 lakh)"
            },
            "generated_at": datetime.utcnow().isoformat()
        }

    def get_tax_reports(
        self,
        account_id: int,
        report_type: Optional[str] = None
    ) -> List[TaxReport]:
        """
        Get tax reports with optional filter
        """
        query = self.db.query(TaxReport).filter(
            TaxReport.account_id == account_id
        )

        if report_type:
            query = query.filter(TaxReport.report_type == report_type)

        return query.order_by(TaxReport.generated_at.desc()).all()

    def get_tax_report(self, report_id: int) -> Dict[str, Any]:
        """
        Get a specific tax report
        """
        report = self.db.query(TaxReport).filter(
            TaxReport.id == report_id
        ).first()

        if not report:
            raise ValueError(f"Tax report {report_id} not found")

        return json.loads(report.report_data)

    def export_tax_report(
        self,
        report_id: int,
        format: str = "json"
    ) -> str:
        """
        Export tax report in specified format
        format: json, csv
        """
        report_data = self.get_tax_report(report_id)

        if format == "json":
            return json.dumps(report_data, indent=2)
        elif format == "csv":
            # Generate CSV format
            csv_lines = []

            # Holdings section
            csv_lines.append("=== HOLDINGS ===")
            csv_lines.append("Stock,ISIN,Quantity,Avg Price,Current Price,Investment,Current Value,P&L,P&L %")
            for holding in report_data.get("holdings", []):
                csv_lines.append(
                    f"{holding['stock']},{holding['isin']},{holding['quantity']},"
                    f"{holding['avg_price']},{holding['current_price']},"
                    f"{holding['investment_value']},{holding['current_value']},"
                    f"{holding['pnl']},{holding['pnl_percent']}"
                )

            # Trades section
            csv_lines.append("\n=== TRADES ===")
            csv_lines.append("Stock,Exchange,Type,Quantity,Price,Value,Date,Order ID")
            for trade in report_data.get("trades_summary", []):
                csv_lines.append(
                    f"{trade['stock']},{trade['exchange']},{trade['transaction_type']},"
                    f"{trade['quantity']},{trade['price']},{trade['value']},"
                    f"{trade['date']},{trade['order_id']}"
                )

            return "\n".join(csv_lines)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def get_tax_summary(self, account_id: int, financial_year: Optional[int] = None) -> Dict[str, Any]:
        """
        Get tax summary for a financial year
        """
        if not financial_year:
            now = datetime.utcnow()
            # Indian financial year: April to March
            if now.month >= 4:
                financial_year = now.year
            else:
                financial_year = now.year - 1

        # Get yearly report
        period_start = datetime(financial_year, 4, 1)
        period_end = datetime(financial_year + 1, 3, 31, 23, 59, 59)

        report = self.db.query(TaxReport).filter(
            TaxReport.account_id == account_id,
            TaxReport.report_type == "YEARLY",
            TaxReport.period_start == period_start
        ).first()

        if not report:
            # Generate new report
            report = self.generate_tax_report(
                account_id,
                "YEARLY",
                period_start,
                period_end
            )

        report_data = json.loads(report.report_data)

        return {
            "financial_year": f"{financial_year}-{financial_year + 1}",
            "period": {
                "start": period_start.strftime("%Y-%m-%d"),
                "end": period_end.strftime("%Y-%m-%d")
            },
            "total_pnl": report_data["portfolio_summary"]["total_pnl"],
            "short_term_gains": report_data["tax_implications"]["short_term_gains"],
            "short_term_losses": report_data["tax_implications"]["short_term_losses"],
            "long_term_gains": report_data["tax_implications"]["long_term_gains"],
            "long_term_losses": report_data["tax_implications"]["long_term_losses"],
            "estimated_tax": self._calculate_estimated_tax(report_data["tax_implications"])
        }

    def _calculate_estimated_tax(self, tax_implications: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate estimated tax based on Indian tax rules
        """
        short_term_gains = tax_implications["short_term_gains"]
        short_term_losses = abs(tax_implications["short_term_losses"])
        long_term_gains = tax_implications["long_term_gains"]
        long_term_losses = abs(tax_implications["long_term_losses"])

        # Short-term capital gains tax: 15%
        net_short_term = short_term_gains - short_term_losses
        short_term_tax = max(0, net_short_term * 0.15)

        # Long-term capital gains tax: 10% on gains above ₹1 lakh
        net_long_term = long_term_gains - long_term_losses
        taxable_long_term = max(0, net_long_term - 100000)
        long_term_tax = taxable_long_term * 0.10

        return {
            "short_term_tax": round(short_term_tax, 2),
            "long_term_tax": round(long_term_tax, 2),
            "total_tax": round(short_term_tax + long_term_tax, 2)
        }
