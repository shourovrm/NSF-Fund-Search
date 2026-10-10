"""Read a job title: is it a faculty post, and is it a student or postdoc post."""

import re

FACULTY = "faculty"
NOT_FACULTY = "not faculty"
UNKNOWN = "unknown"

PROFESSOR_TITLE = re.compile(r"professor|\bprof\b|\bfaculty\b|\bdean\b|department (chair|head)", re.IGNORECASE)

# Professors in name who usually cannot take a PhD student as primary advisor.
# The title alone does not settle it, so these stay "unknown".
LIMITED_PROFESSOR_TITLE = re.compile(r"adjunct|visiting|emerit|courtesy|affiliate", re.IGNORECASE)

STUDENT_OR_POSTDOC_TITLE = re.compile(
    r"student|candidate|trainee|undergraduate|\bintern\b|\bph\.?d\b|doctoral|post-?\s?doc"
    r"|graduate (research|teaching|assistant|fellow)|(research|teaching) assistant",
    re.IGNORECASE,
)

STAFF_TITLE = re.compile(
    r"scientist|researcher|research (associate|fellow|staff)|engineer|lecturer|instructor|manager|director"
    r"|coordinator|specialist|curator|librarian|technician|analyst|developer|administrator|officer",
    re.IGNORECASE,
)


def is_student_or_postdoc_title(job_title):
    # "Research Assistant Professor" holds the words "research assistant" but is a faculty post.
    if PROFESSOR_TITLE.search(job_title):
        return False
    return bool(STUDENT_OR_POSTDOC_TITLE.search(job_title))


def role_from_job_title(job_title):
    """Return FACULTY, NOT_FACULTY or UNKNOWN for a job title; a blank title is UNKNOWN."""
    if not job_title:
        return UNKNOWN
    if PROFESSOR_TITLE.search(job_title):
        if LIMITED_PROFESSOR_TITLE.search(job_title):
            return UNKNOWN
        return FACULTY
    if is_student_or_postdoc_title(job_title) or STAFF_TITLE.search(job_title):
        return NOT_FACULTY
    return UNKNOWN
