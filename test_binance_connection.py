"""Test Binance API connection and account status"""
import os
from dotenv import load_dotenv
from binance.client import Client
from binance.exceptions import BinanceAPIException

load_dotenv()

TRADING_MODE = os.getenv("TRADING_MODE", "live")
API_KEY = os.getenv("BINANCE_TESTNET_API_KEY" if TRADING_MODE == "testnet" else "BINANCE_API_KEY")
SECRET_KEY = os.getenv("BINANCE_TESTNET_SECRET_KEY" if TRADING_MODE == "testnet" else "BINANCE_SECRET_KEY")

def test_connection():
    """Test Binance API connection"""
    try:
        if TRADING_MODE == "testnet":
            # Testnet requires specific base URL
            client = Client(
                API_KEY, 
                SECRET_KEY,
                testnet=True,
                tld='com'  # Force .com TLD for testnet
            )
            print("🧪 TESTNET MODE - Using fake money")
            print("=" * 60)
        else:
            client = Client(API_KEY, SECRET_KEY)
            print("💰 LIVE MODE - Using real money")
            print("=" * 60)
        
        # Test connection
        print("Testing Binance API connection...")
        status = client.get_system_status()
        print(f"✓ System Status: {status}")
        
        # Get account info
        print("\nFetching account information...")
        account = client.get_account()
        print(f"✓ Account Type: {account.get('accountType', 'Unknown')}")
        print(f"✓ Can Trade: {account.get('canTrade', False)}")
        print(f"✓ Can Deposit: {account.get('canDeposit', False)}")
        print(f"✓ Can Withdraw: {account.get('canWithdraw', False)}")
        
        # Get balances (only non-zero)
        print("\nAccount Balances:")
        balances = account.get('balances', [])
        for balance in balances:
            free = float(balance['free'])
            locked = float(balance['locked'])
            if free > 0 or locked > 0:
                asset = balance['asset']
                print(f"  {asset}: {free:.8f} free, {locked:.8f} locked")
        
        # Test futures account (if enabled)
        try:
            print("\nChecking Futures account...")
            futures_account = client.futures_account()
            total_balance = float(futures_account.get('totalWalletBalance', 0))
            available = float(futures_account.get('availableBalance', 0))
            print(f"✓ Futures enabled")
            print(f"  Total Balance: {total_balance:.2f} USDT")
            print(f"  Available: {available:.2f} USDT")
        except BinanceAPIException as e:
            print(f"✗ Futures not enabled or accessible: {e}")
        
        print("\n✓ Connection test successful!")
        return True
        
    except BinanceAPIException as e:
        print(f"\n✗ Binance API Error: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Connection Error: {e}")
        return False

if __name__ == "__main__":
    test_connection()
