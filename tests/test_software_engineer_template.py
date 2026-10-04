from conftest import pdf_text
from factories import base_profile

from aptum.modules.cv.document import build_cv_data
from aptum.modules.cv.templates.software_engineer import SoftwareEngineerTemplate


def test_linkedin_prints_full_url_other_links_keep_their_label():
    doc = build_cv_data(base_profile(portfolio_url="https://alex.example.dev"))
    text = pdf_text(SoftwareEngineerTemplate().render(doc))
    assert "https://www.linkedin.com/in/example-alex" in text.replace("\n", "")
    assert "GitHub" in text and "Portfolio" in text
