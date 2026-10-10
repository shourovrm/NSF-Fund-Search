You are reading saved Google search results about US researchers who lead National Science Foundation grants. For each person, decide their department, job title and role, and pick which result is their department page and which is their website. You do not search or open any page: use only the text given.

Your files are in /home/rms/agent-searching/Grad-Application/NSF/data/faculty/cache/web/ and are named read_NN_p01.txt, read_NN_p02.txt and so on, where NN is the two-digit number you were given. Work through them in order. For each one: read it, then write your answers to results_NN_pKK.jsonl with the same NN and part number, and only then open the next file. Stop when the next part does not exist.

Each person is a block:
    ## <id> | <name> | <institution> | <email> | grant: <start of their grant title>
    1. <link> | <page title> | <snippet>
    2. ...
NSF institution names can be legal wrappers (for example "Georgia Tech Research Corporation" is Georgia Tech).
The heading may end with "department on record: <name>"; that department is already known, so you only need the page and the website.
A result whose title starts with "WEBSITE ON RECORD" is the person's own website, already known, followed by text taken from that page. If that text states their department, use it and give that result's number as department_result.

For each person write one JSON object on one line, with exactly these keys:
{"id": "<id copied exactly, as a string>", "department": "<department or school name without 'Department of', or null>", "department_result": <number or null>, "website_result": <number or null>, "job_title": "<title as written in a result, or null>", "role": "faculty" | "not faculty" | "unknown"}

Rules:
- department: only a department, school or institute that a result states for this person at this institution. If no result states one, use null. Do not infer it from the grant title.
- department_result: the number of the result that is a page of the institution (or the person's own site) naming this person, preferably their profile or directory page. Null if none fits.
- website_result: the number of the person's own lab, group or personal homepage if one is listed; otherwise their institutional profile page. It may be the same number as department_result. News articles, award announcements, seminar listings and other people's pages are not websites; use null rather than pick one.
- Same person: the result must be about a person with this name whose field fits the grant, at this institution or at the institution their email address belongs to. NSF's institution can be out of date or can be an organisation that only manages the grant; when it and the email disagree, the email shows where the person works. A page that prints the person's email address is theirs. A person can also go by a middle or short name (NSF's "Charles D Sherrill" is "C. David Sherrill"). If the results are about a namesake in another field or place, use null for everything and role "unknown".
- A list of many people (a faculty directory, a lab's team page), a file such as a CV in PDF, and a profile on LinkedIn or a similar service are never the website_result. A list may be the department_result when nothing better names the person.
- role: "faculty" for assistant, associate or full professors (including research or teaching professors and named chairs); "not faculty" for research scientists, staff, lecturers, directors without a professor title, postdocs, emeritus professors, museum or company staff; "unknown" when no result gives a title.
- Write every person in the file, in order. Valid JSON on every line, no markdown, no extra text in the file.

Do not modify any other file. When all your parts are done, reply with one line: how many people you wrote, how many have a department, how many have a website_result.
