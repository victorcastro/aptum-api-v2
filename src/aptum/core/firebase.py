import firebase_admin
from firebase_admin import auth, credentials

from aptum.core.config import get_settings


def _ensure_initialized() -> None:
    if firebase_admin._apps:
        return
    settings = get_settings()
    options = {"projectId": settings.firebase_project_id}
    if settings.firebase_client_email and settings.firebase_private_key:
        cred = credentials.Certificate(
            {
                "type": "service_account",
                "project_id": settings.firebase_project_id,
                "client_email": settings.firebase_client_email,
                "private_key": settings.firebase_private_key.replace("\\n", "\n"),
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        )
        firebase_admin.initialize_app(cred, options)
    else:
        firebase_admin.initialize_app(options=options)


def verify_id_token(token: str) -> dict:
    """Return the decoded claims of a Firebase ID token. Raises ValueError-family errors if invalid."""
    _ensure_initialized()
    return auth.verify_id_token(token, check_revoked=get_settings().firebase_check_revoked)
