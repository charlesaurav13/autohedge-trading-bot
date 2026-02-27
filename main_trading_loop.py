"""
Main Trading Loop - Orchestrates analysis, news, and execution
"""
import os
import sys
import time
import json
from datetime import datetime
from typing import Dict, List
from loguru import logger
from dotenv import load_dotenv

# Import our modules
from trading_bot import TradingBot
from news_monitor import NewsMonitor
from paper_trading import PaperTradingSimulator
sys.path.insert(0, os.path.dirname(__file__))
from autohedge.main import AutoHedge, fetch_crypto_data, format_crypto_data

load_dotenv()

# Configuration
TRADING_MODE = os.getenv("TRADING_MODE", "paper")
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", 15))
NEWS_CHECK_HOURS = int(os.getenv("NEWS_CHECK_HOURS", 6))
MIN_SIGNAL_STRENGTH = float(os.getenv("MIN_SIGNAL_STRENGTH", 5.0))
TRADING_PAIRS = os.getenv("TRADING_PAIRS", "BTC/USDT,ETH/USDT,SOL/USDT").split(",")
BINANCE_SYMBOLS = [pair.replace("/", "") for pair in TRADING_PAIRS]

# Trading parameters
CAPITAL_USDT = float(os.getenv("CAPITAL_USDT", 100))
POSITION_SIZE_PCT = float(os.getenv("POSITION_SIZE_PCT", 30))
LEVERAGE = int(os.getenv("LEVERAGE", 10))
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", 5))
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", 10))
MAX_TRADES_PER_DAY = int(os.getenv("MAX_TRADES_PER_DAY", 3))

# Map trading pairs to analysis symbols
SYMBOL_MAP = {
    'BTCUSDT': 'BTC',
    'ETHUSDT': 'ETH',
    'SOLUSDT': 'SOL'
}


class TradingOrchestrator:
    """Main orchestrator for trading system"""
    
    def __init__(self):
        logger.info("=" * 70)
        logger.info("INITIALIZING CRYPTO TRADING SYSTEM")
        logger.info("=" * 70)
        
        # Initialize bot based on trading mode
        if TRADING_MODE == "paper":
            logger.info("📝 PAPER TRADING MODE - Simulated execution with real prices")
            self.bot = PaperTradingSimulator(starting_balance=CAPITAL_USDT)
            self.is_paper_trading = True
        else:
            logger.info(f"Mode: {TRADING_MODE}")
            self.bot = TradingBot()
            self.is_paper_trading = False
        
        self.news_monitor = NewsMonitor()
        self.autohedge = AutoHedge(
            assets=list(SYMBOL_MAP.values()),
            output_dir="analysis_outputs"
        )
        
        self.last_analysis_time = {}
        self.analysis_cache = {}
        
        logger.info("✓ All systems initialized")
        logger.info(f"Check interval: {CHECK_INTERVAL_MINUTES} minutes")
        logger.info(f"Trading pairs: {', '.join(TRADING_PAIRS)}")
        logger.info("=" * 70)
    
    def run_autohedge_analysis(self, symbol: str) -> Dict:
        """Run AutoHedge analysis for a symbol"""
        asset = SYMBOL_MAP.get(symbol, symbol.replace('USDT', ''))
        
        logger.info(f"Running AutoHedge analysis for {asset}...")
        
        try:
            # Fetch market data
            market_data = fetch_crypto_data(asset)
            formatted_data = format_crypto_data(market_data)
            
            # Run analysis
            task = f"Analyze {asset} for potential trading opportunities. Consider technical indicators, market sentiment, and risk factors."
            analysis = self.autohedge.run(task=task)
            
            # Parse the analysis to extract decision
            analysis_str = str(analysis).lower()
            
            # Look for GO/NO-GO decision
            if 'go' in analysis_str and 'no-go' not in analysis_str:
                decision = 'GO'
            elif 'no-go' in analysis_str or 'no go' in analysis_str:
                decision = 'NO-GO'
            else:
                decision = 'UNCERTAIN'
            
            # Extract direction (long/short bias)
            if 'long' in analysis_str or 'bullish' in analysis_str or 'buy' in analysis_str:
                direction = 'LONG'
            elif 'short' in analysis_str or 'bearish' in analysis_str or 'sell' in analysis_str:
                direction = 'SHORT'
            else:
                direction = 'NEUTRAL'
            
            # Extract confidence (look for probability/confidence scores)
            confidence = 5.0  # default medium confidence
            
            # Look for percentage confidence
            import re
            percentages = re.findall(r'(\d+)%?\s*(?:probability|confidence|chance)', analysis_str)
            if percentages:
                confidence = float(percentages[0]) / 10.0  # Convert to 0-10 scale
            
            result = {
                'asset': asset,
                'symbol': symbol,
                'decision': decision,
                'direction': direction,
                'confidence': confidence,
                'analysis': analysis_str[:500],  # First 500 chars
                'market_data': market_data,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Analysis complete for {asset}: {decision} / {direction} (confidence: {confidence}/10)")
            return result
            
        except Exception as e:
            logger.error(f"Error running AutoHedge analysis for {asset}: {e}")
            return {
                'asset': asset,
                'symbol': symbol,
                'decision': 'ERROR',
                'error': str(e)
            }
    
    def combine_signals(self, symbol: str) -> Dict:
        """Combine AutoHedge analysis and news signals"""
        logger.info(f"\n{'='*60}")
        logger.info(f"ANALYZING {symbol}")
        logger.info('='*60)
        
        # Get news signal
        news_signal = self.news_monitor.get_asset_news_signal(symbol, hours=NEWS_CHECK_HOURS)
        logger.info(f"News: {news_signal['signal']} (strength: {news_signal['strength']}/10)")
        logger.info(f"  {news_signal['reason']}")
        
        # Get AutoHedge analysis
        analysis = self.run_autohedge_analysis(symbol)
        logger.info(f"Analysis: {analysis['decision']} / {analysis['direction']} (confidence: {analysis['confidence']}/10)")
        
        # Combine signals
        combined_score = 0
        trade_direction = None
        reasons = []
        
        # News contribution
        if news_signal['signal'] == 'BULLISH':
            combined_score += news_signal['strength']
            if not trade_direction:
                trade_direction = 'LONG'
            reasons.append(f"Bullish news ({news_signal['strength']}/10)")
        elif news_signal['signal'] == 'BEARISH':
            combined_score += news_signal['strength']
            if not trade_direction:
                trade_direction = 'SHORT'
            reasons.append(f"Bearish news ({news_signal['strength']}/10)")
        
        # AutoHedge contribution
        if analysis['decision'] == 'GO':
            combined_score += analysis['confidence']
            if analysis['direction'] != 'NEUTRAL':
                if trade_direction and trade_direction != analysis['direction']:
                    # Conflicting signals - reduce score
                    combined_score *= 0.5
                    reasons.append(f"⚠️  Conflicting signals: News={news_signal['signal']}, Analysis={analysis['direction']}")
                else:
                    trade_direction = analysis['direction']
                    reasons.append(f"AutoHedge {analysis['direction']} ({analysis['confidence']}/10)")
        
        # Final decision
        # In paper trading: ignore Director veto (take risks to test system)
        # In live trading: respect Director veto (safety first)
        if self.is_paper_trading:
            should_trade = (
                combined_score >= MIN_SIGNAL_STRENGTH and
                trade_direction is not None
            )
            if analysis['decision'] == 'NO-GO':
                reasons.append(f"⚠️ Director said NO-GO but overriding for paper trading test")
        else:
            should_trade = (
                combined_score >= MIN_SIGNAL_STRENGTH and
                trade_direction is not None and
                analysis['decision'] != 'NO-GO'
            )
        
        result = {
            'symbol': symbol,
            'should_trade': should_trade,
            'direction': trade_direction,
            'combined_score': round(combined_score, 2),
            'reasons': reasons,
            'news': news_signal,
            'analysis': analysis
        }
        
        logger.info(f"\n{'─'*60}")
        logger.info(f"COMBINED SIGNAL: {result['direction']} (score: {result['combined_score']}/20)")
        logger.info(f"Should trade: {result['should_trade']}")
        for reason in reasons:
            logger.info(f"  • {reason}")
        logger.info('='*60)
        
        return result
    
    def check_and_trade(self):
        """Main trading logic - analyze all cryptos and trade the BEST one"""
        logger.info("\n" + "="*70)
        logger.info(f"TRADING CHECK - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*70)
        
        # Check and manage existing positions first
        if self.is_paper_trading:
            self.bot.check_stop_loss_take_profit()
        else:
            self.bot.check_stop_loss_take_profit()
        
        # Print current status
        if self.is_paper_trading:
            status = self.bot.get_status()
            logger.info(f"Balance: ${status['balance']:.2f} USDT (PnL: {status['pnl_pct']:+.2f}%)")
            logger.info(f"Daily Trades: {status['daily_trades']}/{MAX_TRADES_PER_DAY}")
            logger.info(f"Open Positions: {len(self.bot.positions)}")
        else:
            status = self.bot.get_status()
            logger.info(f"Account Balance: ${status['account']['total_balance']:.2f} USDT")
            logger.info(f"Daily Trades: {status['daily_trades']}/{status['max_trades']}")
            logger.info(f"Open Positions: {len(status['positions'])}")
        
        # Can we open new trades?
        if self.is_paper_trading:
            can_trade = (
                self.bot.daily_trades < MAX_TRADES_PER_DAY and
                len(self.bot.positions) < len(BINANCE_SYMBOLS)
            )
        else:
            can_trade = self.bot.can_open_trade()
        
        if not can_trade:
            logger.info("Cannot open new trades (max reached or positions full)")
            return
        
        # STEP 1: Analyze ALL symbols first
        logger.info("\n" + "🔍" * 35)
        logger.info("ANALYZING ALL CRYPTOS TO FIND BEST OPPORTUNITY")
        logger.info("🔍" * 35)
        
        all_signals = []
        for symbol in BINANCE_SYMBOLS:
            # Skip if already have position
            if symbol in self.bot.positions:
                logger.info(f"Skipping {symbol} - already have position")
                continue
            
            # Get signal for this symbol
            signal = self.combine_signals(symbol)
            all_signals.append(signal)
        
        # STEP 2: Filter valid signals (should_trade = True)
        valid_signals = [s for s in all_signals if s['should_trade']]
        
        if not valid_signals:
            logger.info("\n" + "⏸️ " * 35)
            logger.info("NO VALID TRADE SIGNALS - All assets below threshold or vetoed by Director")
            logger.info("⏸️ " * 35)
            
            # Show summary
            logger.info("\nSignal Summary:")
            for signal in all_signals:
                logger.info(f"  {signal['symbol']}: {signal['combined_score']:.1f}/20 - "
                          f"{signal['direction'] or 'NEUTRAL'} - "
                          f"{'✅ Would trade' if signal['combined_score'] >= MIN_SIGNAL_STRENGTH else '❌ Below threshold'} - "
                          f"{'❌ Director veto' if signal['analysis']['decision'] == 'NO-GO' else '✅ Director approved'}")
            return
        
        # STEP 3: Pick the BEST signal (highest combined_score)
        best_signal = max(valid_signals, key=lambda x: x['combined_score'])
        
        logger.info("\n" + "⭐" * 35)
        logger.info(f"BEST OPPORTUNITY: {best_signal['symbol']}")
        logger.info(f"Score: {best_signal['combined_score']:.1f}/20 | Direction: {best_signal['direction']}")
        logger.info("⭐" * 35)
        
        # Show comparison
        if len(valid_signals) > 1:
            logger.info("\nComparison with other valid signals:")
            for signal in sorted(valid_signals, key=lambda x: x['combined_score'], reverse=True):
                indicator = "👑" if signal == best_signal else "  "
                logger.info(f"{indicator} {signal['symbol']}: {signal['combined_score']:.1f}/20 - {signal['direction']}")
        
        # STEP 4: Execute ONLY the best trade
        symbol = best_signal['symbol']
        
        if self.is_paper_trading:
            # Paper trading execution
            reason = " | ".join(best_signal['reasons'])
            success = self.bot.open_position(
                symbol=symbol,
                side=best_signal['direction'],
                position_size_pct=POSITION_SIZE_PCT,
                leverage=LEVERAGE,
                stop_loss_pct=STOP_LOSS_PCT,
                take_profit_pct=TAKE_PROFIT_PCT,
                reason=reason
            )
        else:
            # Real trading execution
            price = self.bot.get_current_price(symbol)
            if not price:
                logger.error(f"Could not get price for {symbol}")
                return
            
            position_usdt, quantity = self.bot.calculate_position_size(symbol, price)
            reason = " | ".join(best_signal['reasons'])
            success = self.bot.open_position(
                symbol=symbol,
                side=best_signal['direction'],
                price=price,
                quantity=quantity,
                reason=reason
            )
        
        if success:
            logger.info(f"\n✅ Successfully opened {best_signal['direction']} position in {symbol}")
            logger.info(f"Position size: {POSITION_SIZE_PCT}% × {LEVERAGE}x leverage = {POSITION_SIZE_PCT * LEVERAGE}% effective exposure")
        else:
            logger.error(f"\n❌ Failed to open position in {symbol}")
    
    def run(self, test_mode: bool = False):
        """Main loop"""
        logger.info("\n" + "🚀" * 35)
        logger.info("STARTING TRADING BOT")
        logger.info("🚀" * 35 + "\n")
        
        if test_mode:
            logger.warning("⚠️  RUNNING IN TEST MODE - Will run once and exit")
            self.check_and_trade()
            
            # Print summary if paper trading
            if self.is_paper_trading:
                print("\n")
                self.bot.print_summary()
            
            return
        
        try:
            iteration = 0
            while True:
                iteration += 1
                logger.info(f"\n{'='*70}")
                logger.info(f"ITERATION #{iteration}")
                logger.info(f"{'='*70}")
                
                self.check_and_trade()
                
                logger.info(f"\nNext check in {CHECK_INTERVAL_MINUTES} minutes...")
                time.sleep(CHECK_INTERVAL_MINUTES * 60)
                
        except KeyboardInterrupt:
            logger.info("\n\nShutdown signal received...")
            logger.info("Saving state...")
            if not self.is_paper_trading:
                self.bot.save_state()
            else:
                # Print final summary for paper trading
                print("\n")
                self.bot.print_summary()
            logger.info("✓ State saved. Goodbye!")
        except Exception as e:
            logger.error(f"Fatal error in main loop: {e}")
            if not self.is_paper_trading:
                self.bot.save_state()
            raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Crypto Trading Bot')
    parser.add_argument('--test', action='store_true', help='Run once in test mode')
    parser.add_argument('--status', action='store_true', help='Show bot status and exit')
    args = parser.parse_args()
    
    if args.status:
        if TRADING_MODE == "paper":
            sim = PaperTradingSimulator()
            sim.print_summary()
        else:
            bot = TradingBot()
            status = bot.get_status()
            print(json.dumps(status, indent=2))
    else:
        orchestrator = TradingOrchestrator()
        orchestrator.run(test_mode=args.test)
