from aptum.modules.cv.document import build_cv_data
from aptum.modules.cv.templates.classic import ClassicTemplate
from aptum.modules.profile.models import Profile


def render_cv_pdf(profile: Profile) -> bytes:
    return ClassicTemplate().render(build_cv_data(profile))
