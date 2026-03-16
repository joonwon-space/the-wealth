from pydantic import BaseModel


class KisCredentialsRequest(BaseModel):
    app_key: str
    app_secret: str
