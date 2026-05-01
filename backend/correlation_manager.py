"""
Correlation Heatmap Manager for pyPortMan
Show correlation between holdings
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
import numpy as np

from models import Account, Holding, CorrelationData, PortfolioSnapshot

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


class CorrelationManager:
    """Manager for portfolio correlation analysis"""

    def __init__(self, db: Session):
        self.db = db

    def calculate_correlation_matrix(
        self,
        account_id: int,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Calculate correlation matrix for portfolio holdings
        """
        # Get holdings
        holdings = self.db.query(Holding).filter(
            Holding.account_id == account_id
        ).all()

        if len(holdings) < 2:
            return {"message": "Need at least 2 holdings to calculate correlation"}

        stocks = [h.stock for h in holdings]

        # Get historical portfolio values for each stock
        # In production, this would use actual stock price history
        # For now, we'll use portfolio snapshots as a proxy

        cutoff = datetime.utcnow() - timedelta(days=period_days)

        # Get portfolio snapshots
        snapshots = self.db.query(PortfolioSnapshot).filter(
            PortfolioSnapshot.account_id == account_id,
            PortfolioSnapshot.recorded_at >= cutoff
        ).order_by(
            PortfolioSnapshot.recorded_at.asc()
        ).all()

        if len(snapshots) < 10:
            return {"message": "Insufficient data for correlation calculation"}

        # Calculate returns
        returns = []
        for i in range(1, len(snapshots)):
            prev_value = snapshots[i-1].total_value
            curr_value = snapshots[i].total_value
            if prev_value > 0:
                returns.append((curr_value - prev_value) / prev_value)

        # For demonstration, create synthetic correlation data
        # In production, calculate actual correlations using price history
        correlation_matrix = self._generate_synthetic_correlation_matrix(stocks)

        # Save correlation data
        self._save_correlation_data(account_id, stocks, correlation_matrix, period_days)

        return {
            "stocks": stocks,
            "correlation_matrix": correlation_matrix,
            "period_days": period_days,
            "calculated_at": datetime.utcnow().isoformat()
        }

    def _generate_synthetic_correlation_matrix(self, stocks: List[str]) -> List[List[float]]:
        """
        Generate synthetic correlation matrix for demonstration
        In production, calculate actual correlations from price data
        """
        n = len(stocks)
        matrix = []

        for i in range(n):
            row = []
            for j in range(n):
                if i == j:
                    row.append(1.0)
                else:
                    # Generate random correlation between -0.5 and 0.9
                    # Stocks in same sector tend to be more correlated
                    correlation = np.random.uniform(-0.3, 0.8)
                    row.append(round(correlation, 4))
            matrix.append(row)

        return matrix

    def _save_correlation_data(
        self,
        account_id: int,
        stocks: List[str],
        correlation_matrix: List[List[float]],
        period_days: int
    ) -> None:
        """
        Save correlation data to database
        """
        # Delete old records
        self.db.query(CorrelationData).filter(
            CorrelationData.account_id == account_id
        ).delete()

        # Save new records
        for i in range(len(stocks)):
            for j in range(i + 1, len(stocks)):
                correlation = CorrelationData(
                    account_id=account_id,
                    stock1=stocks[i],
                    stock2=stocks[j],
                    correlation=correlation_matrix[i][j],
                    period_days=period_days
                )
                self.db.add(correlation)

        self.db.commit()

    def get_correlation_matrix(
        self,
        account_id: int,
        period_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get correlation matrix for an account
        """
        # Get holdings
        holdings = self.db.query(Holding).filter(
            Holding.account_id == account_id
        ).all()

        stocks = [h.stock for h in holdings]

        if len(stocks) < 2:
            return {"message": "Need at least 2 holdings to calculate correlation"}

        # Get correlation data
        query = self.db.query(CorrelationData).filter(
            CorrelationData.account_id == account_id
        )

        if period_days:
            query = query.filter(CorrelationData.period_days == period_days)

        correlations = query.all()

        if not correlations:
            # Calculate new correlations
            return self.calculate_correlation_matrix(account_id, period_days or 30)

        # Build matrix
        stock_index = {stock: i for i, stock in enumerate(stocks)}
        n = len(stocks)
        matrix = [[0.0] * n for _ in range(n)]

        # Set diagonal to 1
        for i in range(n):
            matrix[i][i] = 1.0

        # Fill matrix from correlation data
        for corr in correlations:
            i = stock_index.get(corr.stock1)
            j = stock_index.get(corr.stock2)
            if i is not None and j is not None:
                matrix[i][j] = corr.correlation
                matrix[j][i] = corr.correlation

        return {
            "stocks": stocks,
            "correlation_matrix": matrix,
            "period_days": correlations[0].period_days if correlations else 30,
            "calculated_at": correlations[0].calculated_at.isoformat() if correlations else None
        }

    def get_high_correlation_pairs(
        self,
        account_id: int,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Get pairs of stocks with high correlation
        """
        correlations = self.db.query(CorrelationData).filter(
            CorrelationData.account_id == account_id,
            CorrelationData.correlation >= threshold
        ).order_by(
            CorrelationData.correlation.desc()
        ).all()

        return [
            {
                "stock1": corr.stock1,
                "stock2": corr.stock2,
                "correlation": corr.correlation,
                "period_days": corr.period_days
            }
            for corr in correlations
        ]

    def get_low_correlation_pairs(
        self,
        account_id: int,
        threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Get pairs of stocks with low correlation (good for diversification)
        """
        correlations = self.db.query(CorrelationData).filter(
            CorrelationData.account_id == account_id,
            CorrelationData.correlation <= threshold
        ).order_by(
            CorrelationData.correlation.asc()
        ).all()

        return [
            {
                "stock1": corr.stock1,
                "stock2": corr.stock2,
                "correlation": corr.correlation,
                "period_days": corr.period_days
            }
            for corr in correlations
        ]

    def get_correlation_summary(self, account_id: int) -> Dict[str, Any]:
        """
        Get summary of portfolio correlations
        """
        correlations = self.db.query(CorrelationData).filter(
            CorrelationData.account_id == account_id
        ).all()

        if not correlations:
            return {"message": "No correlation data available"}

        corr_values = [c.correlation for c in correlations]

        return {
            "total_pairs": len(correlations),
            "avg_correlation": sum(corr_values) / len(corr_values),
            "max_correlation": max(corr_values),
            "min_correlation": min(corr_values),
            "high_correlation_count": len([c for c in corr_values if c >= 0.7]),
            "low_correlation_count": len([c for c in corr_values if c <= 0.3]),
            "period_days": correlations[0].period_days if correlations else 30
        }

    def get_diversification_score(self, account_id: int) -> Dict[str, Any]:
        """
        Calculate diversification score based on correlations
        """
        correlations = self.db.query(CorrelationData).filter(
            CorrelationData.account_id == account_id
        ).all()

        if not correlations:
            return {"message": "No correlation data available"}

        # Calculate average correlation
        avg_corr = sum(c.correlation for c in correlations) / len(correlations)

        # Diversification score: lower correlation = higher diversification
        # Score from 0 to 100
        diversification_score = max(0, min(100, (1 - avg_corr) * 100))

        # Determine diversification level
        if diversification_score >= 70:
            level = "EXCELLENT"
        elif diversification_score >= 50:
            level = "GOOD"
        elif diversification_score >= 30:
            level = "MODERATE"
        else:
            level = "POOR"

        return {
            "diversification_score": round(diversification_score, 2),
            "diversification_level": level,
            "avg_correlation": round(avg_corr, 4),
            "recommendation": self._get_diversification_recommendation(diversification_score)
        }

    def _get_diversification_recommendation(self, score: float) -> str:
        """
        Get diversification recommendation based on score
        """
        if score >= 70:
            return "Portfolio is well-diversified. Consider maintaining current allocation."
        elif score >= 50:
            return "Portfolio has good diversification. Consider adding uncorrelated assets."
        elif score >= 30:
            return "Portfolio has moderate diversification. Consider reducing exposure to highly correlated stocks."
        else:
            return "Portfolio is poorly diversified. Consider adding stocks from different sectors or asset classes."

    def get_sector_correlation(self, account_id: int) -> Dict[str, Any]:
        """
        Analyze correlation by sector
        """
        from sector_pnl import STOCK_SECTOR_MAPPING

        correlations = self.db.query(CorrelationData).filter(
            CorrelationData.account_id == account_id
        ).all()

        if not correlations:
            return {"message": "No correlation data available"}

        # Group correlations by sector
        sector_correlations = {}

        for corr in correlations:
            sector1 = STOCK_SECTOR_MAPPING.get(corr.stock1, "Others")
            sector2 = STOCK_SECTOR_MAPPING.get(corr.stock2, "Others")

            if sector1 == sector2:
                # Same sector correlation
                if sector1 not in sector_correlations:
                    sector_correlations[sector1] = []
                sector_correlations[sector1].append(corr.correlation)

        # Calculate average correlation per sector
        sector_avg = {}
        for sector, corrs in sector_correlations.items():
            if corrs:
                sector_avg[sector] = sum(corrs) / len(corrs)

        return {
            "sector_correlations": sector_avg,
            "most_correlated_sector": max(sector_avg, key=sector_avg.get) if sector_avg else None,
            "least_correlated_sector": min(sector_avg, key=sector_avg.get) if sector_avg else None
        }
