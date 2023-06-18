import typing as t
from contextlib import suppress
from datetime import timedelta
from time import time

from acb.config import ac
from acb.logger import ic
from acb.actions import minify
from acb.adapters import db

from firebase_admin import auth
from firebase_admin import initialize_app
from google.auth.transport import requests as google_requests

from sqlmodel import select
from starlette.authentication import BaseUser
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request

firebase_request_adapter = google_requests.Request()
firebase_options = dict(projectId=ac.app.project)
firebase_app = initialize_app(options=dict(**firebase_options))


class CurrentUser(BaseUser):
    user_data: t.Any = {}

    def has_role(self, role):
        return self.user_data.custom_claims.get(role)

    def set_role(self, role):
        return auth.set_custom_user_claims(self.user_data["uid"], {role: True})

    @property
    def identity(self):
        return self.user_data.get("uid")

    @property
    def display_name(self):
        return self.user_data.get("name")

    @property
    def email(self):
        return self.user_data.get("email")

    def is_authenticated(self, request: Request = None) -> bool | str:
        if request:
            with suppress(
                auth.ExpiredIdTokenError,
                auth.RevokedIdTokenError,
                auth.InvalidIdTokenError,
            ):
                session_cookie = request.session.get(ac.firebase.token.id)
                if session_cookie:
                    self.user_data = auth.verify_session_cookie(
                        session_cookie, check_revoked=True
                    )
        return self.identity


current_user = CurrentUser()


class StarletteAuthenticationBackend:
    async def authenticate(self, request: Request) -> bool:
        return current_user.is_authenticated(request)


class SQLAdminAuthenticationBackend(StarletteAuthenticationBackend):
    def __init__(self, secret_key: str, user_model: t.Any) -> None:
        super().__init__(secret_key)
        self.middlewares = [
            Middleware(
                SessionMiddleware,
                secret_key=secret_key,
                session_cookie=ac.firebase.token.session,
                https_only=True if ac.app.is_deployed else False,
            )
        ]
        self.name = "firebase"
        self.user_model = user_model
        # self.base_logger = BaseLogger()
        # self.ic = self.base_logger.ic
        # self.pf = self.base_logger.pf

    async def login(self, request: Request) -> bool:
        id_token = request.cookies.get(ac.firebase.token.id)
        user_data = None
        if id_token:
            if current_user.is_authenticated(request):
                return True
            with suppress(
                auth.ExpiredIdTokenError,
                auth.RevokedIdTokenError,
                auth.InvalidIdTokenError,
            ):
                user_data = auth.verify_id_token(id_token, check_revoked=True)

            if user_data:
                async with db.async_session() as session:
                    user_query = select(self.user_model).where(
                        self.user_model.email == user_data["email"]
                        and self.user_model.is_active
                    )
                    result = await session.execute(user_query)
                    enabled_user = result.one_or_none()
                if enabled_user and (time() - user_data["auth_time"] < 5 * 6):
                    enabled_user = enabled_user[0]
                    short_url = await minify.url(user_data["picture"])
                    auth.set_custom_user_claims(
                        user_data["uid"], {enabled_user.role: True}
                    )
                    async with db.async_session() as session:
                        enabled_user.name = (user_data["name"],)
                        enabled_user.uid = (user_data["uid"],)
                        enabled_user.image = (short_url,)
                        await enabled_user.save()
                        # session.add(enabled_user)
                        # await session.commit()
                    expires_in = timedelta(days=14)
                    session_cookie = auth.create_session_cookie(
                        id_token, expires_in=expires_in
                    )
                    request.session.update({ac.firebase.token.id: session_cookie})
                    ic(request.session.keys())
                    return True
                else:
                    auth.revoke_refresh_tokens(user_data["uid"])
        request.session.clear()
        current_user.user_data = dict()
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        with suppress(
            auth.ExpiredIdTokenError, auth.RevokedIdTokenError, auth.InvalidIdTokenError
        ):
            id_token = request.cookies.get(ac.firebase.token.id)
            user_data = auth.verify_id_token(id_token, check_revoked=True)
            auth.revoke_refresh_tokens(user_data["uid"])
        current_user.user_data = dict()
        return True


authentication_backend = SQLAdminAuthenticationBackend
