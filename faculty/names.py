"""Decide whether two spellings name the same person or the same institution."""

import re
import unicodedata

# Words that do not tell two institutions apart, plus legal wrappers NSF puts around names.
INSTITUTION_STOPWORDS = {
    "university", "univ", "of", "the", "at", "and", "in", "for", "regents", "trustees", "research", "foundation",
    "inc", "corporation", "corp", "campus", "main", "system", "board", "president", "fellows", "college", "station",
}

# A two-letter name such as Qi is a whole name, not a short form: without this
# floor "Qi" matched the unrelated "Qingjie".
SHORT_FORM_MIN_LENGTH = 3


def fold_accents(text):
    """Lower-case and drop accents, so that 'José' and 'Jose' compare equal."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(character for character in decomposed if not unicodedata.combining(character)).lower()


def institution_tokens(name):
    words = re.findall(r"[a-z]+", fold_accents(name).replace("&", " and "))
    return {word for word in words if word not in INSTITUTION_STOPWORDS}


def is_same_institution(first_name, second_name):
    """True when one name's distinctive words all appear in the other, e.g.
    'University of Michigan' and NSF's 'Regents of the University of Michigan - Ann Arbor'."""
    first_tokens = institution_tokens(first_name)
    second_tokens = institution_tokens(second_name)
    if not first_tokens or not second_tokens:
        return False
    return first_tokens <= second_tokens or second_tokens <= first_tokens


def is_same_given_name(first_name, second_name):
    """True for equal first names, for an initial, and for a short form such as Steve for Steven."""
    first_word = re.split(r"[\s.]+", fold_accents(first_name).strip())[0]
    second_word = re.split(r"[\s.]+", fold_accents(second_name).strip())[0]
    if not first_word or not second_word:
        return False
    if first_word == second_word:
        return True
    shorter, longer = sorted((first_word, second_word), key=len)
    if len(shorter) == 1:
        return longer.startswith(shorter)
    if len(shorter) < SHORT_FORM_MIN_LENGTH:
        return False
    return longer.startswith(shorter) or (len(shorter) >= 4 and shorter[:4] == longer[:4])
