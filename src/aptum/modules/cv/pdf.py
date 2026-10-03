from aptum.modules.cv.ats.pipeline import generate_ats_cv
from aptum.modules.profile.models import Profile


def render_cv_pdf(profile: Profile) -> bytes:
    """The default CV download: the ATS PDF."""
    return generate_ats_cv(profile).pdf
