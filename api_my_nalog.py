import requests
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Union, Optional

class NalogApi:
    def __init__(self, inn: Optional[str] = None, password: Optional[str] = None):
        self.api_url = "https://lknpd.nalog.ru/api/v1"
        self.device_info = {
            "appVersion": "1.0.0",
            "sourceType": "iso",
            "sourceDeviceId": self.create_device_id(),
            "metaDetails": {
                "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_2_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.192 Safari/537.36",
                "os": "ios"
            }
            
        }
        self.inn = inn
        self.token = ""
        self.token_expire_in = ""
        self.refresh_token = ""
        self.auth_promise = self.authenticate(inn, password)

    def create_device_id(self) -> str:
        import random
        return ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=32))

    def authenticate(self, inn: Optional[str], password: Optional[str]) -> None:
        self.auth_password(inn, password)

    def auth_password(self, username: str, password: str) -> None:
        body = json.dumps({
            "username": username,
            "password": password,
            "deviceInfo": self.device_info
        })
        response = self._post("/auth/lkfl", body)
        self._auth(response)



    def _auth(self, response: Dict) -> None:
        if not response.get("refreshToken"):
            raise ValueError(response.get("message", "Authorization failed"))
        print("Authorization in lknpd.nalog.ru was successful")
        self.inn = response["profile"]["inn"]
        self.token = response["token"]
        self.token_expire_in = response["tokenExpireIn"]
        self.refresh_token = response["refreshToken"]

    def _get_token(self) -> str:
        if self.token and not self.is_expired_token(self.token_expire_in):
            return self.token
        body = json.dumps({
            "deviceInfo": self.device_info,
            "refreshToken": self.refresh_token
        })
        response = self._post("/auth/token", body)
        if not response.get("token"):
            raise ValueError(response.get("message", "Failed to refresh token"))
        self.refresh_token = response.get("refreshToken", self.refresh_token)
        self.token = response["token"]
        self.token_expire_in = response["tokenExpireIn"]
        return self.token

    def is_expired_token(self, token_expire_in: str) -> bool:
        return datetime.now().timestamp() > datetime.fromisoformat(token_expire_in).timestamp()

    def _post(self, endpoint: str, body: str) -> Dict:
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "content-type": "application/json",
            "referrer": "https://lknpd.nalog.ru/",
            "referrerPolicy": "strict-origin-when-cross-origin"
        }
        response = requests.post(f"{self.api_url}{endpoint}", headers=headers, data=body)
        return response.json()

    def _post_headers(self) -> Dict[str, str]:
        return {
            "accept": "application/json, text/plain, */*",
            "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "content-type": "application/json",
            "referrer": "https://lknpd.nalog.ru/",
            "referrerPolicy": "strict-origin-when-cross-origin"
        }

    def call_method(self, method_path: str, data: Optional[Dict] = None) -> Dict:
        token = self._get_token()
        headers = {
            "authorization": f"Bearer {token}",
            **self._post_headers()
        }
        body = json.dumps(data) if data else None
        method = "POST" if body else "GET"
        response = requests.request(method, f"{self.api_url}/{method_path}", headers=headers, data=body)
        return response.json()

    def get_user_info(self) -> Dict:
        return self.call_method("user")

    def add_income(self, timezone_offset,amount,name,quantity, date: Optional[datetime] = None) -> str:
        
        current_time = (datetime.now(timezone.utc) + timedelta(hours=timezone_offset)).isoformat()


        response = self.call_method(
            "income", {
            
            "ignoreMaxTotalIncomeRestriction": False,
            "operationTime": current_time,
            "paymentType": "CASH",
            "client":{"contactPhone":"","displayName":"","inn":"","incomeType":"FROM_INDIVIDUAL"},
            "requestTime": current_time,
            "services": [{ "amount":str(amount),"name":str(name), "quantity":str(quantity)}],
            "totalAmount": str(amount)
        })

        approved_receipt_uuid = response.get("approvedReceiptUuid")
        if not approved_receipt_uuid:
            raise ValueError(response.get("message", "Failed to add income"))
        return approved_receipt_uuid

    def cancel_income(self,timezone_offset, receipt_uuid: str, comment: str) -> Dict:
        current_time = (datetime.now(timezone.utc) + timedelta(hours=timezone_offset)).isoformat()
        response = self.call_method("cancel", {
            "receiptUuid": receipt_uuid,
            "comment": comment,
            "partnerCode": None,
            "requestTime": current_time
        })
        income_info = response.get("incomeInfo")
        if not income_info:
            raise ValueError(response.get("message", "Failed to cancel income"))
        return income_info

    def get_approved_income(self, receipt_uuid: str, format: str = "json") -> Union[Dict, bytes]:
        inn = self.inn
        token = self._get_token()
        headers = {
            "authorization": f"Bearer {token}",
            **self._post_headers()
        }
        response = requests.get(f"{self.api_url}/receipt/{inn}/{receipt_uuid}/{format}",stream=True, headers=headers)
        return response.json() if format == "json" else response.content


    def get_link_income(self, receipt_uuid: str, format: str = "print") -> Union[Dict, bytes]:
        inn = self.inn
        link = f"{self.api_url}/receipt/{inn}/{receipt_uuid}/{format}"
        return link
