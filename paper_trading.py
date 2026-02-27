"""
Paper Trading Simulator - Test strategy without exchange connection
Simulates trades locally using real market data from yfinance
"""
import os
import json
from datetime import datetime
from typing import Dict, List
from loguru import logger
import yfinance as yf

class PaperTradingSimulator:
    """Simulate trading without real exchange"""
    
    def __init__(self, starting_balance: float = 100.0):
        self.balance = starting_balance
        self.starting_balance = starting_balance
        self.positions: Dict = {}
        self.trade_history: List = []
        self.daily_trades = 0
        self.last_reset_date = datetime.now().date()
        
        logger.add(
            "paper_trading_{time}.log",
            rotation="1 day",
            level="INFO"
        )
        
        logger.info("=" * 60)
        logger.info("📝 PAPER TRADING SIMULATOR")
        logger.info(f"Starting Balance: ${starting_balance} USDT")
        logger.info("=" * 60)
    
    def get_current_price(self, symbol: str) -> float:
        """Get real current price from yfinance"""
        # Convert BTCUSDT -> BTC-USD
        if symbol.endswith('USDT'):
            symbol_yf = symbol.replace('USDT', '-USD')
        else:
            symbol_yf = f"{symbol}-USD"
        
        try:
            ticker = yf.Ticker(symbol_yf)
            data = ticker.history(period='1d', interval='1m')
            if not data.empty:
                return float(data['Close'].iloc[-1])
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
        
        return None
    
    def _reset_daily_trades_if_needed(self):
        """Reset daily trade counter at midnight"""
        current_date = datetime.now().date()
        if current_date > self.last_reset_date:
            logger.info(f"🔄 Daily reset: {self.daily_trades} trades yesterday, resetting counter")
            self.daily_trades = 0
            self.last_reset_date = current_date
    
    def open_position(
        self,
        symbol: str,
        side: str,
        position_size_pct: float,
        leverage: int,
        stop_loss_pct: float,
        take_profit_pct: float,
        reason: str = ""
    ) -> bool:
        """Simulate opening a position"""
        
        # Reset daily counter if new day
        self._reset_daily_trades_if_needed()
        
        if symbol in self.positions:
            logger.warning(f"Already have position in {symbol}")
            return False
        
        price = self.get_current_price(symbol)
        if not price:
            logger.error(f"Could not get price for {symbol}")
            return False
        
        # Calculate position
        position_usdt = self.balance * (position_size_pct / 100)
        quantity = position_usdt / price
        
        # Calculate SL/TP
        if side == 'LONG':
            stop_loss = price * (1 - stop_loss_pct / 100)
            take_profit = price * (1 + take_profit_pct / 100)
        else:  # SHORT
            stop_loss = price * (1 + stop_loss_pct / 100)
            take_profit = price * (1 - take_profit_pct / 100)
        
        self.positions[symbol] = {
            'side': side,
            'entry_price': price,
            'quantity': quantity,
            'position_size_usdt': position_usdt,
            'leverage': leverage,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'opened_at': datetime.now().isoformat(),
            'reason': reason
        }
        
        self.daily_trades += 1
        
        logger.info(f"✓ OPENED {side} position: {symbol}")
        logger.info(f"  Entry: ${price:.4f}")
        logger.info(f"  Size: ${position_usdt:.2f} ({leverage}x leverage)")
        logger.info(f"  Stop Loss: ${stop_loss:.4f}")
        logger.info(f"  Take Profit: ${take_profit:.4f}")
        if reason:
            logger.info(f"  Reason: {reason}")
        
        return True
    
    def close_position(self, symbol: str, reason: str = "") -> Dict:
        """Simulate closing a position"""
        
        if symbol not in self.positions:
            logger.warning(f"No position in {symbol}")
            return None
        
        pos = self.positions[symbol]
        current_price = self.get_current_price(symbol)
        
        if not current_price:
            logger.error(f"Could not get price for {symbol}")
            return None
        
        # Calculate PnL
        entry = pos['entry_price']
        leverage = pos['leverage']
        position_size = pos['position_size_usdt']
        
        if pos['side'] == 'LONG':
            price_change_pct = ((current_price - entry) / entry) * 100
        else:  # SHORT
            price_change_pct = ((entry - current_price) / entry) * 100
        
        # Apply leverage
        pnl_pct = price_change_pct * leverage
        pnl_usdt = position_size * (pnl_pct / 100)
        
        # Update balance
        self.balance += pnl_usdt
        
        # Record trade
        trade_record = {
            'symbol': symbol,
            'side': pos['side'],
            'entry_price': entry,
            'exit_price': current_price,
            'pnl_pct': round(pnl_pct, 2),
            'pnl_usdt': round(pnl_usdt, 2),
            'closed_at': datetime.now().isoformat(),
            'reason': reason
        }
        
        self.trade_history.append(trade_record)
        
        logger.info(f"✓ CLOSED {pos['side']} position: {symbol}")
        logger.info(f"  Entry: ${entry:.4f}")
        logger.info(f"  Exit: ${current_price:.4f}")
        logger.info(f"  PnL: {pnl_pct:+.2f}% (${pnl_usdt:+.2f} USDT)")
        logger.info(f"  New Balance: ${self.balance:.2f} USDT")
        if reason:
            logger.info(f"  Reason: {reason}")
        
        # Remove position
        del self.positions[symbol]
        
        return trade_record
    
    def check_stop_loss_take_profit(self):
        """Check all positions for SL/TP"""
        # Reset daily counter if new day
        self._reset_daily_trades_if_needed()
        
        for symbol in list(self.positions.keys()):
            pos = self.positions[symbol]
            current_price = self.get_current_price(symbol)
            
            if not current_price:
                continue
            
            # Check stop loss
            if pos['side'] == 'LONG' and current_price <= pos['stop_loss']:
                logger.warning(f"⚠️  Stop Loss hit for {symbol}")
                self.close_position(symbol, reason="Stop Loss")
            elif pos['side'] == 'SHORT' and current_price >= pos['stop_loss']:
                logger.warning(f"⚠️  Stop Loss hit for {symbol}")
                self.close_position(symbol, reason="Stop Loss")
            
            # Check take profit
            elif pos['side'] == 'LONG' and current_price >= pos['take_profit']:
                logger.info(f"🎯 Take Profit hit for {symbol}")
                self.close_position(symbol, reason="Take Profit")
            elif pos['side'] == 'SHORT' and current_price <= pos['take_profit']:
                logger.info(f"🎯 Take Profit hit for {symbol}")
                self.close_position(symbol, reason="Take Profit")
    
    def get_status(self) -> Dict:
        """Get current status"""
        total_pnl = self.balance - self.starting_balance
        pnl_pct = (total_pnl / self.starting_balance) * 100
        
        wins = [t for t in self.trade_history if t['pnl_usdt'] > 0]
        losses = [t for t in self.trade_history if t['pnl_usdt'] < 0]
        win_rate = (len(wins) / len(self.trade_history) * 100) if self.trade_history else 0
        
        return {
            'balance': round(self.balance, 2),
            'starting_balance': self.starting_balance,
            'total_pnl': round(total_pnl, 2),
            'pnl_pct': round(pnl_pct, 2),
            'total_trades': len(self.trade_history),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': round(win_rate, 2),
            'open_positions': len(self.positions),
            'daily_trades': self.daily_trades
        }
    
    def print_summary(self):
        """Print trading summary"""
        status = self.get_status()
        
        print("\n" + "=" * 60)
        print("📝 PAPER TRADING SUMMARY")
        print("=" * 60)
        print(f"Starting Balance: ${status['starting_balance']:.2f} USDT")
        print(f"Current Balance:  ${status['balance']:.2f} USDT")
        print(f"Total PnL:        ${status['total_pnl']:+.2f} USDT ({status['pnl_pct']:+.2f}%)")
        print(f"\nTrades:")
        print(f"  Total: {status['total_trades']}")
        print(f"  Wins:  {status['wins']} ({status['win_rate']:.1f}%)")
        print(f"  Losses: {status['losses']}")
        print(f"\nOpen Positions: {status['open_positions']}")
        print(f"Daily Trades: {status['daily_trades']}")
        print("=" * 60)
        
        if self.trade_history:
            print("\n📊 Trade History:")
            for i, trade in enumerate(self.trade_history[-10:], 1):  # Last 10 trades
                print(f"\n{i}. {trade['symbol']} {trade['side']}")
                print(f"   Entry: ${trade['entry_price']:.4f}")
                print(f"   Exit:  ${trade['exit_price']:.4f}")
                print(f"   PnL:   {trade['pnl_pct']:+.2f}% (${trade['pnl_usdt']:+.2f})")
                print(f"   Reason: {trade['reason']}")


if __name__ == "__main__":
    # Test the simulator
    sim = PaperTradingSimulator(starting_balance=100)
    
    # Test opening a position
    sim.open_position(
        symbol='BTCUSDT',
        side='LONG',
        position_size_pct=30,
        leverage=10,
        stop_loss_pct=5,
        take_profit_pct=10,
        reason="Test trade"
    )
    
    # Check SL/TP
    sim.check_stop_loss_take_profit()
    
    # Print status
    sim.print_summary()
