from typing import List
from requests import Response, post
import os

from libs.strings import gettext


class Mailgun:
    MAILGUN_DOMAIN = os.environ.get("MAILGUN_DOMAIN")  # can be None
    MAILGUN_API_KEY = os.environ.get("MAILGUN_API_KEY")  # can be None

    FROM_TITLE = "Stores REST API"
    FROM_EMAIL = "postmaster@sandbox2a515628660c4502bba934fd43899bba.mailgun.org"

    @classmethod
    def send_email(cls, email: List[str], subject, text, html) -> Response:
        if cls.MAILGUN_DOMAIN is None:
            raise MailGunException(gettext("mailgun_failed_load_domain"))

        if cls.MAILGUN_API_KEY is None:
            raise MailGunException(gettext("mailgun_failed_load_api_key"))
        response = post(
            f"https://api.mailgun.net/v3/{cls.MAILGUN_DOMAIN}/messages",
            auth=("api", f"{cls.MAILGUN_API_KEY}"),
            data={
                "from": f"{cls.FROM_TITLE} <{cls.FROM_EMAIL}>",
                "to": email,
                "subject": subject,
                "text": text,
                "html": html
            },
        )

        if response.status_code != 200:
            raise MailGunException(gettext("mailgun_error_send_email"))

        return response


class MailGunException(Exception):
    def __init__(self, message: str):
        super().__init__(message)
