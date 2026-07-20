"""Academic Publishing Intelligence — Grant analyzer (Phase XII)."""
from __future__ import annotations

from .models import GrantFit

_GRANTS: list[dict] = [
    # ── US ────────────────────────────────────────────────────────────────────
    {"title": "NIH R01 Research Grant",               "funder": "NIH",           "amt": 500000, "topics": ["medicine","health","biology","neuroscience","public health"],      "elig": ["phd","md","faculty"],           "criteria": ["significance","innovation","approach","investigators","environment"], "docs": ["research plan","budget","biosketches","letters of support"]},
    {"title": "NSF CAREER Award",                      "funder": "NSF",           "amt": 650000, "topics": ["engineering","computer science","education","science","mathematics"],"elig": ["faculty","early career"],      "criteria": ["intellectual merit","broader impacts","educational integration"],      "docs": ["project description","budget","data management plan","evaluation plan"]},
    {"title": "NSF Standard Research Grant",           "funder": "NSF",           "amt": 300000, "topics": ["engineering","computer science","mathematics","social science"],      "elig": ["faculty","researcher"],        "criteria": ["intellectual merit","broader impacts","feasibility"],                  "docs": ["project description","budget","references","CVs"]},
    {"title": "NIH K Award (Career Development)",      "funder": "NIH",           "amt": 150000, "topics": ["medicine","health","clinical","translational","nursing"],             "elig": ["early career","postdoc","md"], "criteria": ["candidate","mentor","research plan","training"],                        "docs": ["research plan","mentor letters","biosketches","training plan"]},
    {"title": "Gates Foundation Grand Challenges",     "funder": "Gates",         "amt": 100000, "topics": ["global health","poverty","education","agriculture","nutrition"],       "elig": ["any"],                        "criteria": ["innovation","impact","feasibility","scalability"],                      "docs": ["proposal","budget","team credentials","impact plan"]},
    # ── EU ────────────────────────────────────────────────────────────────────
    {"title": "ERC Starting Grant",                    "funder": "ERC",           "amt": 1500000,"topics": ["any","frontier research","europe","science","humanities"],             "elig": ["early career","phd","2-7yr"], "criteria": ["scientific excellence","pi profile","project quality"],                 "docs": ["b1 extended synopsis","b2 detailed proposal","CV","track record"]},
    {"title": "ERC Consolidator Grant",                "funder": "ERC",           "amt": 2000000,"topics": ["any","frontier research","europe"],                                   "elig": ["established researcher","7-12yr phd"], "criteria": ["scientific excellence","pi profile","feasibility"],              "docs": ["b1 synopsis","b2 full proposal","CV","publication list"]},
    {"title": "Horizon Europe MSCA Postdoctoral Fellowship","funder": "EU/MSCA",  "amt": 200000, "topics": ["any","europe","interdisciplinary","international mobility"],            "elig": ["postdoc","0-8yr phd"],         "criteria": ["scientific quality","training","intersectoral","international"],        "docs": ["part b proposal","CV","host letter","workplan"]},
    {"title": "Horizon Europe Collaborative Projects",  "funder": "EU/H2020",     "amt": 3000000,"topics": ["technology","energy","health","society","environment","innovation"],   "elig": ["consortium","3+ countries"],  "criteria": ["excellence","impact","implementation","consortium quality"],            "docs": ["full proposal","consortium agreement","data plan","ethics review"]},
    # ── UK ────────────────────────────────────────────────────────────────────
    {"title": "UKRI Standard Research Grant",          "funder": "UKRI",          "amt": 500000, "topics": ["science","engineering","medicine","arts","social science","humanities"], "elig": ["faculty","research fellow"], "criteria": ["significance","originality","rigor","track record"],                    "docs": ["case for support","impact plan","CVs","letters of support"]},
    {"title": "Wellcome Trust Investigator Award",     "funder": "Wellcome",      "amt": 3000000,"topics": ["biology","medicine","health","neuroscience","global health"],           "elig": ["established researcher"],     "criteria": ["scientific quality","investigator track record","environment"],         "docs": ["preliminary application","full application","CVs","reference letters"]},
    # ── International / Private ───────────────────────────────────────────────
    {"title": "Bill & Melinda Gates Grand Challenges Exploration","funder":"Gates","amt": 100000,"topics": ["global health","poverty","agriculture","education","sanitation"],       "elig": ["any"],                       "criteria": ["innovation","global impact","feasibility"],                            "docs": ["two page proposal","budget"]},
    {"title": "Fulbright Scholar Program",             "funder": "Fulbright",     "amt": 50000,  "topics": ["any","international","cultural exchange","research"],                   "elig": ["us citizen","faculty","phd"], "criteria": ["academic merit","project quality","cultural engagement"],               "docs": ["project statement","CV","references","language certification"]},
]


def _topic_fit(text: str, discipline: str, grant_topics: list[str]) -> float:
    combined = text.lower() + " " + discipline.lower()
    hits = sum(1 for t in grant_topics if t in combined)
    any_ok = "any" in grant_topics
    if any_ok:
        return 0.7
    return min(1.0, hits / max(len(grant_topics) * 0.4, 1))


def _eligibility_score(
    profile: dict,
    grant_elig: list[str],
) -> float:
    """Estimate eligibility based on user's academic profile."""
    role = str(profile.get("role", "")).lower()
    career_stage = str(profile.get("career_stage", "")).lower()
    combined = role + " " + career_stage

    if "any" in grant_elig:
        return 0.9

    score = 0.0
    if "faculty" in grant_elig and ("professor" in combined or "faculty" in combined or "lecturer" in combined):
        score += 0.5
    if "phd" in grant_elig and ("phd" in combined or "doctoral" in combined):
        score += 0.3
    if "postdoc" in grant_elig and "postdoc" in combined:
        score += 0.4
    if "early career" in grant_elig and any(kw in combined for kw in ["early", "junior", "postdoc", "phd"]):
        score += 0.4
    if "researcher" in grant_elig:
        score += 0.3

    return min(1.0, score + 0.2)


def _competitiveness(funder: str, amount: int) -> float:
    """Lower = more competitive. ERC/NIH are most competitive."""
    very_hard = {"ERC", "NIH", "NeurIPS", "Wellcome"}
    hard = {"NSF", "UKRI", "EU/H2020", "EU/MSCA"}
    moderate = {"Gates", "Fulbright"}

    if funder in very_hard:
        base = 0.15
    elif funder in hard:
        base = 0.30
    elif funder in moderate:
        base = 0.45
    else:
        base = 0.55

    # Large grants are harder
    if amount > 1_000_000:
        base *= 0.7
    elif amount > 500_000:
        base *= 0.85

    return round(min(1.0, max(0.05, base)), 3)


def analyze_grant_fit(
    text: str,
    discipline: str,
    manuscript_quality: float,
    user_profile: dict | None = None,
) -> list[GrantFit]:
    profile = user_profile or {}
    scored: list[tuple[float, GrantFit]] = []

    for g in _GRANTS:
        topic = _topic_fit(text, discipline, g["topics"])
        if topic == 0.0:
            continue

        elig = _eligibility_score(profile, g["elig"])
        comp = _competitiveness(g["funder"], g["amt"])
        q = manuscript_quality / 100.0

        # Funding probability: topic × eligibility × research quality × competitiveness
        fund_prob = round(topic * elig * (0.4 + 0.6 * q) * comp, 3)

        # Proposal readiness from quality
        readiness = round(0.3 + 0.7 * q, 3)

        missing: list[str] = []
        if topic < 0.5:
            missing.append("Strengthen research topic alignment with grant scope")
        if elig < 0.5:
            missing.append("Verify eligibility criteria (career stage, institution)")
        if q < 0.6:
            missing.append("Improve manuscript quality before applying")
        if not profile.get("publications"):
            missing.append("Establish publication track record")

        strengths: list[str] = []
        if topic >= 0.7:
            strengths.append(f"Strong topic alignment with {g['funder']} scope")
        if elig >= 0.7:
            strengths.append("You meet the eligibility criteria")
        if q >= 0.7:
            strengths.append("Strong research quality supports competitive proposal")

        overall_fit = round(
            0.4 * topic + 0.25 * elig + 0.25 * comp + 0.10 * readiness, 3
        )

        fit = GrantFit(
            title=g["title"],
            funder=g["funder"],
            amount_usd=g["amt"],
            eligibility=g["elig"],
            required_docs=g["docs"],
            evaluation_criteria=g["criteria"],
            topics=g["topics"],
            eligibility_score=elig,
            topic_fit=topic,
            competitiveness=comp,
            funding_probability=fund_prob,
            proposal_readiness=readiness,
            missing_elements=missing,
            strengths=strengths,
            rationale=(
                f"{g['title']} ({g['funder']}, ${g['amt']:,}) shows {topic:.0%} topic fit "
                f"with estimated {fund_prob:.0%} funding probability."
            ),
        )
        scored.append((overall_fit, fit))

    scored.sort(key=lambda x: -x[0])
    return [f for _, f in scored]
