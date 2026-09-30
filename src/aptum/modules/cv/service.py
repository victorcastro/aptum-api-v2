from sqlalchemy.orm import Session

from aptum.modules.cv.pdf import render_cv_pdf
from aptum.modules.profile.service import ProfileService


class CVService:
    def __init__(self, db: Session) -> None:
        self.profiles = ProfileService(db)

    def export_pdf(self, user_id: int) -> bytes:
        """Render the authenticated user's own profile; the profile is always resolved by user_id."""
        return render_cv_pdf(self.profiles.get_or_create(user_id))
