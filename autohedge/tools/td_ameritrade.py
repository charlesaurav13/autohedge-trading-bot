import os
import json
from typing import Dict, Any, Optional
from loguru import logger
from requests import Response, Session
from requests.exceptions import HTTPError, RequestException
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class TDAmeritradeClient:
    """
    A robust client for interacting with TD Ameritrade's API.
    """

    BASE_URL = "https://api.tdameritrade.com/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        access_token: Optional[str] = None,
        accound_id: str = None,
    ):
        """
        Initialize the TD Ameritrade client.

        Args:
            api_key: Your TD Ameritrade API Key (optional, defaults to env variable).
            access_token: OAuth 2.0 Access Token (optional, defaults to env variable).
        """
        self.api_key = api_key or os.getenv("TD_API_KEY")
        self.access_token = access_token or os.getenv(
            "TD_ACCESS_TOKEN"
        )
        self.accound_id = accound_id

        if not self.api_key or not self.access_token:
            logger.error("Missing TD Ameritrade API credentials.")
            raise EnvironmentError(
                "Ensure TD_API_KEY and TD_ACCESS_TOKEN are set."
            )

        self.session = Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }
        )

        logger.success(
            "TD Ameritrade Client initialized successfully."
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def _make_request(
        self, method: str, endpoint: str, **kwargs
    ) -> Response:
        """
        Perform an HTTP request with retries.

        Args:
            method: HTTP method (GET, POST, etc.).
            endpoint: API endpoint.
            kwargs: Additional request arguments.

        Returns:
            Response object.
        """
        url = f"{self.BASE_URL}{endpoint}"
        try:
            logger.info(
                f"Making {method} request to {url} with params: {kwargs.get('params')}"
            )
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except HTTPError as http_err:
            logger.error(
                f"HTTP error occurred: {http_err} - {response.text}"
            )
            raise
        except RequestException as req_err:
            logger.error(f"Request error occurred: {req_err}")
            raise

    def place_order(
        self, order_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Place an order (buy/sell) on TD Ameritrade.

        Args:
            account_id: The account ID to execute the order.
            order_payload: The order details (JSON payload).

        Returns:
            Response JSON from the API.
        """
        endpoint = f"/accounts/{self.accound_id}/orders"
        response = self._make_request(
            "POST", endpoint, json=order_payload
        )
        logger.success("Order placed successfully.")
        return response.json()

    def get_account_info(
        self,
    ) -> Dict[str, Any]:
        """
        Fetch account information, such as balances and positions.

        Args:
            account_id: The account ID.

        Returns:
            Response JSON with account details.
        """
        endpoint = f"/accounts/{self.account_id}"
        params = {"fields": "positions"}
        response = self._make_request("GET", endpoint, params=params)
        logger.success("Account information fetched successfully.")
        return response.json()

    def build_order(
        self,
        symbol: str,
        quantity: int,
        action: str,
        price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Create an order payload.

        Args:
            symbol: The stock ticker symbol (e.g., 'AAPL').
            quantity: The number of shares.
            action: 'BUY' or 'SELL'.
            price: Limit price (optional, for limit orders).

        Returns:
            The JSON payload for the order.
        """
        order_payload = {
            "orderType": "LIMIT" if price else "MARKET",
            "session": "NORMAL",
            "duration": "DAY",
            "orderStrategyType": "SINGLE",
            "orderLegCollection": [
                {
                    "instruction": (
                        "BUY" if action.upper() == "BUY" else "SELL"
                    ),
                    "quantity": quantity,
                    "instrument": {
                        "symbol": symbol,
                        "assetType": "EQUITY",
                    },
                }
            ],
        }
        if price:
            order_payload["price"] = price

        logger.debug(
            f"Order payload built: {json.dumps(order_payload, indent=2)}"
        )
        return order_payload


# Example Usage
if __name__ == "__main__":
    logger.add(
        "td_ameritrade_client.log",
        rotation="1 MB",
        retention="10 days",
        level="DEBUG",
    )

    try:
        # Replace with valid account ID
        account_id = "your_account_id_here"

        client = TDAmeritradeClient()

        # Build and place a buy order
        buy_order = client.build_order(
            symbol="AAPL", quantity=10, action="BUY", price=150.00
        )
        response = client.place_order(order_payload=buy_order)
        logger.info(
            f"Order Response: {json.dumps(response, indent=2)}"
        )

        # Fetch account information
        account_info = client.get_account_info()
        logger.info(
            f"Account Info: {json.dumps(account_info, indent=2)}"
        )

    except Exception as e:
        logger.error(f"An error occurred: {e}")
