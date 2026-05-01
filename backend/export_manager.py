"""
Export Module for pyPortMan
PDF, Excel, and CSV export functionality for portfolio reports
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
import pandas as pd
import io
import json

from models import Account, Holding, Position, Order, PortfolioSnapshot, GTTOrder

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


class ExportManager:
    """
    Manager for exporting portfolio data to various formats
    Supports PDF, Excel, and CSV exports
    """

    def __init__(self, db: Session):
        self.db = db

    def export_holdings_to_csv(
        self,
        account_id: Optional[int] = None
    ) -> str:
        """
        Export holdings to CSV format

        Args:
            account_id: Optional account ID filter

        Returns:
            CSV string
        """
        query = self.db.query(Holding)

        if account_id:
            query = query.filter(Holding.account_id == account_id)

        holdings = query.all()

        # Create DataFrame
        data = []
        for h in holdings:
            data.append({
                "Stock": h.stock,
                "Exchange": h.exchange,
                "Quantity": h.qty,
                "Average Price": h.avg_price,
                "LTP": h.ltp,
                "Current Value": h.current_value,
                "P&L": h.pnl,
                "P&L %": h.pnl_percent,
                "Product": h.product,
                "Last Updated": h.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            })

        df = pd.DataFrame(data)
        return df.to_csv(index=False)

    def export_positions_to_csv(
        self,
        account_id: Optional[int] = None
    ) -> str:
        """
        Export positions to CSV format

        Args:
            account_id: Optional account ID filter

        Returns:
            CSV string
        """
        query = self.db.query(Position)

        if account_id:
            query = query.filter(Position.account_id == account_id)

        positions = query.all()

        # Create DataFrame
        data = []
        for p in positions:
            data.append({
                "Stock": p.stock,
                "Exchange": p.exchange,
                "Quantity": p.qty,
                "Average Price": p.avg_price,
                "LTP": p.ltp,
                "P&L": p.pnl,
                "P&L %": p.pnl_percent,
                "Product": p.product,
                "Product Type": p.product_type,
                "Buy Quantity": p.buy_qty,
                "Sell Quantity": p.sell_qty,
                "Unrealized P&L": p.unrealized_pnl,
                "Realized P&L": p.realized_pnl,
                "Last Updated": p.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            })

        df = pd.DataFrame(data)
        return df.to_csv(index=False)

    def export_orders_to_csv(
        self,
        account_id: Optional[int] = None,
        days: int = 30
    ) -> str:
        """
        Export orders to CSV format

        Args:
            account_id: Optional account ID filter
            days: Number of days to export

        Returns:
            CSV string
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = self.db.query(Order).filter(Order.placed_at >= cutoff_date)

        if account_id:
            query = query.filter(Order.account_id == account_id)

        orders = query.order_by(Order.placed_at.desc()).all()

        # Create DataFrame
        data = []
        for o in orders:
            data.append({
                "Order ID": o.order_id,
                "Stock": o.stock,
                "Exchange": o.exchange,
                "Quantity": o.qty,
                "Price": o.price,
                "Order Type": o.order_type,
                "Transaction Type": o.transaction_type,
                "Status": o.status,
                "Product": o.product,
                "Validity": o.validity,
                "Variety": o.variety,
                "Placed At": o.placed_at.strftime("%Y-%m-%d %H:%M:%S")
            })

        df = pd.DataFrame(data)
        return df.to_csv(index=False)

    def export_gtt_orders_to_csv(
        self,
        account_id: Optional[int] = None
    ) -> str:
        """
        Export GTT orders to CSV format

        Args:
            account_id: Optional account ID filter

        Returns:
            CSV string
        """
        query = self.db.query(GTTOrder)

        if account_id:
            query = query.filter(GTTOrder.account_id == account_id)

        gtt_orders = query.order_by(GTTOrder.created_at.desc()).all()

        # Create DataFrame
        data = []
        for g in gtt_orders:
            data.append({
                "GTT ID": g.gtt_id,
                "Stock": g.stock,
                "Exchange": g.exchange,
                "Quantity": g.qty,
                "Buy Price": g.buy_price,
                "Target Price": g.target_price,
                "Stop Loss": g.sl_price,
                "Allocation %": g.allocation_pct,
                "Status": g.status,
                "Trigger Type": g.trigger_type,
                "Triggered At": g.triggered_at.strftime("%Y-%m-%d %H:%M:%S") if g.triggered_at else "",
                "Created At": g.created_at.strftime("%Y-%m-%d %H:%M:%S")
            })

        df = pd.DataFrame(data)
        return df.to_csv(index=False)

    def export_portfolio_summary_to_csv(
        self,
        account_id: int
    ) -> str:
        """
        Export portfolio summary to CSV format

        Args:
            account_id: Account ID

        Returns:
            CSV string
        """
        account = self.db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise ValueError("Account not found")

        holdings = self.db.query(Holding).filter(Holding.account_id == account_id).all()
        positions = self.db.query(Position).filter(Position.account_id == account_id).all()

        # Calculate summary
        total_value = sum(h.current_value for h in holdings)
        investment_value = sum(h.qty * h.avg_price for h in holdings)
        total_pnl = sum(h.pnl for h in holdings) + sum(p.pnl for p in positions)

        # Create summary data
        data = [{
            "Account Name": account.name,
            "Account ID": account.account_id,
            "Total Value": total_value,
            "Investment Value": investment_value,
            "Total P&L": total_pnl,
            "P&L %": (total_pnl / investment_value * 100) if investment_value > 0 else 0,
            "Holdings Count": len(holdings),
            "Positions Count": len(positions),
            "Last Updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        }]

        df = pd.DataFrame(data)
        return df.to_csv(index=False)

    def export_to_excel(
        self,
        account_id: int,
        include_holdings: bool = True,
        include_positions: bool = True,
        include_orders: bool = True,
        include_gtt: bool = True,
        days: int = 30
    ) -> bytes:
        """
        Export portfolio data to Excel format

        Args:
            account_id: Account ID
            include_holdings: Include holdings sheet
            include_positions: Include positions sheet
            include_orders: Include orders sheet
            include_gtt: Include GTT orders sheet
            days: Number of days for orders

        Returns:
            Excel file as bytes
        """
        output = io.BytesIO()

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Summary sheet
            summary_data = [{
                "Metric": "Value",
                "Account Name": self.db.query(Account).filter(Account.id == account_id).first().name,
                "Export Date": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            }]
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)

            # Holdings sheet
            if include_holdings:
                holdings_csv = self.export_holdings_to_csv(account_id)
                holdings_df = pd.read_csv(io.StringIO(holdings_csv))
                holdings_df.to_excel(writer, sheet_name='Holdings', index=False)

            # Positions sheet
            if include_positions:
                positions_csv = self.export_positions_to_csv(account_id)
                positions_df = pd.read_csv(io.StringIO(positions_csv))
                positions_df.to_excel(writer, sheet_name='Positions', index=False)

            # Orders sheet
            if include_orders:
                orders_csv = self.export_orders_to_csv(account_id, days)
                orders_df = pd.read_csv(io.StringIO(orders_csv))
                orders_df.to_excel(writer, sheet_name='Orders', index=False)

            # GTT sheet
            if include_gtt:
                gtt_csv = self.export_gtt_orders_to_csv(account_id)
                gtt_df = pd.read_csv(io.StringIO(gtt_csv))
                gtt_df.to_excel(writer, sheet_name='GTT Orders', index=False)

        output.seek(0)
        return output.getvalue()

    def export_to_pdf(
        self,
        account_id: int,
        report_type: str = "portfolio"
    ) -> bytes:
        """
        Export portfolio data to PDF format

        Args:
            account_id: Account ID
            report_type: Type of report (portfolio, holdings, positions, orders)

        Returns:
            PDF file as bytes
        """
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
        except ImportError:
            logger.error("reportlab not installed. Install with: pip install reportlab")
            raise ImportError("reportlab is required for PDF export")

        # Create PDF buffer
        output = io.BytesIO()
        doc = SimpleDocTemplate(output, pagesize=A4)

        # Create styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.darkblue,
            spaceAfter=30
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.darkblue,
            spaceAfter=12
        )

        # Build content
        elements = []

        # Title
        account = self.db.query(Account).filter(Account.id == account_id).first()
        if account:
            elements.append(Paragraph(f"Portfolio Report - {account.name}", title_style))
            elements.append(Paragraph(f"Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
            elements.append(Spacer(1, 0.2 * inch))

        # Get data based on report type
        if report_type == "portfolio" or report_type == "holdings":
            holdings = self.db.query(Holding).filter(Holding.account_id == account_id).all()

            if holdings:
                elements.append(Paragraph("Holdings", heading_style))

                # Create table data
                table_data = [["Stock", "Qty", "Avg Price", "LTP", "Value", "P&L", "P&L %"]]
                for h in holdings:
                    table_data.append([
                        h.stock,
                        str(h.qty),
                        f"₹{h.avg_price:.2f}",
                        f"₹{h.ltp:.2f}",
                        f"₹{h.current_value:.2f}",
                        f"₹{h.pnl:.2f}",
                        f"{h.pnl_percent:.2f}%"
                    ])

                table = Table(table_data, colWidths=[1.5*inch, 0.5*inch, 1*inch, 1*inch, 1*inch, 1*inch, 0.8*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                elements.append(table)
                elements.append(Spacer(1, 0.3 * inch))

                # Summary
                total_value = sum(h.current_value for h in holdings)
                total_pnl = sum(h.pnl for h in holdings)

                elements.append(Paragraph("Summary", heading_style))
                summary_data = [
                    ["Total Value", f"₹{total_value:,.2f}"],
                    ["Total P&L", f"₹{total_pnl:,.2f}"],
                    ["Number of Holdings", str(len(holdings))]
                ]
                summary_table = Table(summary_data, colWidths=[2*inch, 3*inch])
                summary_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                elements.append(summary_table)

        if report_type == "portfolio" or report_type == "positions":
            positions = self.db.query(Position).filter(Position.account_id == account_id).all()

            if positions:
                elements.append(Spacer(1, 0.3 * inch))
                elements.append(Paragraph("Positions", heading_style))

                table_data = [["Stock", "Qty", "Avg Price", "LTP", "P&L", "P&L %", "Product"]]
                for p in positions:
                    table_data.append([
                        p.stock,
                        str(p.qty),
                        f"₹{p.avg_price:.2f}",
                        f"₹{p.ltp:.2f}",
                        f"₹{p.pnl:.2f}",
                        f"{p.pnl_percent:.2f}%",
                        p.product
                    ])

                table = Table(table_data, colWidths=[1.5*inch, 0.5*inch, 1*inch, 1*inch, 1*inch, 0.8*inch, 1*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                elements.append(table)

        if report_type == "portfolio" or report_type == "orders":
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            orders = self.db.query(Order).filter(
                Order.account_id == account_id,
                Order.placed_at >= cutoff_date
            ).order_by(Order.placed_at.desc()).all()

            if orders:
                elements.append(Spacer(1, 0.3 * inch))
                elements.append(Paragraph("Recent Orders (Last 30 Days)", heading_style))

                table_data = [["Order ID", "Stock", "Type", "Qty", "Price", "Status", "Date"]]
                for o in orders[:50]:  # Limit to 50 orders
                    table_data.append([
                        o.order_id[:10] + "...",
                        o.stock,
                        o.transaction_type,
                        str(o.qty),
                        f"₹{o.price:.2f}",
                        o.status,
                        o.placed_at.strftime("%Y-%m-%d")
                    ])

                table = Table(table_data, colWidths=[1*inch, 1*inch, 0.6*inch, 0.5*inch, 1*inch, 0.8*inch, 1*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                elements.append(table)

        # Build PDF
        doc.build(elements)

        output.seek(0)
        return output.getvalue()

    def export_tax_report_to_csv(
        self,
        account_id: int,
        period_start: datetime,
        period_end: datetime
    ) -> str:
        """
        Export tax report to CSV format

        Args:
            account_id: Account ID
            period_start: Start date of period
            period_end: End date of period

        Returns:
            CSV string
        """
        # Get orders within period
        orders = self.db.query(Order).filter(
            Order.account_id == account_id,
            Order.placed_at >= period_start,
            Order.placed_at <= period_end,
            Order.status == "COMPLETE"
        ).order_by(Order.placed_at.asc()).all()

        # Get holdings for current positions
        holdings = self.db.query(Holding).filter(Holding.account_id == account_id).all()

        # Create tax report data
        data = []

        # Add completed trades
        for o in orders:
            data.append({
                "Date": o.placed_at.strftime("%Y-%m-%d"),
                "Stock": o.stock,
                "Exchange": o.exchange,
                "Transaction Type": o.transaction_type,
                "Quantity": o.qty,
                "Price": o.price,
                "Total Value": o.qty * o.price,
                "Order ID": o.order_id,
                "Product": o.product
            })

        # Add current holdings
        for h in holdings:
            data.append({
                "Date": "Holding",
                "Stock": h.stock,
                "Exchange": h.exchange,
                "Transaction Type": "HOLDING",
                "Quantity": h.qty,
                "Average Price": h.avg_price,
                "Total Value": h.current_value,
                "Order ID": "N/A",
                "Product": h.product
            })

        df = pd.DataFrame(data)
        return df.to_csv(index=False)

    def export_historical_data_to_csv(
        self,
        account_id: int,
        days: int = 90
    ) -> str:
        """
        Export historical portfolio data to CSV format

        Args:
            account_id: Account ID
            days: Number of days of historical data

        Returns:
            CSV string
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        snapshots = self.db.query(PortfolioSnapshot).filter(
            PortfolioSnapshot.account_id == account_id,
            PortfolioSnapshot.recorded_at >= cutoff_date
        ).order_by(PortfolioSnapshot.recorded_at.asc()).all()

        # Create DataFrame
        data = []
        for s in snapshots:
            data.append({
                "Date": s.recorded_at.strftime("%Y-%m-%d"),
                "Total Value": s.total_value,
                "Investment Value": s.investment_value,
                "Day P&L": s.day_pnl,
                "Day P&L %": s.day_pnl_percent,
                "Overall P&L": s.overall_pnl,
                "Overall P&L %": s.overall_pnl_percent,
                "Holdings Count": s.holdings_count,
                "Positions Count": s.positions_count
            })

        df = pd.DataFrame(data)
        return df.to_csv(index=False)

    def get_export_summary(
        self,
        account_id: int
    ) -> Dict[str, Any]:
        """
        Get summary of available exports

        Args:
            account_id: Account ID

        Returns:
            Dict with export summary
        """
        account = self.db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise ValueError("Account not found")

        holdings_count = self.db.query(Holding).filter(Holding.account_id == account_id).count()
        positions_count = self.db.query(Position).filter(Position.account_id == account_id).count()
        orders_count = self.db.query(Order).filter(Order.account_id == account_id).count()
        gtt_count = self.db.query(GTTOrder).filter(GTTOrder.account_id == account_id).count()

        return {
            "account_id": account_id,
            "account_name": account.name,
            "available_exports": {
                "holdings_csv": {
                    "description": "Export all holdings to CSV",
                    "record_count": holdings_count
                },
                "positions_csv": {
                    "description": "Export all positions to CSV",
                    "record_count": positions_count
                },
                "orders_csv": {
                    "description": "Export recent orders to CSV",
                    "record_count": orders_count
                },
                "gtt_csv": {
                    "description": "Export GTT orders to CSV",
                    "record_count": gtt_count
                },
                "portfolio_excel": {
                    "description": "Export complete portfolio to Excel",
                    "includes": ["Holdings", "Positions", "Orders", "GTT Orders"]
                },
                "portfolio_pdf": {
                    "description": "Export portfolio report to PDF",
                    "includes": ["Holdings", "Positions", "Orders"]
                },
                "tax_report_csv": {
                    "description": "Export tax report to CSV",
                    "period": "Custom date range"
                },
                "historical_csv": {
                    "description": "Export historical portfolio data",
                    "period": "Last 90 days"
                }
            },
            "generated_at": datetime.utcnow().isoformat()
        }


if __name__ == "__main__":
    from database import SessionLocal

    db = SessionLocal()
    export_manager = ExportManager(db)

    print("Export Manager initialized")
    print("Available export formats: CSV, Excel, PDF")

    db.close()
