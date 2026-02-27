"""
Test Binance Testnet API with custom base URL
"""
import os
from dotenv import load_dotenv
from binance.client import Client

load_dotenv()

API_KEY = os.getenv("BINANCE_TESTNET_API_KEY")
SECRET_KEY = os.getenv("BINANCE_TESTNET_SECRET_KEY")

# Binance Futures Testnet base URL
TESTNET_BASE_URL = "https://testnet.binancefuture.com"

try:
    print("🧪 Testing Binance Futures Testnet Connection")
    print("=" * 60)
    
    # Create client with custom testnet base URL
    client = Client(
        API_KEY,
        SECRET_KEY,
        testnet=True
    )
    
    # Override base URLs for futures testnet
    client.FUTURES_URL = "https://testnet.binancefuture.com/fapi"
    client.FUTURES_DATA_URL = "https://testnet.binancefuture.com/fapi"
    
    print("Testing Futures account...")
    account = client.futures_account()
    
    print("✓ Connection successful!")
    print(f"\nAccount Balance: {account.get('totalWalletBalance', 0)} USDT")
    print(f"Available: {account.get('availableBalance', 0)} USDT")
    
    # Check positions
    positions = client.futures_position_information()
    open_positions = [p for p in positions if float(p['positionAmt']) != 0]
    print(f"\nOpen Positions: {len(open_positions)}")
    
    if open_positions:
        for pos in open_positions:
            print(f"  {pos['symbol']}: {pos['positionAmt']} @ {pos['entryPrice']}")
    
except Exception as e:
    print(f"✗ Connection failed: {e}")
    print("\nTroubleshooting:")
    print("1. Make sure you generated keys at: https://testnet.binancefuture.com/")
    print("2. Keys are instant - no email verification needed")
    print("3. Try generating new keys if these don't work")
