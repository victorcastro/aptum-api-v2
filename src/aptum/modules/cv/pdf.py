from aptum.modules.cv.document import build_cv_data
from aptum.modules.cv.templates.registry import DEFAULT_TEMPLATE, get_template
from aptum.modules.profile.models import Profile


def render_cv_pdf(profile: Profile) -> bytes:
    return get_template(DEFAULT_TEMPLATE).render(build_cv_data(profile))
