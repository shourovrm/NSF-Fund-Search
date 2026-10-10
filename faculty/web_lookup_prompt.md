You are looking up US researchers on the web. Each one leads a National Science Foundation grant. For each person find their department, their own website, their Google Scholar profile, and whether they are faculty.

Input file (read it first, one JSON object per line): {lookup_path}
Each line has: id, name, email, institution, grant_title, and known_department / known_website / known_scholar (already found; null means missing). The file is sorted by institution, so reuse what you learn about one institution's site for its other people. NSF institution names can be legal wrappers (e.g. "Georgia Tech Research Corporation" means Georgia Tech).

How to look up each person:
- Search for the name plus the institution (add a word from the grant topic if the name is common). Prefer the person's profile page on the institution's own site.
- Open the best page when the search result does not clearly state the department and job title.
- Spend at most 3 searches or page reads per person. If you still have not found something, leave that field null. Do not keep digging.
- Make sure it is the same person: the institution must match, and the research area should fit the grant title. The email username is a useful check.

Hard rules about links (a script will fetch every link afterwards and reject pages that do not load or do not show the person's name):
- Report only URLs that you actually saw in a search result or on a page you read. Never construct, guess or "fix" a URL.
- department_url must be a page that shows this person's name together with their department (normally their profile page on the institution site, or a department directory page listing them).
- website is the person's own lab, group or personal homepage if one exists; otherwise their institutional profile page. It must be about this person specifically, not a department home page.
- scholar must be a Google Scholar profile URL of the form https://scholar.google.com/citations?user=XXXXXXXXXXXX that you saw linked or listed for this person. If you did not see one, use null. Never invent the ID.
- If known_website or known_scholar is already given, copy it into your answer unless you found it is wrong.

Output: write one JSON object per line, for every person in the input file, to {results_path} with exactly these keys:
{{"id": "<id copied from the input, as a string>", "department": "<department or school name, without 'Department of', or null>", "department_url": "<URL or null>", "website": "<URL or null>", "scholar": "<URL or null>", "job_title": "<title as written on the page, e.g. Associate Professor, or null>", "role": "faculty" | "not faculty" | "unknown", "note": "<one short sentence: what you opened, or why something is missing>"}}

role is "faculty" for assistant, associate or full professors (including research or teaching professors); "not faculty" for research scientists, staff, lecturers, directors without a professor title, postdocs, emeritus professors, museum or company staff; "unknown" when you could not find the title.

Write valid JSON on every line, with no markdown and no trailing commas. Do not modify any other file. When done, reply with one line: how many people have a department, how many have a website, how many have a scholar link.
