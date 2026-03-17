"""Custom JWT authentication backend for workers."""

import logging
from typing import Optional, Tuple

from django.utils.translation import gettext_lazy as _
from rest_framework import authentication, exceptions
from rest_framework.request import Request
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from workers.models import Worker

logger = logging.getLogger(__name__)


class WorkerJWTAuthentication(authentication.BaseAuthentication):
    """Authenticate requests using a JWT that encodes a worker_id."""

    keyword = "Bearer"

    def authenticate(self, request: Request) -> Optional[Tuple[Worker, str]]:
        """Authenticate the request and attach worker to it."""
        auth_header = authentication.get_authorization_header(request).decode("utf-8")
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) != 2 or parts[0] != self.keyword:
            return None

        token = parts[1]
        try:
            untoken = UntypedToken(token)
        except (InvalidToken, TokenError) as exc:
            logger.warning("Invalid worker JWT: %s", exc)
            raise exceptions.AuthenticationFailed(_("Invalid token"))

        worker_id = untoken.payload.get("worker_id")
        if not worker_id:
            raise exceptions.AuthenticationFailed(_("Invalid worker token payload"))

        try:
            worker = Worker.objects.get(id=worker_id)
        except Worker.DoesNotExist:
            raise exceptions.AuthenticationFailed(_("Worker not found"))

        # Attach worker to request for downstream permissions and views.
        request.worker = worker
        return worker, token

