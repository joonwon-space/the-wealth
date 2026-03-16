from typing import Optional

from pydantic import BaseModel


class KisCredentialsRequest(BaseModel):
    app_key: str
    app_secret: str
    account_no: Optional[str] = None
    acnt_prdt_cd: str = "01"
