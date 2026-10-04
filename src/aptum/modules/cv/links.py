from aptum.modules.profile.models import Profile


def visible_link_urls(profile: Profile) -> list[str]:
    """URLs of the links the user left visible, in the order they saved them, without repeats."""
    urls = (link["url"] for link in profile.links or [] if link.get("visible", True) and link.get("url"))
    return list(dict.fromkeys(urls))
