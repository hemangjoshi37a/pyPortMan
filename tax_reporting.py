"""
Tax Reporting Module
Capital gains calculation (STCG/LTCG), tax-ready reports, financial year summaries
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from dataclasses import dataclass
import json
from enum import Enum


class TaxYear(Enum):
    """Indian Financial Year"""
    FY_2023_24 = "2023-24"
    FY_2024_25 = "2024-25"
    FY_2025_26 = "2025-26"


class TransactionType(Enum):
    """Transaction types"""
    BUY = "BUY"
    SELL = "SELL"


class AssetType(Enum):
    """Asset types for tax purposes"""
    EQUITY = "EQUITY"
    EQUITY_MF = "EQUITY_MF"
    DEBT_MF = "DEBT_MF"
    DEBT = "DEBT"
    GOLD = "GOLD"
    REAL_ESTATE = "REAL_ESTATE"
    CRYPTO = "CRYPTO"
    OTHERS = "OTHERS"


@dataclass
class Transaction:
    """Transaction data structure"""
    symbol: str
    transaction_type: TransactionType
    quantity: int
    price: float
    date: date
    broker: str
    asset_type: AssetType
    stt: float = 0.0
    brokerage: float = 0.0
    other_charges: float = 0.0

    @property
    def total_cost(self) -> float:
        """Total cost including all charges"""
        base_cost = self.quantity * self.price
        if self.transaction_type == TransactionType.BUY:
            return base_cost + self.brokerage + self.other_charges
        else:
            return base_cost - self.brokerage - self.other_charges - self.stt


@dataclass
class CapitalGain:
    """Capital gain data structure"""
    symbol: str
    asset_type: AssetType
    buy_date: date
    sell_date: date
    buy_price: float
    sell_price: float
    quantity: int
    holding_period_days: int
    holding_period_years: float
    gain_type: str  # STCG or LTCG
    gain_amount: float
    tax_rate: float
    tax_amount: float
    indexation_benefit: bool = False
    indexed_cost: float = 0.0


class TaxCalculator:
    """Tax calculator for Indian tax laws"""

    # Tax rates for FY 2024-25
    TAX_RATES = {
        AssetType.EQUITY: {
            "STCG": 0.15,  # 15% for equity held < 1 year
            "LTCG": 0.10   # 10% on gains above 1 lakh for equity held >= 1 year
        },
        AssetType.EQUITY_MF: {
            "STCG": 0.15,
            "LTCG": 0.10
        },
        AssetType.DEBT_MF: {
            "STCG": 0.30,  # As per income slab
            "LTCG": 0.20   # 20% with indexation
        },
        AssetType.DEBT: {
            "STCG": 0.30,
            "LTCG": 0.20
        },
        AssetType.GOLD: {
            "STCG": 0.30,
            "LTCG": 0.20
        },
        AssetType.REAL_ESTATE: {
            "STCG": 0.30,
            "LTCG": 0.20
        },
        AssetType.CRYPTO: {
            "STCG": 0.30,
            "LTCG": 0.20
        },
        AssetType.OTHERS: {
            "STCG": 0.30,
            "LTCG": 0.20
        }
    }

    # Cost Inflation Index (CII) for indexation
    CII = {
        2001: 100,
        2002: 105,
        2003: 109,
        2004: 113,
        2005: 117,
        2006: 122,
        2007: 129,
        2008: 137,
        2009: 148,
        2010: 167,
        2011: 184,
        2012: 200,
        2013: 219,
        2014: 240,
        2015: 254,
        2016: 264,
        2017: 272,
        2018: 280,
        2019: 289,
        2020: 301,
        2021: 317,
        2022: 331,
        2023: 348,
        2024: 363
    }

    # LTCG exemption limit for equity
    EQUITY_LTCG_EXEMPTION = 100000  # 1 lakh

    def __init__(self):
        self.transactions: List[Transaction] = []
        self.holdings: Dict[str, List[Transaction]] = {}

    def add_transaction(self, transaction: Transaction):
        """Add a transaction"""
        self.transactions.append(transaction)

    def add_transactions_from_dataframe(self, df: pd.DataFrame):
        """Add transactions from DataFrame"""
        for _, row in df.iterrows():
            transaction = Transaction(
                symbol=row['symbol'],
                transaction_type=TransactionType(row['transaction_type']),
                quantity=int(row['quantity']),
                price=float(row['price']),
                date=pd.to_datetime(row['date']).date(),
                broker=row.get('broker', ''),
                asset_type=AssetType(row.get('asset_type', 'EQUITY')),
                stt=float(row.get('stt', 0)),
                brokerage=float(row.get('brokerage', 0)),
                other_charges=float(row.get('other_charges', 0))
            )
            self.add_transaction(transaction)

    def calculate_capital_gains(self, tax_year: TaxYear = TaxYear.FY_2024_25) -> List[CapitalGain]:
        """Calculate capital gains using FIFO method"""
        capital_gains = []

        # Sort transactions by date
        sorted_transactions = sorted(self.transactions, key=lambda x: x.date)

        # Group by symbol
        symbol_transactions = {}
        for txn in sorted_transactions:
            if txn.symbol not in symbol_transactions:
                symbol_transactions[txn.symbol] = []
            symbol_transactions[txn.symbol].append(txn)

        # Calculate gains for each symbol
        for symbol, txns in symbol_transactions.items():
            buy_queue = []  # Queue for FIFO

            for txn in txns:
                if txn.transaction_type == TransactionType.BUY:
                    buy_queue.append(txn)
                elif txn.transaction_type == TransactionType.SELL:
                    remaining_qty = txn.quantity

                    while remaining_qty > 0 and buy_queue:
                        buy_txn = buy_queue[0]

                        if buy_txn.quantity <= remaining_qty:
                            # Full sell from this buy
                            gain = self._calculate_gain(buy_txn, txn)
                            capital_gains.append(gain)
                            remaining_qty -= buy_txn.quantity
                            buy_queue.pop(0)
                        else:
                            # Partial sell
                            partial_buy = Transaction(
                                symbol=buy_txn.symbol,
                                transaction_type=TransactionType.BUY,
                                quantity=remaining_qty,
                                price=buy_txn.price,
                                date=buy_txn.date,
                                broker=buy_txn.broker,
                                asset_type=buy_txn.asset_type,
                                stt=buy_txn.stt * (remaining_qty / buy_txn.quantity),
                                brokerage=buy_txn.brokerage * (remaining_qty / buy_txn.quantity),
                                other_charges=buy_txn.other_charges * (remaining_qty / buy_txn.quantity)
                            )
                            gain = self._calculate_gain(partial_buy, txn)
                            capital_gains.append(gain)

                            # Update original buy quantity
                            buy_txn.quantity -= remaining_qty
                            remaining_qty = 0

        # Filter by tax year
        fy_start, fy_end = self._get_fy_dates(tax_year)
        filtered_gains = [g for g in capital_gains
                         if fy_start <= g.sell_date <= fy_end]

        return filtered_gains

    def _calculate_gain(self, buy_txn: Transaction, sell_txn: Transaction) -> CapitalGain:
        """Calculate gain for a buy-sell pair"""
        holding_period = (sell_txn.date - buy_txn.date).days
        holding_years = holding_period / 365.25

        # Determine gain type
        asset_type = buy_txn.asset_type
        if asset_type in [AssetType.EQUITY, AssetType.EQUITY_MF]:
            is_long_term = holding_period >= 365
        else:
            is_long_term = holding_period >= 1095  # 3 years for other assets

        gain_type = "LTCG" if is_long_term else "STCG"

        # Calculate gain
        buy_cost = buy_txn.total_cost
        sell_value = sell_txn.total_cost
        gain_amount = sell_value - buy_cost

        # Apply indexation for LTCG on non-equity assets
        indexed_cost = buy_cost
        if is_long_term and asset_type not in [AssetType.EQUITY, AssetType.EQUITY_MF]:
            indexed_cost = self._apply_indexation(buy_cost, buy_txn.date.year, sell_txn.date.year)

        # Calculate tax
        tax_rate = self.TAX_RATES[asset_type][gain_type]

        if gain_type == "LTCG" and asset_type in [AssetType.EQUITY, AssetType.EQUITY_MF]:
            # 10% on gains above 1 lakh
            taxable_gain = max(0, gain_amount - self.EQUITY_LTCG_EXEMPTION)
            tax_amount = taxable_gain * tax_rate
        else:
            tax_amount = gain_amount * tax_rate

        return CapitalGain(
            symbol=buy_txn.symbol,
            asset_type=asset_type,
            buy_date=buy_txn.date,
            sell_date=sell_txn.date,
            buy_price=buy_txn.price,
            sell_price=sell_txn.price,
            quantity=buy_txn.quantity,
            holding_period_days=holding_period,
            holding_period_years=holding_years,
            gain_type=gain_type,
            gain_amount=gain_amount,
            tax_rate=tax_rate,
            tax_amount=tax_amount,
            indexation_benefit=(indexed_cost != buy_cost),
            indexed_cost=indexed_cost
        )

    def _apply_indexation(self, cost: float, buy_year: int, sell_year: int) -> float:
        """Apply cost inflation indexation"""
        cii_buy = self.CII.get(buy_year, 100)
        cii_sell = self.CII.get(sell_year, 100)

        if cii_buy == 0:
            return cost

        indexed_cost = cost * (cii_sell / cii_buy)
        return indexed_cost

    def _get_fy_dates(self, tax_year: TaxYear) -> tuple:
        """Get start and end dates for financial year"""
        year = int(tax_year.value.split('-')[0])
        start_date = date(year - 1, 4, 1)
        end_date = date(year, 3, 31)
        return start_date, end_date

    def get_tax_summary(self, tax_year: TaxYear = TaxYear.FY_2024_25) -> Dict:
        """Get tax summary for the financial year"""
        gains = self.calculate_capital_gains(tax_year)

        summary = {
            "tax_year": tax_year.value,
            "total_stcg": 0,
            "total_ltcg": 0,
            "total_stcg_tax": 0,
            "total_ltcg_tax": 0,
            "total_tax": 0,
            "net_gain": 0,
            "asset_breakdown": {},
            "symbol_breakdown": {}
        }

        for gain in gains:
            if gain.gain_type == "STCG":
                summary["total_stcg"] += gain.gain_amount
                summary["total_stcg_tax"] += gain.tax_amount
            else:
                summary["total_ltcg"] += gain.gain_amount
                summary["total_ltcg_tax"] += gain.tax_amount

            summary["net_gain"] += gain.gain_amount

            # Asset breakdown
            asset = gain.asset_type.value
            if asset not in summary["asset_breakdown"]:
                summary["asset_breakdown"][asset] = {
                    "stcg": 0,
                    "ltcg": 0,
                    "tax": 0
                }

            if gain.gain_type == "STCG":
                summary["asset_breakdown"][asset]["stcg"] += gain.gain_amount
            else:
                summary["asset_breakdown"][asset]["ltcg"] += gain.gain_amount

            summary["asset_breakdown"][asset]["tax"] += gain.tax_amount

            # Symbol breakdown
            symbol = gain.symbol
            if symbol not in summary["symbol_breakdown"]:
                summary["symbol_breakdown"][symbol] = {
                    "stcg": 0,
                    "ltcg": 0,
                    "tax": 0,
                    "transactions": 0
                }

            if gain.gain_type == "STCG":
                summary["symbol_breakdown"][symbol]["stcg"] += gain.gain_amount
            else:
                summary["symbol_breakdown"][symbol]["ltcg"] += gain.gain_amount

            summary["symbol_breakdown"][symbol]["tax"] += gain.tax_amount
            summary["symbol_breakdown"][symbol]["transactions"] += 1

        summary["total_tax"] = summary["total_stcg_tax"] + summary["total_ltcg_tax"]

        return summary

    def get_holdings_as_of(self, as_of_date: date) -> Dict:
        """Get holdings as of a specific date"""
        holdings = {}

        for txn in self.transactions:
            if txn.date > as_of_date:
                continue

            if txn.symbol not in holdings:
                holdings[txn.symbol] = {
                    "quantity": 0,
                    "avg_price": 0,
                    "total_cost": 0,
                    "asset_type": txn.asset_type
                }

            if txn.transaction_type == TransactionType.BUY:
                old_qty = holdings[txn.symbol]["quantity"]
                old_cost = holdings[txn.symbol]["total_cost"]
                new_qty = old_qty + txn.quantity
                new_cost = old_cost + txn.total_cost

                holdings[txn.symbol]["quantity"] = new_qty
                holdings[txn.symbol]["total_cost"] = new_cost
                holdings[txn.symbol]["avg_price"] = new_cost / new_qty if new_qty > 0 else 0

            elif txn.transaction_type == TransactionType.SELL:
                holdings[txn.symbol]["quantity"] -= txn.quantity

        return holdings


class TaxReportGenerator:
    """Generate tax-ready reports"""

    def __init__(self, tax_calculator: TaxCalculator):
        self.calculator = tax_calculator

    def generate_capital_gains_report(self, tax_year: TaxYear = TaxYear.FY_2024_25) -> pd.DataFrame:
        """Generate capital gains report"""
        gains = self.calculator.calculate_capital_gains(tax_year)

        data = []
        for gain in gains:
            data.append({
                "Symbol": gain.symbol,
                "Asset Type": gain.asset_type.value,
                "Buy Date": gain.buy_date.strftime("%Y-%m-%d"),
                "Sell Date": gain.sell_date.strftime("%Y-%m-%d"),
                "Buy Price": gain.buy_price,
                "Sell Price": gain.sell_price,
                "Quantity": gain.quantity,
                "Holding Period (Days)": gain.holding_period_days,
                "Holding Period (Years)": round(gain.holding_period_years, 2),
                "Gain Type": gain.gain_type,
                "Gain Amount": round(gain.gain_amount, 2),
                "Tax Rate": f"{gain.tax_rate * 100}%",
                "Tax Amount": round(gain.tax_amount, 2),
                "Indexation Benefit": gain.indexation_benefit,
                "Indexed Cost": round(gain.indexed_cost, 2) if gain.indexation_benefit else "-"
            })

        return pd.DataFrame(data)

    def generate_tax_summary_report(self, tax_year: TaxYear = TaxYear.FY_2024_25) -> pd.DataFrame:
        """Generate tax summary report"""
        summary = self.calculator.get_tax_summary(tax_year)

        # Main summary
        main_summary = pd.DataFrame([{
            "Tax Year": summary["tax_year"],
            "Total STCG": round(summary["total_stcg"], 2),
            "Total LTCG": round(summary["total_ltcg"], 2),
            "Total STCG Tax": round(summary["total_stcg_tax"], 2),
            "Total LTCG Tax": round(summary["total_ltcg_tax"], 2),
            "Total Tax": round(summary["total_tax"], 2),
            "Net Gain": round(summary["net_gain"], 2)
        }])

        return main_summary

    def generate_asset_breakdown_report(self, tax_year: TaxYear = TaxYear.FY_2024_25) -> pd.DataFrame:
        """Generate asset-wise breakdown report"""
        summary = self.calculator.get_tax_summary(tax_year)

        data = []
        for asset, values in summary["asset_breakdown"].items():
            data.append({
                "Asset Type": asset,
                "STCG": round(values["stcg"], 2),
                "LTCG": round(values["ltcg"], 2),
                "Total Tax": round(values["tax"], 2)
            })

        return pd.DataFrame(data)

    def generate_symbol_breakdown_report(self, tax_year: TaxYear = TaxYear.FY_2024_25) -> pd.DataFrame:
        """Generate symbol-wise breakdown report"""
        summary = self.calculator.get_tax_summary(tax_year)

        data = []
        for symbol, values in summary["symbol_breakdown"].items():
            data.append({
                "Symbol": symbol,
                "STCG": round(values["stcg"], 2),
                "LTCG": round(values["ltcg"], 2),
                "Total Tax": round(values["tax"], 2),
                "Transactions": values["transactions"]
            })

        return pd.DataFrame(data)

    def generate_holdings_report(self, as_of_date: Optional[date] = None) -> pd.DataFrame:
        """Generate holdings report"""
        if as_of_date is None:
            as_of_date = date.today()

        holdings = self.calculator.get_holdings_as_of(as_of_date)

        data = []
        for symbol, values in holdings.items():
            if values["quantity"] > 0:
                data.append({
                    "Symbol": symbol,
                    "Quantity": values["quantity"],
                    "Average Price": round(values["avg_price"], 2),
                    "Total Cost": round(values["total_cost"], 2),
                    "Asset Type": values["asset_type"].value
                })

        return pd.DataFrame(data)

    def export_to_excel(self, tax_year: TaxYear = TaxYear.FY_2024_25,
                      filename: Optional[str] = None) -> str:
        """Export all reports to Excel"""
        if filename is None:
            filename = f"tax_report_{tax_year.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # Capital Gains Report
            cg_report = self.generate_capital_gains_report(tax_year)
            cg_report.to_excel(writer, sheet_name='Capital Gains', index=False)

            # Tax Summary
            summary_report = self.generate_tax_summary_report(tax_year)
            summary_report.to_excel(writer, sheet_name='Tax Summary', index=False)

            # Asset Breakdown
            asset_report = self.generate_asset_breakdown_report(tax_year)
            asset_report.to_excel(writer, sheet_name='Asset Breakdown', index=False)

            # Symbol Breakdown
            symbol_report = self.generate_symbol_breakdown_report(tax_year)
            symbol_report.to_excel(writer, sheet_name='Symbol Breakdown', index=False)

            # Holdings
            holdings_report = self.generate_holdings_report()
            holdings_report.to_excel(writer, sheet_name='Holdings', index=False)

        return filename

    def export_to_json(self, tax_year: TaxYear = TaxYear.FY_2024_25,
                      filename: Optional[str] = None) -> str:
        """Export reports to JSON"""
        if filename is None:
            filename = f"tax_report_{tax_year.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        summary = self.calculator.get_tax_summary(tax_year)

        report = {
            "tax_year": summary["tax_year"],
            "summary": summary,
            "capital_gains": self.generate_capital_gains_report(tax_year).to_dict("records"),
            "holdings": self.generate_holdings_report().to_dict("records")
        }

        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        return filename

    def generate_itr_form_data(self, tax_year: TaxYear = TaxYear.FY_2024_25) -> Dict:
        """Generate data for ITR forms"""
        summary = self.calculator.get_tax_summary(tax_year)

        return {
            "schedule_cg": {
                "stcg_equity": summary["total_stcg"],
                "ltcg_equity": summary["total_ltcg"],
                "stcg_other": 0,  # Add if other assets
                "ltcg_other": 0,
                "exempt_ltcg": max(0, summary["total_ltcg"] - TaxCalculator.EQUITY_LTCG_EXEMPTION)
            },
            "tax_payable": {
                "stcg_tax": summary["total_stcg_tax"],
                "ltcg_tax": summary["total_ltcg_tax"],
                "total_tax": summary["total_tax"]
            }
        }


# Utility functions
def parse_tradebook_from_broker(broker_name: str, file_path: str) -> pd.DataFrame:
    """Parse tradebook from broker export"""
    # This is a placeholder - actual implementation would vary by broker format
    try:
        if broker_name.lower() == "zerodha":
            df = pd.read_csv(file_path)
            # Map Zerodha columns to standard format
            df = df.rename(columns={
                "Trade Date": "date",
                "Symbol": "symbol",
                "Quantity": "quantity",
                "Price": "price",
                "Trade Type": "transaction_type"
            })
        elif broker_name.lower() == "angel":
            df = pd.read_excel(file_path)
            # Map Angel columns to standard format
            df = df.rename(columns({
                "Trade Date": "date",
                "Symbol": "symbol",
                "Quantity": "quantity",
                "Price": "price",
                "Buy/Sell": "transaction_type"
            })
        else:
            df = pd.read_csv(file_path)

        return df
    except Exception as e:
        print(f"Error parsing tradebook: {e}")
        return pd.DataFrame()


def create_tax_calculator_from_tradebook(tradebook_df: pd.DataFrame) -> TaxCalculator:
    """Create TaxCalculator from tradebook DataFrame"""
    calculator = TaxCalculator()
    calculator.add_transactions_from_dataframe(tradebook_df)
    return calculator
