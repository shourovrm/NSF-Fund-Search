"""List the lead investigators of the site's awards, one per NSF investigator ID."""

import sys
from pathlib import Path

# nsf_awards.py sits one directory up and is a script, not an installed package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import nsf_awards  # noqa: E402


def load_lead_investigators():
    """Return {nsf_id: investigator} for the lead PI of every award the site shows.

    Awards are read oldest first, so a person who moved keeps the institution
    and email of their newest award.
    """
    awards = [
        award for award in nsf_awards.load_awards()
        if nsf_awards.is_active_at_fall_2027(award) and nsf_awards.is_research_award_funding_students(award)
    ]
    awards.sort(key=lambda award: award.get("awd_min_amd_letter_date") or "")
    investigators = {}
    for award in awards:
        lead_pi, _ = nsf_awards.current_investigators(award)
        if lead_pi is None or not lead_pi.get("nsf_id"):
            continue
        investigator = investigators.setdefault(lead_pi["nsf_id"], {"nsf_id": lead_pi["nsf_id"], "grant_titles": []})
        investigator["name"] = lead_pi["pi_full_name"]
        investigator["first_name"] = lead_pi["pi_first_name"]
        investigator["last_name"] = lead_pi["pi_last_name"]
        investigator["email"] = lead_pi.get("pi_email_addr") or ""
        investigator["institution"] = (award.get("inst") or {}).get("inst_name") or ""
        investigator["grant_titles"].append(award.get("awd_titl_txt") or "")
    return investigators
