"""Tell a person's own page from a link that only mentions them: a file, a news story, a list of people."""

import re
import urllib.parse

import names

FILE = "file"
SHARED_SERVICE = "shared service"
NEWS_PAGE = "news page"
LIST_PAGE = "list page"

# A CV or a paper is about the person but is not a page a reader can browse from.
FILE_PATH = re.compile(r"\.(pdf|docx?|pptx?|xlsx?|csv|txt|bib|zip)$")
# Pages about the person on shared services; a reader needs the person's own or the university's pages.
SHARED_SERVICE_HOSTS = re.compile(
    r"(^|\.)(linkedin|facebook|twitter|x|instagram|youtube|researchgate|ratemyprofessors|rocketreach|zoominfo"
    r"|academia|semanticscholar|openreview|ieeexplore\.ieee|dl\.acm|scilit|alphaxiv|arxiv|orcid|scholar\.google"
    r"|wikipedia|amazon|signalhire|contactout|expertisefinder|academictree|mathgenealogy)\.[a-z.]+$"
)
# A code repository, unlike the personal sites served from github.io.
CODE_HOSTS = {"github.com", "gist.github.com", "raw.githubusercontent.com", "gitlab.com"}
NEWS_SEGMENT = re.compile(
    r"^(news|news-events|news-and-events|stories|story|press|press-releases?|events?|seminars?|blog"
    r"|announcements?|catalog|bulletin)$")
# "people", "our-team" and "bioengineering-faculty" are lists; "faculty-profile" is one person.
LIST_SEGMENT = re.compile(r"(^|[-_])(people|team|faculty|staff|directory|members|personnel)$")
INDEX_FILE = re.compile(r"^(index|default|home)\.[a-z]+$")
# A shorter word of a name, such as the "li" of "Li", turns up inside unrelated words of a link.
NAME_WORD_MIN_LENGTH = 3


def name_words(lookup_entry):
    """Return the words that mark a link as this person's: family name, given name and email name."""
    words = re.split(r"[\s\-']+", names.fold_accents(lookup_entry["last_name"]))
    words.append(names.fold_accents(lookup_entry["first_name"]).split()[0] if lookup_entry["first_name"].strip() else "")
    words.append(lookup_entry["email"].split("@")[0].lower())
    return {word for word in words if len(word) >= NAME_WORD_MIN_LENGTH}


def url_names_person(url, lookup_entry):
    folded_url = names.fold_accents(urllib.parse.unquote(url))
    return any(word in folded_url for word in name_words(lookup_entry))


def path_segments(url):
    path = urllib.parse.unquote(urllib.parse.urlparse(url).path).lower()
    segments = [segment for segment in path.split("/") if segment]
    if segments and INDEX_FILE.match(segments[-1]):
        segments.pop()
    return segments


def weakness(url, lookup_entry):
    """Return why this link is not the person's own page, or None when nothing is wrong with it."""
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    segments = path_segments(url)
    if FILE_PATH.search(parsed.path.lower()):
        return FILE
    if SHARED_SERVICE_HOSTS.search(host) or host in CODE_HOSTS:
        return SHARED_SERVICE
    if any(NEWS_SEGMENT.match(segment) for segment in segments):
        return NEWS_PAGE
    # A list on the person's own site, such as smithlab.org/people, still leads to them.
    if segments and LIST_SEGMENT.search(segments[-1]) and not url_names_person(url, lookup_entry):
        return LIST_PAGE
    return None


def shorter_urls(url):
    """Return the pages above this one on the same site, the site's front page first."""
    parsed = urllib.parse.urlparse(url)
    segments = [segment for segment in parsed.path.split("/") if segment]
    site = f"{parsed.scheme}://{parsed.netloc}"
    return [site + "/" + "".join(segment + "/" for segment in segments[:depth]) for depth in range(len(segments))]
