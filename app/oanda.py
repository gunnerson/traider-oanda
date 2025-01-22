import json
import time
from typing import Any

from requests import ConnectionError, ReadTimeout, Session

from . import enums


class Api:
    """Defines a base api class."""

    def __init__(
        self,
        api_account: str,
        api_token: str,
        base_url: str,
        timeout: int = 3,
    ):
        self.api_account = api_account
        self.base_url = base_url
        self.timeout = timeout

        self.session = Session()
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_token}",
                "Accept-Datetime-Format": "UNIX",
            }
        )

    def get_query(self, params: dict) -> str:
        """Returns a query string of all given parameters."""
        query = "?"
        for key, value in params.items():
            query += f"{key}={value}&"
        return query[:-1]

    def send_request(
        self,
        method: enums.Method,
        endpoint: str,
        params: dict = {},
    ) -> Any:
        """
        Sends a request with the given method to the given endpoint.
        """

        url = self.base_url + endpoint
        if method == enums.Method.GET:
            url += self.get_query(params)

        try:
            if method == enums.Method.GET:
                response = self.session.request(
                    method.value,
                    url,
                    timeout=self.timeout,
                )
            else:
                response = self.session.request(
                    method.value,
                    url,
                    data=json.dumps(params),
                    timeout=self.timeout,
                )
        except (ConnectionError, ReadTimeout):
            print(
                f"[-] OANDA-API endpoint '{endpoint}' returned with error 'ConnectionError'."
            )
            return None

        if response.status_code in [400, 401, 403, 404, 405]:
            res = json.loads(response.text)
            print(
                f"[-] OANDA-API endpoint '{endpoint}' returned with error code '{response.status_code}'({response.reason}): {res["errorMessage"]}"
            )
            return None

        if response.status_code in [200, 201]:
            return response.json()

        print(f"[-] OANDA-API endpoint '{endpoint}' failed to fetch data...")
        return None


class Endpoint:
    """
    Class for handling all API endpoints
    https://developer.oanda.com/rest-live-v20/development-guide/
    """

    def __init__(self, api_account: str, api_token: str, base_url: str):
        self.api = Api(api_account, api_token, base_url)

    def summary(self) -> dict:
        headers = {
            "Accept-Datetime-Format": "UNIX",
        }
        return self.api.send_request(
            enums.Method.GET, f"accounts/{self.api.api_account}/summary", headers
        )

    def instruments(self) -> dict:
        return self.api.send_request(
            enums.Method.GET, f"accounts/{self.api.api_account}/instruments"
        )

    def candles(
        self,
        pair: str,
        interval: str,
        count: int = 500,
    ) -> dict:
        params = {
            "price": "M",
            "granularity": interval,
            "count": count,
            "smooth": True,
        }
        return self.api.send_request(
            enums.Method.GET, f"instruments/{pair}/candles", params
        )

    def pricing(self, pair: str) -> dict:
        params = {
            "instruments": pair,
            "includeHomeConversions": True,
        }
        return self.api.send_request(
            enums.Method.GET, f"accounts/{self.api.api_account}/pricing", params
        )

    def place_order(
        self,
        order_type: enums.OrderType,
        pair: str | None = None,
        vol: int | float | None = None,
        price: float | None = None,
        trade_id: str | None = None,
        distance: int | float | None = None,
    ) -> dict:
        if order_type == enums.OrderType.MARKET:
            params = {
                "order": {
                    "type": order_type,
                    "instrument": pair,
                    "units": str(vol),
                    "priceBound": str(price),
                }
            }
        elif order_type == enums.OrderType.TRAILING_STOP_LOSS:
            params = {
                "order": {
                    "type": order_type,
                    "tradeID": trade_id,
                    "distance": str(distance),
                }
            }
        return self.api.send_request(
            enums.Method.POST,
            f"accounts/{self.api.api_account}/orders",
            params,  # type: ignore
        )

    def get_order(
        self,
        order_id: str,
    ) -> dict:
        return self.api.send_request(
            enums.Method.GET,
            f"accounts/{self.api.api_account}/orders/{order_id}",
        )

    def get_trade(
        self,
        trade_id: str,
    ) -> dict:
        return self.api.send_request(
            enums.Method.GET,
            f"accounts/{self.api.api_account}/trades/{trade_id}",
        )

    def cancel_order(self, order_id: str) -> dict:
        return self.api.send_request(
            enums.Method.PUT,
            f"accounts/{self.api.api_account}/orders/{order_id}/cancel",
        )

    def close_position(self, pair: str) -> dict:
        params = {
            "longUnits": "ALL",
            "shortUnits": "ALL",
        }
        return self.api.send_request(
            enums.Method.PUT,
            f"accounts/{self.api.api_account}/positions/{pair}/close",
            params,
        )
