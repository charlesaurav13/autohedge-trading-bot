"""
Crypto Trading Bot - Main Trading Engine
Integrates AutoHedge analysis, news monitoring, and Binance Futures execution
"""
import os
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from dotenv import load_dotenv
from loguru import logger
from binance.client import Client
from binance.exceptions import BinanceAPIException

load_dotenv()

# Configuration
TRADING_MODE = os.getenv("TRADING_MODE", "live")
API_KEY = os.getenv("BINANCE_TESTNET_API_KEY" if TRADING_MODE == "testnet" else "BINANCE_API_KEY")
SECRET_KEY = os.getenv("BINANCE_TESTNET_SECRET_KEY" if TRADING_MODE == "testnet" else "BINANCE_SECRET_KEY")
CAPITAL_USDT = float(os.getenv("CAPITAL_USDT", 100))
POSITION_SIZE_PCT = float(os.getenv("POSITION_SIZE_PCT", 30))
LEVERAGE = int(os.getenv("LEVERAGE", 10))
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", 10))
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", 5))
MAX_TRADES_PER_DAY = int(os.getenv("MAX_TRADES_PER_DAY", 3))
TRADING_PAIRS = os.getenv("TRADING_PAIRS", "BTC/USDT,ETH/USDT,SOL/USDT").split(",")

# Convert pairs to Binance format (BTC/USDT -> BTCUSDT)
BINANCE_SYMBOLS = [pair.replace("/", "") for pair in TRADING_PAIRS]

# Logger setup
logger.add(
    "trading_bot_{time}.log",
    rotation="1 day",
    retention="30 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)


class TradingBot:
    """Main trading bot orchestrator"""
    
    def __init__(self):
        # Initialize client based on trading mode
        if TRADING_MODE == "testnet":
            self.client = Client(API_KEY, SECRET_KEY, testnet=True)
            # Override base URLs for Binance Futures Testnet
            self.client.FUTURES_URL = "https://testnet.binancefuture.com/fapi"
            self.client.FUTURES_DATA_URL = "https://testnet.binancefuture.com/fapi"
            logger.warning("🧪 RUNNING IN TESTNET MODE - Using fake money!")
        else:
            self.client = Client(API_KEY, SECRET_KEY)
            logger.info("💰 RUNNING IN LIVE MODE - Using real money!")
        
        self.positions: Dict[str, Dict] = {}
        self.daily_trades = 0
        self.last_trade_reset = datetime.now().date()
        self.state_file = "bot_state.json"
        self.load_state()
        
        logger.info("=" * 60)
        logger.info("CRYPTO TRADING BOT INITIALIZED")
        logger.info(f"Mode: {'🧪 TESTNET (FAKE MONEY)' if TRADING_MODE == 'testnet' else '💰 LIVE (REAL MONEY)'}")
        logger.info("=" * 60)
        logger.info(f"Capital: ${CAPITAL_USDT} USDT")
        logger.info(f"Position Size: {POSITION_SIZE_PCT}% (${CAPITAL_USDT * POSITION_SIZE_PCT / 100} per trade)")
        logger.info(f"Leverage: {LEVERAGE}x")
        logger.info(f"Take Profit: {TAKE_PROFIT_PCT}%")
        logger.info(f"Stop Loss: {STOP_LOSS_PCT}%")
        logger.info(f"Max Trades/Day: {MAX_TRADES_PER_DAY}")
        logger.info(f"Trading Pairs: {', '.join(TRADING_PAIRS)}")
        logger.info("=" * 60)
    
    def load_state(self):
        """Load bot state from file"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    self.positions = state.get('positions', {})
                    self.daily_trades = state.get('daily_trades', 0)
                    last_reset = state.get('last_trade_reset')
                    if last_reset:
                        self.last_trade_reset = datetime.fromisoformat(last_reset).date()
                logger.info(f"State loaded: {len(self.positions)} open positions, {self.daily_trades} trades today")
        except Exception as e:
            logger.error(f"Error loading state: {e}")
    
    def save_state(self):
        """Save bot state to file"""
        try:
            state = {
                'positions': self.positions,
                'daily_trades': self.daily_trades,
                'last_trade_reset': self.last_trade_reset.isoformat(),
                'timestamp': datetime.now().isoformat()
            }
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving state: {e}")
    
    def reset_daily_trades(self):
        """Reset daily trade counter if new day"""
        today = datetime.now().date()
        if today > self.last_trade_reset:
            logger.info(f"New day - resetting trade counter (was {self.daily_trades})")
            self.daily_trades = 0
            self.last_trade_reset = today
            self.save_state()
    
    def get_account_balance(self) -> Tuple[float, float]:
        """Get Futures account balance"""
        try:
            account = self.client.futures_account()
            total = float(account.get('totalWalletBalance', 0))
            available = float(account.get('availableBalance', 0))
            return total, available
        except Exception as e:
            logger.error(f"Error getting account balance: {e}")
            return 0.0, 0.0
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price for symbol"""
        try:
            ticker = self.client.futures_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            return None
    
    def set_leverage(self, symbol: str, leverage: int):
        """Set leverage for symbol"""
        try:
            self.client.futures_change_leverage(symbol=symbol, leverage=leverage)
            logger.info(f"Set leverage to {leverage}x for {symbol}")
        except BinanceAPIException as e:
            logger.error(f"Error setting leverage for {symbol}: {e}")
    
    def calculate_position_size(self, symbol: str, price: float) -> Tuple[float, float]:
        """
        Calculate position size in USDT and quantity
        Returns: (position_usdt, quantity)
        """
        position_usdt = CAPITAL_USDT * (POSITION_SIZE_PCT / 100)
        
        # Get symbol precision
        info = self.client.futures_exchange_info()
        symbol_info = next((s for s in info['symbols'] if s['symbol'] == symbol), None)
        
        if not symbol_info:
            logger.error(f"Symbol info not found for {symbol}")
            return 0, 0
        
        # Get quantity precision
        for filter in symbol_info['filters']:
            if filter['filterType'] == 'LOT_SIZE':
                step_size = float(filter['stepSize'])
                break
        else:
            step_size = 0.001  # default
        
        # Calculate quantity
        quantity = position_usdt / price
        
        # Round to step size
        precision = len(str(step_size).split('.')[-1].rstrip('0'))
        quantity = round(quantity, precision)
        
        return position_usdt, quantity
    
    def open_position(
        self,
        symbol: str,
        side: str,  # 'LONG' or 'SHORT'
        price: float,
        quantity: float,
        reason: str = ""
    ) -> bool:
        """
        Open a new position
        """
        try:
            # Set leverage
            self.set_leverage(symbol, LEVERAGE)
            
            # Place market order
            binance_side = 'BUY' if side == 'LONG' else 'SELL'
            order = self.client.futures_create_order(
                symbol=symbol,
                side=binance_side,
                type='MARKET',
                quantity=quantity
            )
            
            logger.info(f"✓ OPENED {side} position: {symbol}")
            logger.info(f"  Price: ${price:.4f}")
            logger.info(f"  Quantity: {quantity}")
            logger.info(f"  Notional: ${price * quantity:.2f}")
            logger.info(f"  Leverage: {LEVERAGE}x")
            if reason:
                logger.info(f"  Reason: {reason}")
            
            # Calculate SL and TP prices
            if side == 'LONG':
                stop_loss_price = price * (1 - STOP_LOSS_PCT / 100)
                take_profit_price = price * (1 + TAKE_PROFIT_PCT / 100)
            else:  # SHORT
                stop_loss_price = price * (1 + STOP_LOSS_PCT / 100)
                take_profit_price = price * (1 - TAKE_PROFIT_PCT / 100)
            
            # Store position
            self.positions[symbol] = {
                'side': side,
                'entry_price': price,
                'quantity': quantity,
                'stop_loss': stop_loss_price,
                'take_profit': take_profit_price,
                'opened_at': datetime.now().isoformat(),
                'reason': reason,
                'order_id': order['orderId']
            }
            
            self.daily_trades += 1
            self.save_state()
            
            logger.info(f"  Stop Loss: ${stop_loss_price:.4f}")
            logger.info(f"  Take Profit: ${take_profit_price:.4f}")
            
            return True
            
        except BinanceAPIException as e:
            logger.error(f"Error opening position for {symbol}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error opening position: {e}")
            return False
    
    def close_position(self, symbol: str, reason: str = "") -> bool:
        """Close an existing position"""
        if symbol not in self.positions:
            logger.warning(f"No position found for {symbol}")
            return False
        
        try:
            pos = self.positions[symbol]
            side = pos['side']
            quantity = pos['quantity']
            entry_price = pos['entry_price']
            
            # Close position (opposite side)
            binance_side = 'SELL' if side == 'LONG' else 'BUY'
            order = self.client.futures_create_order(
                symbol=symbol,
                side=binance_side,
                type='MARKET',
                quantity=quantity
            )
            
            # Get exit price
            current_price = self.get_current_price(symbol)
            if not current_price:
                current_price = entry_price  # fallback
            
            # Calculate PnL
            if side == 'LONG':
                pnl_pct = ((current_price - entry_price) / entry_price) * 100 * LEVERAGE
            else:
                pnl_pct = ((entry_price - current_price) / entry_price) * 100 * LEVERAGE
            
            pnl_usdt = (CAPITAL_USDT * POSITION_SIZE_PCT / 100) * (pnl_pct / 100)
            
            logger.info(f"✓ CLOSED {side} position: {symbol}")
            logger.info(f"  Entry: ${entry_price:.4f}")
            logger.info(f"  Exit: ${current_price:.4f}")
            logger.info(f"  PnL: {pnl_pct:+.2f}% (${pnl_usdt:+.2f} USDT)")
            if reason:
                logger.info(f"  Reason: {reason}")
            
            # Remove position
            del self.positions[symbol]
            self.save_state()
            
            return True
            
        except BinanceAPIException as e:
            logger.error(f"Error closing position for {symbol}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error closing position: {e}")
            return False
    
    def check_stop_loss_take_profit(self):
        """Check all positions for SL/TP hits"""
        for symbol in list(self.positions.keys()):
            pos = self.positions[symbol]
            current_price = self.get_current_price(symbol)
            
            if not current_price:
                continue
            
            side = pos['side']
            sl_price = pos['stop_loss']
            tp_price = pos['take_profit']
            
            # Check stop loss
            if side == 'LONG' and current_price <= sl_price:
                logger.warning(f"⚠️  Stop Loss hit for {symbol}")
                self.close_position(symbol, reason="Stop Loss triggered")
            elif side == 'SHORT' and current_price >= sl_price:
                logger.warning(f"⚠️  Stop Loss hit for {symbol}")
                self.close_position(symbol, reason="Stop Loss triggered")
            
            # Check take profit
            elif side == 'LONG' and current_price >= tp_price:
                logger.info(f"🎯 Take Profit hit for {symbol}")
                self.close_position(symbol, reason="Take Profit triggered")
            elif side == 'SHORT' and current_price <= tp_price:
                logger.info(f"🎯 Take Profit hit for {symbol}")
                self.close_position(symbol, reason="Take Profit triggered")
    
    def can_open_trade(self) -> bool:
        """Check if we can open a new trade"""
        self.reset_daily_trades()
        
        if self.daily_trades >= MAX_TRADES_PER_DAY:
            logger.warning(f"Max trades per day reached ({MAX_TRADES_PER_DAY})")
            return False
        
        if len(self.positions) >= len(BINANCE_SYMBOLS):
            logger.warning("Already have positions in all tracked symbols")
            return False
        
        return True
    
    def get_status(self) -> Dict:
        """Get current bot status"""
        total_balance, available_balance = self.get_account_balance()
        
        status = {
            'timestamp': datetime.now().isoformat(),
            'account': {
                'total_balance': total_balance,
                'available_balance': available_balance,
            },
            'daily_trades': self.daily_trades,
            'max_trades': MAX_TRADES_PER_DAY,
            'open_positions': len(self.positions),
            'positions': {}
        }
        
        for symbol, pos in self.positions.items():
            current_price = self.get_current_price(symbol)
            if current_price:
                entry = pos['entry_price']
                if pos['side'] == 'LONG':
                    pnl_pct = ((current_price - entry) / entry) * 100 * LEVERAGE
                else:
                    pnl_pct = ((entry - current_price) / entry) * 100 * LEVERAGE
                
                status['positions'][symbol] = {
                    'side': pos['side'],
                    'entry_price': entry,
                    'current_price': current_price,
                    'pnl_pct': round(pnl_pct, 2),
                    'sl': pos['stop_loss'],
                    'tp': pos['take_profit']
                }
        
        return status


if __name__ == "__main__":
    bot = TradingBot()
    
    # Print status
    status = bot.get_status()
    print(json.dumps(status, indent=2))
