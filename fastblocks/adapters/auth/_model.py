import typing as t

from acb.adapters.sql import SqlModel
from sqlmodel import Field  # type: ignore

from pydantic import EmailStr
from sqlalchemy_utils.types import URLType
from sqlalchemy_utils.types import EmailType


class UserModel(SqlModel):
    uid: t.Optional[str] = Field(unique=True)
    name: str
    gmail: EmailStr = Field(unique=True, nullable=False)
    email: t.Optional[EmailType] = Field(unique=True, nullable=False)
    image: t.Optional[URLType]
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
