"""
Crypto News Monitor - Fetch and analyze crypto news for trading signals
"""
import os
import requests
from typing import List, Dict
from datetime import datetime, timedelta
from loguru import logger
import feedparser

# News sources (free RSS feeds)
NEWS_SOURCES = {
    'coindesk': 'https://www.coindesk.com/arc/outboundfeeds/rss/',
    'cointelegraph': 'https://cointelegraph.com/rss',
    'decrypt': 'https://decrypt.co/feed',
    'bitcoinist': 'https://bitcoinist.com/feed/',
}

# Keywords for BTC, ETH, SOL
ASSET_KEYWORDS = {
    'BTCUSDT': ['bitcoin', 'btc', 'satoshi'],
    'ETHUSDT': ['ethereum', 'eth', 'vitalik', 'eip'],
    'SOLUSDT': ['solana', 'sol', 'anatoly']
}

# Bullish keywords
BULLISH_KEYWORDS = [
    'bullish', 'surge', 'rally', 'breakout', 'moon', 'pump',
    'adoption', 'institutional', 'all-time high', 'ath',
    'breakthrough', 'partnership', 'upgrade', 'approved'
]

# Bearish keywords
BEARISH_KEYWORDS = [
    'bearish', 'crash', 'dump', 'plunge', 'decline', 'fall',
    'hack', 'scam', 'regulation', 'ban', 'sec lawsuit',
    'collapse', 'drop', 'sell-off'
]


class NewsMonitor:
    """Monitor crypto news for trading signals"""
    
    def __init__(self):
        self.last_check = datetime.now() - timedelta(hours=1)
        logger.info("News Monitor initialized")
    
    def fetch_recent_news(self, hours: int = 6) -> List[Dict]:
        """Fetch news from the last N hours"""
        all_news = []
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        for source_name, feed_url in NEWS_SOURCES.items():
            try:
                logger.info(f"Fetching news from {source_name}...")
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries[:20]:  # Get latest 20 from each
                    # Parse publish date
                    pub_date = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_date = datetime(*entry.published_parsed[:6])
                    
                    # Skip old news
                    if pub_date and pub_date < cutoff_time:
                        continue
                    
                    title = entry.get('title', '')
                    summary = entry.get('summary', '')
                    link = entry.get('link', '')
                    
                    all_news.append({
                        'source': source_name,
                        'title': title,
                        'summary': summary,
                        'link': link,
                        'published': pub_date.isoformat() if pub_date else None
                    })
                
                logger.info(f"  Found {len([n for n in all_news if n['source'] == source_name])} recent articles")
                
            except Exception as e:
                logger.error(f"Error fetching {source_name}: {e}")
        
        logger.info(f"Total recent news: {len(all_news)}")
        return all_news
    
    def analyze_sentiment(self, text: str) -> Dict:
        """Analyze sentiment of text (simple keyword-based)"""
        text_lower = text.lower()
        
        bullish_score = sum(1 for keyword in BULLISH_KEYWORDS if keyword in text_lower)
        bearish_score = sum(1 for keyword in BEARISH_KEYWORDS if keyword in text_lower)
        
        if bullish_score > bearish_score:
            sentiment = 'bullish'
            score = bullish_score
        elif bearish_score > bullish_score:
            sentiment = 'bearish'
            score = bearish_score
        else:
            sentiment = 'neutral'
            score = 0
        
        return {
            'sentiment': sentiment,
            'score': score,
            'bullish_keywords': bullish_score,
            'bearish_keywords': bearish_score
        }
    
    def get_asset_news_signal(self, symbol: str, hours: int = 6) -> Dict:
        """Get news signal for a specific asset"""
        news = self.fetch_recent_news(hours=hours)
        
        # Filter news relevant to this asset
        keywords = ASSET_KEYWORDS.get(symbol, [])
        relevant_news = []
        
        for article in news:
            text = f"{article['title']} {article['summary']}".lower()
            if any(keyword in text for keyword in keywords):
                relevant_news.append(article)
        
        if not relevant_news:
            return {
                'symbol': symbol,
                'signal': 'NEUTRAL',
                'strength': 0,
                'reason': 'No recent news found',
                'article_count': 0,
                'bullish_count': 0,
                'bearish_count': 0,
                'top_headlines': []
            }
        
        # Analyze sentiment of relevant news
        bullish_count = 0
        bearish_count = 0
        total_bullish_score = 0
        total_bearish_score = 0
        
        for article in relevant_news:
            text = f"{article['title']} {article['summary']}"
            sentiment = self.analyze_sentiment(text)
            
            if sentiment['sentiment'] == 'bullish':
                bullish_count += 1
                total_bullish_score += sentiment['score']
            elif sentiment['sentiment'] == 'bearish':
                bearish_count += 1
                total_bearish_score += sentiment['score']
        
        # Determine overall signal
        if bullish_count > bearish_count and total_bullish_score > 0:
            signal = 'BULLISH'
            strength = min(total_bullish_score / len(relevant_news) * 10, 10)
            reason = f"{bullish_count} bullish articles found"
        elif bearish_count > bullish_count and total_bearish_score > 0:
            signal = 'BEARISH'
            strength = min(total_bearish_score / len(relevant_news) * 10, 10)
            reason = f"{bearish_count} bearish articles found"
        else:
            signal = 'NEUTRAL'
            strength = 0
            reason = 'Mixed or neutral sentiment'
        
        return {
            'symbol': symbol,
            'signal': signal,
            'strength': round(strength, 2),
            'reason': reason,
            'article_count': len(relevant_news),
            'bullish_count': bullish_count,
            'bearish_count': bearish_count,
            'top_headlines': [article['title'] for article in relevant_news[:3]]
        }


if __name__ == "__main__":
    monitor = NewsMonitor()
    
    # Test with each asset
    for symbol in ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']:
        print(f"\n{'='*60}")
        print(f"News analysis for {symbol}")
        print('='*60)
        
        signal = monitor.get_asset_news_signal(symbol, hours=12)
        
        print(f"Signal: {signal['signal']} (strength: {signal['strength']}/10)")
        print(f"Reason: {signal['reason']}")
        print(f"Articles analyzed: {signal['article_count']}")
        
        if signal['top_headlines']:
            print("\nTop headlines:")
            for headline in signal['top_headlines']:
                print(f"  - {headline}")
