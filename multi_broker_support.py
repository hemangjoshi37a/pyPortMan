"""
Multi-Broker Support Module
Support for 5Paisa, Upstox, Dhan brokers with unified portfolio view
"""

import requests
import pandas as pd
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import time


class BrokerBase:
    """Base class for all broker integrations"""

    def __init__(self, api_key: str, api_secret: str, user_id: str, password: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.user_id = user_id
        self.password = password
        self.access_token = None
        self.session = requests.Session()
        self.broker_name = "base"

    def login(self) -> bool:
        """Login to broker API"""
        raise NotImplementedError

    def get_holdings(self) -> List[Dict]:
        """Get holdings"""
        raise NotImplementedError

    def get_positions(self) -> List[Dict]:
        """Get positions"""
        raise NotImplementedError

    def get_orders(self) -> List[Dict]:
        """Get orders"""
        raise NotImplementedError

    def place_order(self, order_params: Dict) -> Dict:
        """Place order"""
        raise NotImplementedError

    def cancel_order(self, order_id: str) -> Dict:
        """Cancel order"""
        raise NotImplementedError

    def get_quote(self, symbol: str) -> Dict:
        """Get quote for symbol"""
        raise NotImplementedError


class FivePaisaBroker(BrokerBase):
    """5Paisa Broker Integration"""

    def __init__(self, api_key: str, api_secret: str, user_id: str, password: str, client_id: str):
        super().__init__(api_key, api_secret, user_id, password)
        self.client_id = client_id
        self.broker_name = "5paisa"
        self.base_url = "https://openapi.5paisa.com/VendorsAPI/Service1.svc"

    def login(self) -> bool:
        """Login to 5Paisa API"""
        try:
            login_url = f"{self.base_url}/LoginRequest"
            payload = {
                "ClientCode": self.user_id,
                "Password": self.password,
                "APIKey": self.api_key,
                "LocalIP": "127.0.0.1",
                "PublicIP": "127.0.0.1",
                "ConnectionID": str(int(time.time()))
            }

            response = self.session.post(login_url, json=payload)
            data = response.json()

            if data.get("Status") == "Success":
                self.access_token = data.get("SessionID")
                return True
            return False
        except Exception as e:
            print(f"5Paisa login error: {e}")
            return False

    def get_holdings(self) -> List[Dict]:
        """Get holdings from 5Paisa"""
        try:
            url = f"{self.base_url}/Holdings"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = self.session.get(url, headers=headers)
            data = response.json()
            return data.get("Data", [])
        except Exception as e:
            print(f"5Paisa holdings error: {e}")
            return []

    def get_positions(self) -> List[Dict]:
        """Get positions from 5Paisa"""
        try:
            url = f"{self.base_url}/Position"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = self.session.get(url, headers=headers)
            data = response.json()
            return data.get("Data", [])
        except Exception as e:
            print(f"5Paisa positions error: {e}")
            return []

    def get_orders(self) -> List[Dict]:
        """Get orders from 5Paisa"""
        try:
            url = f"{self.base_url}/OrderBook"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = self.session.get(url, headers=headers)
            data = response.json()
            return data.get("Data", [])
        except Exception as e:
            print(f"5Paisa orders error: {e}")
            return []

    def place_order(self, order_params: Dict) -> Dict:
        """Place order on 5Paisa"""
        try:
            url = f"{self.base_url}/PlaceOrder"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = self.session.post(url, json=order_params, headers=headers)
            return response.json()
        except Exception as e:
            print(f"5Paisa place order error: {e}")
            return {"error": str(e)}

    def cancel_order(self, order_id: str) -> Dict:
        """Cancel order on 5Paisa"""
        try:
            url = f"{self.base_url}/CancelOrder"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            payload = {"OrderID": order_id}
            response = self.session.post(url, json=payload, headers=headers)
            return response.json()
        except Exception as e:
            print(f"5Paisa cancel order error: {e}")
            return {"error": str(e)}

    def get_quote(self, symbol: str) -> Dict:
        """Get quote from 5Paisa"""
        try:
            url = f"{self.base_url}/GetQuote"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            payload = {"Symbol": symbol}
            response = self.session.post(url, json=payload, headers=headers)
            return response.json()
        except Exception as e:
            print(f"5Paisa quote error: {e}")
            return {}


class UpstoxBroker(BrokerBase):
    """Upstox Broker Integration"""

    def __init__(self, api_key: str, api_secret: str, user_id: str, password: str, redirect_uri: str = "http://127.0.0.1:5000"):
        super().__init__(api_key, api_secret, user_id, password)
        self.redirect_uri = redirect_uri
        self.broker_name = "upstox"
        self.base_url = "https://api.upstox.com/v2"

    def login(self) -> bool:
        """Login to Upstox API"""
        try:
            # For Upstox, typically need OAuth flow
            # This is a simplified version
            auth_url = f"{self.base_url}/login/authorization/dialog"
            params = {
                "client_id": self.api_key,
                "redirect_uri": self.redirect_uri,
                "response_type": "code"
            }
            # In production, this would redirect user to browser
            # For now, assuming access_token is already obtained
            return True
        except Exception as e:
            print(f"Upstox login error: {e}")
            return False

    def get_holdings(self) -> List[Dict]:
        """Get holdings from Upstox"""
        try:
            url = f"{self.base_url}/portfolio/long-term-positions"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json"
            }
            response = self.session.get(url, headers=headers)
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            print(f"Upstox holdings error: {e}")
            return []

    def get_positions(self) -> List[Dict]:
        """Get positions from Upstox"""
        try:
            url = f"{self.base_url}/portfolio/positions"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json"
            }
            response = self.session.get(url, headers=headers)
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            print(f"Upstox positions error: {e}")
            return []

    def get_orders(self) -> List[Dict]:
        """Get orders from Upstox"""
        try:
            url = f"{self.base_url}/order/retrieve-all"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json"
            }
            response = self.session.get(url, headers=headers)
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            print(f"Upstox orders error: {e}")
            return []

    def place_order(self, order_params: Dict) -> Dict:
        """Place order on Upstox"""
        try:
            url = f"{self.base_url}/order/place"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            response = self.session.post(url, json=order_params, headers=headers)
            return response.json()
        except Exception as e:
            print(f"Upstox place order error: {e}")
            return {"error": str(e)}

    def cancel_order(self, order_id: str) -> Dict:
        """Cancel order on Upstox"""
        try:
            url = f"{self.base_url}/order/cancel"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            payload = {"order_id": order_id}
            response = self.session.post(url, json=payload, headers=headers)
            return response.json()
        except Exception as e:
            print(f"Upstox cancel order error: {e}")
            return {"error": str(e)}

    def get_quote(self, symbol: str) -> Dict:
        """Get quote from Upstox"""
        try:
            url = f"{self.base_url}/market-quote/quotes"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json"
            }
            params = {"instrument_key": symbol}
            response = self.session.get(url, headers=headers, params=params)
            data = response.json()
            return data.get("data", {})
        except Exception as e:
            print(f"Upstox quote error: {e}")
            return {}


class DhanBroker(BrokerBase):
    """Dhan Broker Integration"""

    def __init__(self, api_key: str, api_secret: str, user_id: str, password: str, client_id: str):
        super().__init__(api_key, api_secret, user_id, password)
        self.client_id = client_id
        self.broker_name = "dhan"
        self.base_url = "https://api.dhan.co"

    def login(self) -> bool:
        """Login to Dhan API"""
        try:
            login_url = f"{self.base_url}/oauth/token"
            payload = {
                "client_id": self.api_key,
                "client_secret": self.api_secret,
                "grant_type": "password",
                "username": self.user_id,
                "password": self.password
            }

            response = self.session.post(login_url, json=payload)
            data = response.json()

            if "access_token" in data:
                self.access_token = data["access_token"]
                return True
            return False
        except Exception as e:
            print(f"Dhan login error: {e}")
            return False

    def get_holdings(self) -> List[Dict]:
        """Get holdings from Dhan"""
        try:
            url = f"{self.base_url}/holdings"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "client-id": self.client_id
            }
            response = self.session.get(url, headers=headers)
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            print(f"Dhan holdings error: {e}")
            return []

    def get_positions(self) -> List[Dict]:
        """Get positions from Dhan"""
        try:
            url = f"{self.base_url}/positions"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "client-id": self.client_id
            }
            response = self.session.get(url, headers=headers)
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            print(f"Dhan positions error: {e}")
            return []

    def get_orders(self) -> List[Dict]:
        """Get orders from Dhan"""
        try:
            url = f"{self.base_url}/orders"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "client-id": self.client_id
            }
            response = self.session.get(url, headers=headers)
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            print(f"Dhan orders error: {e}")
            return []

    def place_order(self, order_params: Dict) -> Dict:
        """Place order on Dhan"""
        try:
            url = f"{self.base_url}/orders"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "client-id": self.client_id,
                "Content-Type": "application/json"
            }
            response = self.session.post(url, json=order_params, headers=headers)
            return response.json()
        except Exception as e:
            print(f"Dhan place order error: {e}")
            return {"error": str(e)}

    def cancel_order(self, order_id: str) -> Dict:
        """Cancel order on Dhan"""
        try:
            url = f"{self.base_url}/orders/{order_id}"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "client-id": self.client_id
            }
            response = self.session.delete(url, headers=headers)
            return response.json()
        except Exception as e:
            print(f"Dhan cancel order error: {e}")
            return {"error": str(e)}

    def get_quote(self, symbol: str) -> Dict:
        """Get quote from Dhan"""
        try:
            url = f"{self.base_url}/market-quote/quotes"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "client-id": self.client_id
            }
            params = {"symbols": symbol}
            response = self.session.get(url, headers=headers, params=params)
            data = response.json()
            return data.get("data", {})
        except Exception as e:
            print(f"Dhan quote error: {e}")
            return {}


class UnifiedPortfolioManager:
    """Unified portfolio manager for multiple brokers"""

    def __init__(self):
        self.brokers: Dict[str, BrokerBase] = {}
        self.portfolio_data = {}

    def add_broker(self, broker_name: str, broker: BrokerBase):
        """Add a broker to the portfolio manager"""
        self.brokers[broker_name] = broker

    def login_all(self) -> Dict[str, bool]:
        """Login to all brokers"""
        results = {}
        for name, broker in self.brokers.items():
            results[name] = broker.login()
        return results

    def get_unified_holdings(self) -> pd.DataFrame:
        """Get unified holdings across all brokers"""
        all_holdings = []

        for broker_name, broker in self.brokers.items():
            holdings = broker.get_holdings()
            for holding in holdings:
                holding["broker"] = broker_name
                all_holdings.append(holding)

        return pd.DataFrame(all_holdings)

    def get_unified_positions(self) -> pd.DataFrame:
        """Get unified positions across all brokers"""
        all_positions = []

        for broker_name, broker in self.brokers.items():
            positions = broker.get_positions()
            for position in positions:
                position["broker"] = broker_name
                all_positions.append(position)

        return pd.DataFrame(all_positions)

    def get_unified_orders(self) -> pd.DataFrame:
        """Get unified orders across all brokers"""
        all_orders = []

        for broker_name, broker in self.brokers.items():
            orders = broker.get_orders()
            for order in orders:
                order["broker"] = broker_name
                all_orders.append(order)

        return pd.DataFrame(all_orders)

    def get_portfolio_summary(self) -> Dict:
        """Get portfolio summary across all brokers"""
        summary = {
            "total_investment": 0,
            "current_value": 0,
            "total_pnl": 0,
            "broker_breakdown": {}
        }

        for broker_name, broker in self.brokers.items():
            holdings = broker.get_holdings()
            broker_investment = 0
            broker_value = 0
            broker_pnl = 0

            for holding in holdings:
                investment = holding.get("investment_value", 0)
                current = holding.get("current_value", 0)
                pnl = holding.get("pnl", 0)

                broker_investment += investment
                broker_value += current
                broker_pnl += pnl

            summary["broker_breakdown"][broker_name] = {
                "investment": broker_investment,
                "current_value": broker_value,
                "pnl": broker_pnl
            }

            summary["total_investment"] += broker_investment
            summary["current_value"] += broker_value
            summary["total_pnl"] += broker_pnl

        return summary

    def find_arbitrage_opportunities(self, symbols: List[str]) -> pd.DataFrame:
        """Find arbitrage opportunities across brokers"""
        opportunities = []

        for symbol in symbols:
            quotes = {}
            for broker_name, broker in self.brokers.items():
                quote = broker.get_quote(symbol)
                if quote:
                    quotes[broker_name] = quote.get("last_price", 0)

            if len(quotes) >= 2:
                prices = list(quotes.values())
                min_price = min(prices)
                max_price = max(prices)
                spread = max_price - min_price
                spread_pct = (spread / min_price) * 100

                if spread_pct > 0.1:  # More than 0.1% spread
                    opportunities.append({
                        "symbol": symbol,
                        "min_price": min_price,
                        "max_price": max_price,
                        "spread": spread,
                        "spread_pct": spread_pct,
                        "buy_from": min(quotes, key=quotes.get),
                        "sell_to": max(quotes, key=quotes.get),
                        "quotes": quotes
                    })

        return pd.DataFrame(opportunities)

    def place_cross_broker_order(self, buy_broker: str, sell_broker: str,
                                  symbol: str, quantity: int) -> Dict:
        """Place cross-broker arbitrage order"""
        results = {
            "buy_order": None,
            "sell_order": None,
            "status": "failed"
        }

        try:
            # Place buy order
            buy_order = self.brokers[buy_broker].place_order({
                "symbol": symbol,
                "quantity": quantity,
                "transaction_type": "BUY",
                "order_type": "MARKET"
            })
            results["buy_order"] = buy_order

            # Place sell order
            sell_order = self.brokers[sell_broker].place_order({
                "symbol": symbol,
                "quantity": quantity,
                "transaction_type": "SELL",
                "order_type": "MARKET"
            })
            results["sell_order"] = sell_order

            if buy_order.get("status") == "success" and sell_order.get("status") == "success":
                results["status"] = "success"

        except Exception as e:
            results["error"] = str(e)

        return results

    def export_portfolio(self, format: str = "excel") -> str:
        """Export unified portfolio data"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if format == "excel":
            filename = f"unified_portfolio_{timestamp}.xlsx"
            with pd.ExcelWriter(filename) as writer:
                self.get_unified_holdings().to_excel(writer, sheet_name="Holdings", index=False)
                self.get_unified_positions().to_excel(writer, sheet_name="Positions", index=False)
                self.get_unified_orders().to_excel(writer, sheet_name="Orders", index=False)

                summary_df = pd.DataFrame([self.get_portfolio_summary()])
                summary_df.to_excel(writer, sheet_name="Summary", index=False)

        elif format == "json":
            filename = f"unified_portfolio_{timestamp}.json"
            data = {
                "holdings": self.get_unified_holdings().to_dict("records"),
                "positions": self.get_unified_positions().to_dict("records"),
                "orders": self.get_unified_orders().to_dict("records"),
                "summary": self.get_portfolio_summary()
            }
            with open(filename, "w") as f:
                json.dump(data, f, indent=2)

        return filename


# Factory function to create broker instances
def create_broker(broker_type: str, **kwargs) -> BrokerBase:
    """Factory function to create broker instances"""
    broker_map = {
        "5paisa": FivePaisaBroker,
        "upstox": UpstoxBroker,
        "dhan": DhanBroker
    }

    broker_class = broker_map.get(broker_type.lower())
    if broker_class:
        return broker_class(**kwargs)
    raise ValueError(f"Unsupported broker type: {broker_type}")
