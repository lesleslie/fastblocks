import typing as t
from contextlib import suppress
from datetime import timedelta
from time import time

from acb.adapters.sql import Sql
from acb.config import Config
from acb.debug import debug
from acb.depends import depends
from sqlmodel import select  # type: ignore

from firebase_admin import auth
from firebase_admin import initialize_app
from google.auth.transport import requests as google_requests
from pydantic import SecretStr
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from ._base import AuthBase
from ._base import AuthBaseUser
from ._base import current_user
from ._model import UserModel


firebase_request_adapter: google_requests.Request = google_requests.Request()
firebase_app: t.Any = None


class CurrentUser(AuthBaseUser):
    user_data: t.Any = {}

    def has_role(self, role: str) -> str:
        return self.user_data.custom_claims.get(role)

    def set_role(self, role: str) -> str | bool | None:
        return auth.set_custom_user_claims(self.user_data["uid"], {role: True})

    @property
    def identity(self) -> str | int | bool:
        return self.user_data.get("uid", False)

    @property
    def display_name(self) -> str:
        return self.user_data.get("name")

    @property
    def email(self):
        return self.user_data.get("email")

    @depends.inject
    def is_authenticated(
        self, request: Request | None, config: Config = depends()
    ) -> bool | int | str:
        if request:
            with suppress(
                auth.ExpiredIdTokenError,
                auth.RevokedIdTokenError,
                auth.InvalidIdTokenError,
            ):
                session_cookie = request.session.get(config.auth.token_id)
                if session_cookie:
                    self.user_data = auth.verify_session_cookie(
                        session_cookie, check_revoked=True
                    )
        return self.identity


current_user.set(CurrentUser())


class Auth(AuthBase):
    config: Config = depends()
    sql: Sql = depends()  # type: ignore

    def __init__(
        self,
        secret_key: t.Optional[SecretStr] = None,
        user_model: t.Optional[UserModel] = None,
    ) -> None:
        self.secret_key = secret_key or self.config.app.secret_key
        self.middlewares = [
            Middleware(
                SessionMiddleware,
                secret_key=secret_key.get_secret_value(),
                session_cookie=self.config.auth.session_cookie,
                https_only=True if self.config.app.is_deployed else False,
            )
        ]
        self.name = "firebase"
        self.user_model = user_model or UserModel

    async def init(self) -> None:
        global firebase_app
        firebase_options: dict[str, str] = dict(projectId=self.config.app.project)
        firebase_app = initialize_app(options=firebase_options.copy())

    async def login(self, request: Request) -> bool:
        id_token = request.cookies.get(self.config.auth.token_id)
        if id_token:
            if current_user.get().is_authenticated(request):
                return True
            user_data = None
            with suppress(
                auth.ExpiredIdTokenError,
                auth.RevokedIdTokenError,
                auth.InvalidIdTokenError,
            ):
                user_data = auth.verify_id_token(id_token, check_revoked=True)

            if user_data:
                async with self.sql.session() as session:
                    user_query = select(self.user_model).where(  # type: ignore
                        self.user_model.email == user_data["email"]  # type: ignore
                        and self.user_model.is_active  # type: ignore
                    )
                    result = await session.execute(user_query)
                    enabled_user = result.one_or_none()
                if enabled_user and (time() - user_data["auth_time"] < 5 * 6):
                    enabled_user = enabled_user[0]
                    # short_url = await minify.url(user_data["picture"])
                    auth.set_custom_user_claims(
                        user_data["uid"], {enabled_user.role: True}
                    )
                    enabled_user.name = (user_data["name"],)
                    enabled_user.uid = (user_data["uid"],)
                    enabled_user.image = (user_data["picture"],)
                    await enabled_user.save()
                    expires_in = timedelta(days=14)
                    session_cookie = auth.create_session_cookie(
                        id_token, expires_in=expires_in
                    )
                    self.config.auth.session_cookie = session_cookie
                    request.session.update({self.config.auth.token_id: session_cookie})
                    debug(request.session.keys())
                    return True
                else:
                    auth.revoke_refresh_tokens(user_data["uid"])
        request.session.clear()
        current_user.get().user_data = {}
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        with suppress(
            auth.ExpiredIdTokenError, auth.RevokedIdTokenError, auth.InvalidIdTokenError
        ):
            id_token = request.cookies.get(self.config.auth.token_id)
            user_data = auth.verify_id_token(id_token, check_revoked=True)
            auth.revoke_refresh_tokens(user_data["uid"])
        current_user.get().user_data = {}
        return True

    @staticmethod
    async def authenticate(request: Request) -> bool:
        return await current_user.get().is_authenticated(request)


depends.set(Auth)
