"""
Helper script to check and setup Binance Futures Testnet account
"""
import os
from dotenv import load_dotenv
from binance.client import Client

load_dotenv()

API_KEY = os.getenv("BINANCE_TESTNET_API_KEY")
SECRET_KEY = os.getenv("BINANCE_TESTNET_SECRET_KEY")

def setup_testnet():
    try:
        print("🧪 Binance Futures Testnet Setup")
        print("=" * 70)
        
        client = Client(API_KEY, SECRET_KEY, testnet=True)
        client.FUTURES_URL = "https://testnet.binancefuture.com/fapi"
        client.FUTURES_DATA_URL = "https://testnet.binancefuture.com/fapi"
        
        # Check Futures account
        print("\n1. Checking Futures Account...")
        futures_account = client.futures_account()
        futures_balance = float(futures_account.get('totalWalletBalance', 0))
        print(f"   Futures Balance: {futures_balance} USDT")
        
        if futures_balance > 0:
            print("   ✓ You have funds! Ready to trade.")
            return True
        
        print("\n⚠️  No funds in Futures account!")
        print("\nTo get test funds:")
        print("=" * 70)
        print("\nOption 1: Web Interface")
        print("  1. Go to: https://testnet.binancefuture.com/")
        print("  2. Look for your balance at top right")
        print("  3. There may be a 'Get Test Funds' button or similar")
        print("  4. Request 10,000 test USDT")
        print("\nOption 2: Contact Support")
        print("  If no funds button exists, Binance testnet sometimes")
        print("  requires manual funding. Check their documentation or")
        print("  Discord/Telegram support channels.")
        print("\nOption 3: Alternative Testing")
        print("  We can also run the strategy in 'paper trading' mode")
        print("  (simulated locally without any exchange connection)")
        print("=" * 70)
        
        return False
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nMake sure:")
        print("  - API keys are from https://testnet.binancefuture.com/")
        print("  - Keys were just generated (they expire)")
        return False

if __name__ == "__main__":
    has_funds = setup_testnet()
    
    if has_funds:
        print("\n✅ Ready to start testing!")
        print("\nNext steps:")
        print("  python main_trading_loop.py --test")
    else:
        print("\n📌 Add funds first, then run:")
        print("  python setup_testnet.py")
        print("  python main_trading_loop.py --test")
