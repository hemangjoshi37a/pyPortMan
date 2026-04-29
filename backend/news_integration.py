"""
News Integration Manager for pyPortMan
Fetch and display relevant news for watchlist stocks
"""

import logging
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session

from models import Account, NewsItem, Watchlist

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


class NewsIntegrationManager:
    """Manager for news integration"""

    def __init__(self, db: Session):
        self.db = db

    def fetch_news_for_stock(
        self,
        stock: str,
        exchange: str = "NSE",
        days: int = 7
    ) -> List[NewsItem]:
        """
        Fetch news for a specific stock
        """
        # In production, integrate with actual news APIs like:
        # - NewsAPI.org
        # - Alpha Vantage
        # - Yahoo Finance
        # - Google News

        # For demonstration, we'll create sample news items
        news_items = self._generate_sample_news(stock, days)

        # Save to database
        for news in news_items:
            existing = self.db.query(NewsItem).filter(
                NewsItem.stock == stock,
                NewsItem.title == news["title"]
            ).first()

            if not existing:
                news_record = NewsItem(
                    stock=stock,
                    exchange=exchange,
                    title=news["title"],
                    summary=news["summary"],
                    url=news["url"],
                    source=news["source"],
                    published_at=news["published_at"],
                    sentiment=news["sentiment"],
                    relevance_score=news["relevance_score"]
                )
                self.db.add(news_record)

        self.db.commit()

        logger.info(f"Fetched {len(news_items)} news items for {stock}")
        return news_items

    def _generate_sample_news(self, stock: str, days: int) -> List[Dict[str, Any]]:
        """
        Generate sample news items for demonstration
        In production, replace with actual API calls
        """
        sample_news = []

        # Sample news templates
        templates = [
            {
                "title": f"{stock} shares surge on strong quarterly results",
                "summary": f"{stock} reported better-than-expected earnings for the quarter, driving investor confidence.",
                "sentiment": "POSITIVE",
                "source": "Economic Times"
            },
            {
                "title": f"{stock} announces new strategic partnership",
                "summary": f"{stock} has entered into a strategic partnership to expand its market presence.",
                "sentiment": "POSITIVE",
                "source": "Moneycontrol"
            },
            {
                "title": f"Analysts maintain 'Buy' rating on {stock}",
                "summary": f"Multiple brokerage firms have maintained their positive outlook on {stock} stock.",
                "sentiment": "POSITIVE",
                "source": "Business Standard"
            },
            {
                "title": f"{stock} faces regulatory scrutiny",
                "summary": f"Regulatory authorities have raised concerns about {stock}'s business practices.",
                "sentiment": "NEGATIVE",
                "source": "Reuters"
            },
            {
                "title": f"{stock} stock volatile amid market uncertainty",
                "summary": f"{stock} experienced significant volatility as investors react to broader market trends.",
                "sentiment": "NEUTRAL",
                "source": "Mint"
            }
        ]

        # Generate news items for the past few days
        for i in range(min(days, len(templates))):
            template = templates[i]
            published_at = datetime.utcnow() - timedelta(days=i)

            sample_news.append({
                "title": template["title"],
                "summary": template["summary"],
                "url": f"https://example.com/news/{stock.lower()}/{i}",
                "source": template["source"],
                "published_at": published_at,
                "sentiment": template["sentiment"],
                "relevance_score": 0.8 + (i * 0.05)  # Decreasing relevance for older news
            })

        return sample_news

    def fetch_news_for_watchlist(
        self,
        account_id: int,
        days: int = 7
    ) -> Dict[str, List[NewsItem]]:
        """
        Fetch news for all stocks in watchlist
        """
        watchlist = self.db.query(Watchlist).filter(
            Watchlist.account_id == account_id,
            Watchlist.is_active == True
        ).all()

        news_by_stock = {}

        for item in watchlist:
            try:
                news = self.fetch_news_for_stock(item.stock, item.exchange, days)
                news_by_stock[item.stock] = news
            except Exception as e:
                logger.error(f"Error fetching news for {item.stock}: {e}")

        return news_by_stock

    def get_news(
        self,
        stock: Optional[str] = None,
        days: int = 7,
        limit: int = 20
    ) -> List[NewsItem]:
        """
        Get news items with optional filters
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        query = self.db.query(NewsItem).filter(
            NewsItem.published_at >= cutoff
        )

        if stock:
            query = query.filter(NewsItem.stock == stock)

        return query.order_by(
            NewsItem.published_at.desc(),
            NewsItem.relevance_score.desc()
        ).limit(limit).all()

    def get_news_summary(
        self,
        account_id: Optional[int] = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get summary of news for watchlist stocks
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        query = self.db.query(NewsItem).filter(
            NewsItem.published_at >= cutoff
        )

        if account_id:
            # Get stocks from watchlist
            watchlist = self.db.query(Watchlist).filter(
                Watchlist.account_id == account_id,
                Watchlist.is_active == True
            ).all()
            stocks = [w.stock for w in watchlist]
            query = query.filter(NewsItem.stock.in_(stocks))

        news_items = query.all()

        # Count by sentiment
        positive = len([n for n in news_items if n.sentiment == "POSITIVE"])
        negative = len([n for n in news_items if n.sentiment == "NEGATIVE"])
        neutral = len([n for n in news_items if n.sentiment == "NEUTRAL"])

        # Group by stock
        news_by_stock = {}
        for news in news_items:
            if news.stock not in news_by_stock:
                news_by_stock[news.stock] = []
            news_by_stock[news.stock].append(news)

        # Calculate average relevance
        avg_relevance = sum(n.relevance_score for n in news_items) / len(news_items) if news_items else 0

        return {
            "total_news": len(news_items),
            "positive": positive,
            "negative": negative,
            "neutral": neutral,
            "sentiment_distribution": {
                "positive_pct": (positive / len(news_items) * 100) if news_items else 0,
                "negative_pct": (negative / len(news_items) * 100) if news_items else 0,
                "neutral_pct": (neutral / len(news_items) * 100) if news_items else 0
            },
            "news_by_stock": {
                stock: len(items) for stock, items in news_by_stock.items()
            },
            "avg_relevance_score": avg_relevance,
            "period_days": days
        }

    def get_sentiment_analysis(
        self,
        stock: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get sentiment analysis for a stock
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        news_items = self.db.query(NewsItem).filter(
            NewsItem.stock == stock,
            NewsItem.published_at >= cutoff
        ).all()

        if not news_items:
            return {
                "stock": stock,
                "message": "No news data available",
                "sentiment": "NEUTRAL"
            }

        # Calculate sentiment scores
        positive_count = len([n for n in news_items if n.sentiment == "POSITIVE"])
        negative_count = len([n for n in news_items if n.sentiment == "NEGATIVE"])
        neutral_count = len([n for n in news_items if n.sentiment == "NEUTRAL"])

        total = len(news_items)

        # Calculate weighted sentiment
        sentiment_score = (positive_count - negative_count) / total if total > 0 else 0

        # Determine overall sentiment
        if sentiment_score > 0.3:
            overall_sentiment = "BULLISH"
        elif sentiment_score < -0.3:
            overall_sentiment = "BEARISH"
        else:
            overall_sentiment = "NEUTRAL"

        # Calculate sentiment trend
        recent_news = sorted(news_items, key=lambda n: n.published_at, reverse=True)[:5]
        recent_positive = len([n for n in recent_news if n.sentiment == "POSITIVE"])
        recent_negative = len([n for n in recent_news if n.sentiment == "NEGATIVE"])

        recent_trend = "IMPROVING" if recent_positive > recent_negative else "DECLINING" if recent_negative > recent_positive else "STABLE"

        return {
            "stock": stock,
            "period_days": days,
            "total_news": total,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": neutral_count,
            "sentiment_score": round(sentiment_score, 2),
            "overall_sentiment": overall_sentiment,
            "recent_trend": recent_trend,
            "positive_pct": round(positive_count / total * 100, 2) if total > 0 else 0,
            "negative_pct": round(negative_count / total * 100, 2) if total > 0 else 0
        }

    def get_top_stories(
        self,
        account_id: Optional[int] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get top news stories by relevance
        """
        query = self.db.query(NewsItem)

        if account_id:
            # Get stocks from watchlist
            watchlist = self.db.query(Watchlist).filter(
                Watchlist.account_id == account_id,
                Watchlist.is_active == True
            ).all()
            stocks = [w.stock for w in watchlist]
            query = query.filter(NewsItem.stock.in_(stocks))

        news_items = query.order_by(
            NewsItem.relevance_score.desc(),
            NewsItem.published_at.desc()
        ).limit(limit).all()

        return [
            {
                "id": news.id,
                "stock": news.stock,
                "title": news.title,
                "summary": news.summary,
                "url": news.url,
                "source": news.source,
                "published_at": news.published_at.isoformat(),
                "sentiment": news.sentiment,
                "relevance_score": news.relevance_score
            }
            for news in news_items
        ]

    def search_news(
        self,
        query: str,
        limit: int = 20
    ) -> List[NewsItem]:
        """
        Search news by keyword
        """
        news_items = self.db.query(NewsItem).filter(
            NewsItem.title.ilike(f"%{query}%")
        ).order_by(
            NewsItem.published_at.desc()
        ).limit(limit).all()

        return news_items

    def cleanup_old_news(self, days: int = 90) -> int:
        """
        Clean up old news items
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        deleted = self.db.query(NewsItem).filter(
            NewsItem.published_at < cutoff
        ).delete()

        self.db.commit()

        logger.info(f"Cleaned up {deleted} old news items")
        return deleted
