"""
Stress Testing Module for pyPortMan
Portfolio stress testing with various market scenarios
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import numpy as np
from sqlalchemy.orm import Session
from dataclasses import dataclass
from enum import Enum

from models import Account, Holding, Position, PortfolioSnapshot

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


class StressScenarioType(Enum):
    """Types of stress scenarios"""
    MARKET_CRASH = "market_crash"
    SECTOR_CRASH = "sector_crash"
    VOLATILITY_SPIKE = "volatility_spike"
    LIQUIDITY_CRISIS = "liquidity_crisis"
    INTEREST_RATE_SHOCK = "interest_rate_shock"
    CURRENCY_CRISIS = "currency_crisis"
    CUSTOM = "custom"


@dataclass
class StressScenario:
    """Definition of a stress scenario"""
    name: str
    description: str
    scenario_type: StressScenarioType
    parameters: Dict[str, Any]
    severity: str  # LOW, MEDIUM, HIGH, EXTREME


@dataclass
class StressTestResult:
    """Result of a stress test"""
    scenario_name: str
    initial_value: float
    final_value: float
    loss: float
    loss_pct: float
    survives: bool
    worst_position: Optional[Dict[str, Any]]
    recovery_time_days: Optional[int]
    margin_call_risk: bool
    details: Dict[str, Any]


class StressTestingManager:
    """
    Portfolio stress testing manager
    Tests portfolio resilience under various adverse market conditions
    """

    def __init__(self, db: Session):
        self.db = db

    def get_portfolio_value(self, account_id: int) -> float:
        """Get current portfolio value for an account"""
        snapshot = self.db.query(PortfolioSnapshot).filter(
            PortfolioSnapshot.account_id == account_id
        ).order_by(PortfolioSnapshot.recorded_at.desc()).first()

        if not snapshot:
            raise ValueError("No portfolio snapshot found")

        return snapshot.total_value

    def get_holdings(self, account_id: int) -> List[Holding]:
        """Get all holdings for an account"""
        return self.db.query(Holding).filter(Holding.account_id == account_id).all()

    def get_positions(self, account_id: int) -> List[Position]:
        """Get all positions for an account"""
        return self.db.query(Position).filter(Position.account_id == account_id).all()

    def run_market_crash_scenario(
        self,
        account_id: int,
        crash_pct: float = -20.0,
        days: int = 1
    ) -> StressTestResult:
        """
        Simulate a market crash scenario

        Args:
            account_id: Account ID
            crash_pct: Percentage decline (negative)
            days: Duration in days

        Returns:
            StressTestResult with scenario outcome
        """
        initial_value = self.get_portfolio_value(account_id)
        holdings = self.get_holdings(account_id)
        positions = self.get_positions(account_id)

        # Calculate final value after crash
        final_value = initial_value * (1 + crash_pct / 100)
        loss = initial_value - final_value
        loss_pct = abs(crash_pct)

        # Find worst affected position
        worst_position = None
        max_loss_pct = 0

        for holding in holdings:
            holding_loss_pct = abs(crash_pct)  # Simplified - all stocks affected equally
            if holding_loss_pct > max_loss_pct:
                max_loss_pct = holding_loss_pct
                worst_position = {
                    "stock": holding.stock,
                    "loss_pct": holding_loss_pct,
                    "loss_amount": holding.current_value * holding_loss_pct / 100
                }

        # Check margin call risk
        margin_call_risk = loss_pct > 50  # Simplified threshold

        return StressTestResult(
            scenario_name=f"Market Crash ({crash_pct}%)",
            initial_value=initial_value,
            final_value=final_value,
            loss=loss,
            loss_pct=loss_pct,
            survives=final_value > 0,
            worst_position=worst_position,
            recovery_time_days=None,
            margin_call_risk=margin_call_risk,
            details={
                "crash_pct": crash_pct,
                "days": days,
                "affected_holdings": len(holdings),
                "affected_positions": len(positions)
            }
        )

    def run_sector_crash_scenario(
        self,
        account_id: int,
        sector: str,
        crash_pct: float = -30.0,
        days: int = 5
    ) -> StressTestResult:
        """
        Simulate a sector-specific crash scenario

        Args:
            account_id: Account ID
            sector: Sector name
            crash_pct: Percentage decline for sector
            days: Duration in days

        Returns:
            StressTestResult with scenario outcome
        """
        initial_value = self.get_portfolio_value(account_id)
        holdings = self.get_holdings(account_id)

        # Simple sector mapping (in production, use proper sector data)
        sector_mapping = {
            "IT": ["TCS", "INFY", "WIPRO", "TECHM", "HCLTECH"],
            "Banking": ["HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK"],
            "Energy": ["RELIANCE", "ONGC", "NTPC", "POWERGRID"],
            "Auto": ["MARUTI", "TATAMOTORS", "BAJAJ-AUTO", "M&M"],
            "FMCG": ["HINDUNILVR", "ITC", "NESTLEIND", "BRITANNIA"],
            "Pharma": ["SUNPHARMA", "DRREDDY", "CIPLA", "AUROPHARMA"],
            "Metals": ["TATASTEEL", "JSWSTEEL", "HINDALCO"],
            "Infra": ["LT", "ADANIPORTS", "DLF"]
        }

        sector_stocks = sector_mapping.get(sector, [])

        # Calculate impact
        sector_value = 0
        other_value = 0

        for holding in holdings:
            if holding.stock in sector_stocks:
                sector_value += holding.current_value
            else:
                other_value += holding.current_value

        # Apply crash to sector
        sector_loss = sector_value * abs(crash_pct) / 100
        final_value = initial_value - sector_loss
        loss = initial_value - final_value
        loss_pct = (loss / initial_value * 100) if initial_value > 0 else 0

        # Find worst affected position
        worst_position = None
        max_loss = 0

        for holding in holdings:
            if holding.stock in sector_stocks:
                holding_loss = holding.current_value * abs(crash_pct) / 100
                if holding_loss > max_loss:
                    max_loss = holding_loss
                    worst_position = {
                        "stock": holding.stock,
                        "loss_pct": abs(crash_pct),
                        "loss_amount": holding_loss
                    }

        return StressTestResult(
            scenario_name=f"Sector Crash - {sector} ({crash_pct}%)",
            initial_value=initial_value,
            final_value=final_value,
            loss=loss,
            loss_pct=loss_pct,
            survives=final_value > 0,
            worst_position=worst_position,
            recovery_time_days=None,
            margin_call_risk=loss_pct > 50,
            details={
                "sector": sector,
                "crash_pct": crash_pct,
                "days": days,
                "sector_value": sector_value,
                "sector_stocks": len(sector_stocks),
                "affected_holdings": len([h for h in holdings if h.stock in sector_stocks])
            }
        )

    def run_volatility_spike_scenario(
        self,
        account_id: int,
        volatility_multiplier: float = 3.0,
        days: int = 10
    ) -> StressTestResult:
        """
        Simulate a volatility spike scenario

        Args:
            account_id: Account ID
            volatility_multiplier: Multiplier for normal volatility
            days: Duration in days

        Returns:
            StressTestResult with scenario outcome
        """
        initial_value = self.get_portfolio_value(account_id)

        # Get historical returns to estimate normal volatility
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        snapshots = self.db.query(PortfolioSnapshot).filter(
            PortfolioSnapshot.account_id == account_id,
            PortfolioSnapshot.recorded_at >= cutoff_date
        ).order_by(PortfolioSnapshot.recorded_at.asc()).all()

        if len(snapshots) < 2:
            raise ValueError("Insufficient historical data for volatility estimation")

        # Calculate daily returns
        returns = []
        for i in range(1, len(snapshots)):
            if snapshots[i - 1].total_value > 0:
                daily_return = (snapshots[i].total_value - snapshots[i - 1].total_value) / snapshots[i - 1].total_value
                returns.append(daily_return)

        normal_volatility = np.std(returns) if returns else 0.01
        spiked_volatility = normal_volatility * volatility_multiplier

        # Simulate worst-case outcome (mean - 2*std of spiked volatility)
        worst_daily_return = -spiked_volatility * 2
        final_value = initial_value * (1 + worst_daily_return * days)
        loss = initial_value - final_value
        loss_pct = (loss / initial_value * 100) if initial_value > 0 else 0

        return StressTestResult(
            scenario_name=f"Volatility Spike ({volatility_multiplier}x)",
            initial_value=initial_value,
            final_value=final_value,
            loss=loss,
            loss_pct=loss_pct,
            survives=final_value > 0,
            worst_position=None,
            recovery_time_days=None,
            margin_call_risk=loss_pct > 50,
            details={
                "volatility_multiplier": volatility_multiplier,
                "normal_volatility": float(normal_volatility),
                "spiked_volatility": float(spiked_volatility),
                "days": days,
                "worst_daily_return": float(worst_daily_return)
            }
        )

    def run_liquidity_crisis_scenario(
        self,
        account_id: int,
        liquidity_discount: float = -15.0,
        days: int = 5
    ) -> StressTestResult:
        """
        Simulate a liquidity crisis scenario

        Args:
            account_id: Account ID
            liquidity_discount: Discount due to illiquidity
            days: Duration in days

        Returns:
            StressTestResult with scenario outcome
        """
        initial_value = self.get_portfolio_value(account_id)
        holdings = self.get_holdings(account_id)

        # Apply liquidity discount (affects less liquid stocks more)
        # Simplified: assume all stocks affected equally
        final_value = initial_value * (1 + liquidity_discount / 100)
        loss = initial_value - final_value
        loss_pct = abs(liquidity_discount)

        # Identify potentially illiquid positions (small caps, etc.)
        illiquid_positions = []
        for holding in holdings:
            # Simplified: assume stocks with lower value are less liquid
            if holding.current_value < 10000:  # Threshold for illiquidity
                illiquid_positions.append({
                    "stock": holding.stock,
                    "value": holding.current_value,
                    "discount": liquidity_discount
                })

        return StressTestResult(
            scenario_name=f"Liquidity Crisis ({liquidity_discount}% discount)",
            initial_value=initial_value,
            final_value=final_value,
            loss=loss,
            loss_pct=loss_pct,
            survives=final_value > 0,
            worst_position=illiquid_positions[0] if illiquid_positions else None,
            recovery_time_days=None,
            margin_call_risk=loss_pct > 50,
            details={
                "liquidity_discount": liquidity_discount,
                "days": days,
                "illiquid_positions": len(illiquid_positions),
                "illiquid_stocks": [p["stock"] for p in illiquid_positions]
            }
        )

    def run_interest_rate_shock_scenario(
        self,
        account_id: int,
        rate_change_pct: float = 2.0,
        days: int = 30
    ) -> StressTestResult:
        """
        Simulate an interest rate shock scenario

        Args:
            account_id: Account ID
            rate_change_pct: Percentage change in interest rates
            days: Duration in days

        Returns:
            StressTestResult with scenario outcome
        """
        initial_value = self.get_portfolio_value(account_id)
        holdings = self.get_holdings(account_id)

        # Interest rate sensitivity (simplified)
        # Rate-sensitive sectors: Banking, Real Estate, Infra
        rate_sensitive_stocks = ["HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK",
                                  "DLF", "OBEROIRLTY", "GODREJPROP", "BRIGADE",
                                  "LT", "ADANIPORTS", "NTPC", "POWERGRID"]

        # Calculate impact
        rate_sensitive_value = 0
        other_value = 0

        for holding in holdings:
            if holding.stock in rate_sensitive_stocks:
                rate_sensitive_value += holding.current_value
            else:
                other_value += holding.current_value

        # Rate-sensitive stocks decline when rates rise
        rate_sensitive_impact = rate_change_pct * 1.5  # Higher sensitivity
        rate_sensitive_loss = rate_sensitive_value * rate_sensitive_impact / 100

        # Other stocks have smaller impact
        other_impact = rate_change_pct * 0.3
        other_loss = other_value * other_impact / 100

        total_loss = rate_sensitive_loss + other_loss
        final_value = initial_value - total_loss
        loss = total_loss
        loss_pct = (loss / initial_value * 100) if initial_value > 0 else 0

        return StressTestResult(
            scenario_name=f"Interest Rate Shock (+{rate_change_pct}%)",
            initial_value=initial_value,
            final_value=final_value,
            loss=loss,
            loss_pct=loss_pct,
            survives=final_value > 0,
            worst_position=None,
            recovery_time_days=None,
            margin_call_risk=loss_pct > 50,
            details={
                "rate_change_pct": rate_change_pct,
                "days": days,
                "rate_sensitive_value": rate_sensitive_value,
                "rate_sensitive_loss": rate_sensitive_loss,
                "other_value": other_value,
                "other_loss": other_loss
            }
        )

    def run_custom_scenario(
        self,
        account_id: int,
        scenario_name: str,
        stock_impacts: Dict[str, float],
        days: int = 1
    ) -> StressTestResult:
        """
        Run a custom stress scenario with specified stock impacts

        Args:
            account_id: Account ID
            scenario_name: Name of the custom scenario
            stock_impacts: Dict mapping stock symbols to percentage changes
            days: Duration in days

        Returns:
            StressTestResult with scenario outcome
        """
        initial_value = self.get_portfolio_value(account_id)
        holdings = self.get_holdings(account_id)

        total_loss = 0
        worst_position = None
        max_loss = 0

        for holding in holdings:
            impact = stock_impacts.get(holding.stock, 0)
            if impact < 0:  # Loss
                holding_loss = holding.current_value * abs(impact) / 100
                total_loss += holding_loss

                if holding_loss > max_loss:
                    max_loss = holding_loss
                    worst_position = {
                        "stock": holding.stock,
                        "loss_pct": abs(impact),
                        "loss_amount": holding_loss
                    }

        final_value = initial_value - total_loss
        loss = total_loss
        loss_pct = (loss / initial_value * 100) if initial_value > 0 else 0

        return StressTestResult(
            scenario_name=scenario_name,
            initial_value=initial_value,
            final_value=final_value,
            loss=loss,
            loss_pct=loss_pct,
            survives=final_value > 0,
            worst_position=worst_position,
            recovery_time_days=None,
            margin_call_risk=loss_pct > 50,
            details={
                "stock_impacts": stock_impacts,
                "days": days,
                "affected_stocks": len([s for s in stock_impacts.keys() if s in [h.stock for h in holdings]])
            }
        )

    def run_comprehensive_stress_test(
        self,
        account_id: int
    ) -> Dict[str, Any]:
        """
        Run comprehensive stress test with multiple scenarios

        Args:
            account_id: Account ID

        Returns:
            Dict with all stress test results
        """
        scenarios = []

        # Market crash scenarios
        for crash_pct in [-10, -20, -30]:
            try:
                result = self.run_market_crash_scenario(account_id, crash_pct)
                scenarios.append(result)
            except Exception as e:
                logger.error(f"Error in market crash scenario: {e}")

        # Sector crash scenarios
        for sector in ["IT", "Banking", "Auto"]:
            try:
                result = self.run_sector_crash_scenario(account_id, sector, -25)
                scenarios.append(result)
            except Exception as e:
                logger.error(f"Error in sector crash scenario: {e}")

        # Volatility spike
        try:
            result = self.run_volatility_spike_scenario(account_id, 3.0)
            scenarios.append(result)
        except Exception as e:
            logger.error(f"Error in volatility spike scenario: {e}")

        # Liquidity crisis
        try:
            result = self.run_liquidity_crisis_scenario(account_id, -15)
            scenarios.append(result)
        except Exception as e:
            logger.error(f"Error in liquidity crisis scenario: {e}")

        # Interest rate shock
        try:
            result = self.run_interest_rate_shock_scenario(account_id, 2.0)
            scenarios.append(result)
        except Exception as e:
            logger.error(f"Error in interest rate shock scenario: {e}")

        # Calculate summary statistics
        losses = [s.loss_pct for s in scenarios]
        worst_case = max(scenarios, key=lambda x: x.loss_pct)
        best_case = min(scenarios, key=lambda x: x.loss_pct)
        avg_loss = np.mean(losses)

        # Count scenarios where portfolio survives
        surviving_scenarios = sum(1 for s in scenarios if s.survives)
        margin_call_scenarios = sum(1 for s in scenarios if s.margin_call_risk)

        return {
            "account_id": account_id,
            "initial_value": scenarios[0].initial_value if scenarios else 0,
            "scenarios": [
                {
                    "name": s.scenario_name,
                    "loss_pct": s.loss_pct,
                    "survives": s.survives,
                    "margin_call_risk": s.margin_call_risk
                }
                for s in scenarios
            ],
            "summary": {
                "total_scenarios": len(scenarios),
                "worst_case": {
                    "name": worst_case.scenario_name,
                    "loss_pct": worst_case.loss_pct
                },
                "best_case": {
                    "name": best_case.scenario_name,
                    "loss_pct": best_case.loss_pct
                },
                "average_loss_pct": float(avg_loss),
                "surviving_scenarios": surviving_scenarios,
                "survival_rate": (surviving_scenarios / len(scenarios) * 100) if scenarios else 0,
                "margin_call_scenarios": margin_call_scenarios,
                "margin_call_rate": (margin_call_scenarios / len(scenarios) * 100) if scenarios else 0
            },
            "recommendations": self._generate_stress_test_recommendations(scenarios)
        }

    def _generate_stress_test_recommendations(
        self,
        scenarios: List[StressTestResult]
    ) -> List[Dict[str, str]]:
        """Generate recommendations based on stress test results"""
        recommendations = []

        if not scenarios:
            return recommendations

        # Check worst case
        worst_case = max(scenarios, key=lambda x: x.loss_pct)
        if worst_case.loss_pct > 40:
            recommendations.append({
                "priority": "critical",
                "type": "risk",
                "message": f"Worst case scenario ({worst_case.scenario_name}) shows {worst_case.loss_pct:.1f}% loss. "
                          f"Consider reducing overall exposure or adding hedges."
            })
        elif worst_case.loss_pct > 25:
            recommendations.append({
                "priority": "high",
                "type": "risk",
                "message": f"Worst case scenario ({worst_case.scenario_name}) shows {worst_case.loss_pct:.1f}% loss. "
                          f"Review position sizing and risk management."
            })

        # Check margin call risk
        margin_call_count = sum(1 for s in scenarios if s.margin_call_risk)
        if margin_call_count > len(scenarios) / 2:
            recommendations.append({
                "priority": "critical",
                "type": "margin",
                "message": f"Margin call risk in {margin_call_count}/{len(scenarios)} scenarios. "
                          f"Reduce leverage or increase capital buffer."
            })

        # Check survival rate
        survival_rate = sum(1 for s in scenarios if s.survives) / len(scenarios) * 100
        if survival_rate < 80:
            recommendations.append({
                "priority": "high",
                "type": "survival",
                "message": f"Portfolio survival rate is only {survival_rate:.1f}%. "
                          f"Consider more conservative positioning."
            })

        # Check sector concentration
        sector_crashes = [s for s in scenarios if "Sector" in s.scenario_name]
        if sector_crashes:
            max_sector_loss = max(s.loss_pct for s in sector_crashes)
            if max_sector_loss > 20:
                recommendations.append({
                    "priority": "medium",
                    "type": "diversification",
                    "message": f"High sector concentration risk. Consider diversifying across sectors."
                })

        if not recommendations:
            recommendations.append({
                "priority": "low",
                "type": "general",
                "message": "Portfolio shows good resilience across stress scenarios."
            })

        return recommendations

    def get_stress_test_report(
        self,
        account_id: int
    ) -> Dict[str, Any]:
        """
        Generate comprehensive stress test report

        Args:
            account_id: Account ID

        Returns:
            Dict with complete stress test report
        """
        comprehensive_result = self.run_comprehensive_stress_test(account_id)

        # Get current portfolio composition
        holdings = self.get_holdings(account_id)
        positions = self.get_positions(account_id)

        # Calculate concentration metrics
        total_value = sum(h.current_value for h in holdings)
        max_single_position = max((h.current_value for h in holdings)) if holdings else 0
        concentration_pct = (max_single_position / total_value * 100) if total_value > 0 else 0

        return {
            "account_id": account_id,
            "generated_at": datetime.utcnow().isoformat(),
            "portfolio_summary": {
                "total_value": total_value,
                "holdings_count": len(holdings),
                "positions_count": len(positions),
                "max_single_position_pct": concentration_pct
            },
            "stress_test_results": comprehensive_result,
            "risk_assessment": {
                "overall_risk_level": self._assess_overall_risk(comprehensive_result),
                "key_vulnerabilities": self._identify_vulnerabilities(comprehensive_result),
                "mitigation_strategies": self._suggest_mitigation_strategies(comprehensive_result)
            }
        }

    def _assess_overall_risk(self, stress_result: Dict[str, Any]) -> str:
        """Assess overall risk level from stress test results"""
        avg_loss = stress_result["summary"]["average_loss_pct"]
        survival_rate = stress_result["summary"]["survival_rate"]
        margin_call_rate = stress_result["summary"]["margin_call_rate"]

        if avg_loss > 30 or survival_rate < 70 or margin_call_rate > 50:
            return "CRITICAL"
        elif avg_loss > 20 or survival_rate < 85 or margin_call_rate > 30:
            return "HIGH"
        elif avg_loss > 15 or survival_rate < 95 or margin_call_rate > 15:
            return "MODERATE"
        else:
            return "LOW"

    def _identify_vulnerabilities(self, stress_result: Dict[str, Any]) -> List[str]:
        """Identify key vulnerabilities from stress test results"""
        vulnerabilities = []

        scenarios = stress_result["scenarios"]
        for scenario in scenarios:
            if scenario["loss_pct"] > 25:
                vulnerabilities.append(f"High loss in {scenario['name']} scenario")
            if scenario["margin_call_risk"]:
                vulnerabilities.append(f"Margin call risk in {scenario['name']} scenario")

        if stress_result["summary"]["survival_rate"] < 90:
            vulnerabilities.append("Low survival rate across scenarios")

        return vulnerabilities

    def _suggest_mitigation_strategies(self, stress_result: Dict[str, Any]) -> List[str]:
        """Suggest risk mitigation strategies"""
        strategies = []

        if stress_result["summary"]["margin_call_rate"] > 30:
            strategies.append("Reduce leverage and increase capital buffer")
            strategies.append("Use stop-loss orders to limit downside")

        if stress_result["summary"]["average_loss_pct"] > 20:
            strategies.append("Diversify across sectors and asset classes")
            strategies.append("Consider hedging with options or futures")

        worst_case = stress_result["summary"]["worst_case"]
        if worst_case["loss_pct"] > 30:
            strategies.append(f"Prepare for {worst_case['name']} scenario with contingency plans")

        strategies.append("Regular stress testing and portfolio review")

        return strategies


if __name__ == "__main__":
    from database import SessionLocal

    db = SessionLocal()
    stress_manager = StressTestingManager(db)

    print("Stress Testing Manager initialized")
    print("Available scenario types:")
    for scenario_type in StressScenarioType:
        print(f"  - {scenario_type.value}")

    db.close()
