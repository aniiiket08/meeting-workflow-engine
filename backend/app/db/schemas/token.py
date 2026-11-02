from pydantic import BaseModel, ConfigDict

from app.db.models.user import UserRole


class TokenUser(BaseModel):
    id: int
    name: str
    username: str
    email: str
    role: UserRole

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: TokenUser | None = None


class TokenPayload(BaseModel):
    sub: str | None = None
