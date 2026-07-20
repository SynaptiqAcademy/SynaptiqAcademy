"""Academic Publishing Intelligence — Conference analyzer (Phase XII)."""
from __future__ import annotations

from .models import ConferenceFit

_CONFERENCES: list[dict] = [
    # ── CS / AI ───────────────────────────────────────────────────────────────
    {"name": "International Conference on Machine Learning", "acr": "ICML",  "pub": "PMLR",     "rank": "A*", "acc": 0.26, "fee": 750,  "indexed": True, "jt": False, "tags": ["ai","machine learning","deep learning","optimization","nlp"],          "loc": "International"},
    {"name": "Neural Information Processing Systems",         "acr": "NeurIPS","pub": "Curran",   "rank": "A*", "acc": 0.26, "fee": 750,  "indexed": True, "jt": False, "tags": ["ai","deep learning","reinforcement learning","generative models"],      "loc": "North America"},
    {"name": "International Conference on Learning Representations","acr":"ICLR","pub":"OpenReview","rank":"A*","acc":0.32,"fee":500,   "indexed": True, "jt": False, "tags": ["deep learning","representation learning","ai"],                            "loc": "International"},
    {"name": "ACL Annual Meeting",                             "acr": "ACL",   "pub": "ACL",      "rank": "A*", "acc": 0.24, "fee": 600,  "indexed": True, "jt": True,  "tags": ["nlp","language","text","machine translation","dialogue"],               "loc": "International"},
    {"name": "IEEE/CVF Computer Vision and Pattern Recognition","acr":"CVPR", "pub":"IEEE",      "rank": "A*", "acc": 0.25, "fee": 700,  "indexed": True, "jt": False, "tags": ["computer vision","image","deep learning","detection","recognition"],     "loc": "North America"},
    {"name": "AAAI Conference on Artificial Intelligence",     "acr": "AAAI",  "pub": "AAAI",     "rank": "A",  "acc": 0.23, "fee": 650,  "indexed": True, "jt": False, "tags": ["ai","knowledge","reasoning","planning","ethics"],                       "loc": "North America"},
    {"name": "ACM International Conference on Information Retrieval","acr":"SIGIR","pub":"ACM", "rank": "A",  "acc": 0.25, "fee": 600,  "indexed": True, "jt": False, "tags": ["information retrieval","search","nlp","recommendation"],                  "loc": "International"},
    # ── Medicine / Health ─────────────────────────────────────────────────────
    {"name": "European Congress of Cardiology",                "acr": "ESC",   "pub": "ESC",      "rank": "A",  "acc": 0.30, "fee": 900,  "indexed": True, "jt": True,  "tags": ["cardiology","medicine","clinical","heart failure"],                     "loc": "Europe"},
    {"name": "American Heart Association Scientific Sessions", "acr": "AHA",   "pub": "AHA",      "rank": "A",  "acc": 0.30, "fee": 800,  "indexed": True, "jt": True,  "tags": ["cardiology","medicine","clinical","vascular","stroke"],                  "loc": "North America"},
    # ── Psychology / Education ────────────────────────────────────────────────
    {"name": "American Psychological Association Annual Convention","acr":"APA","pub":"APA",    "rank": "A",  "acc": 0.40, "fee": 400,  "indexed": True, "jt": False, "tags": ["psychology","cognitive","social","clinical","behaviour"],                 "loc": "North America"},
    {"name": "Society for Research on Educational Effectiveness","acr":"SREE", "pub": "SREE",    "rank": "B",  "acc": 0.45, "fee": 300,  "indexed": True, "jt": False, "tags": ["education","learning","pedagogy","assessment","policy"],                  "loc": "North America"},
    # ── Engineering ───────────────────────────────────────────────────────────
    {"name": "IEEE World Congress on Computational Intelligence","acr":"WCCI","pub":"IEEE",     "rank": "A",  "acc": 0.35, "fee": 750,  "indexed": True, "jt": False, "tags": ["engineering","ai","neural networks","evolutionary","control"],             "loc": "International"},
    {"name": "Renewable Energy World Conference",               "acr": "REWC",  "pub": "Elsevier","rank": "B", "acc": 0.50, "fee": 450,  "indexed": True, "jt": True,  "tags": ["energy","renewable","sustainability","solar","wind"],                    "loc": "Europe"},
    # ── Social Science / Management ───────────────────────────────────────────
    {"name": "Academy of Management Annual Meeting",            "acr": "AoM",   "pub": "AOM",      "rank": "A",  "acc": 0.35, "fee": 500,  "indexed": True, "jt": False, "tags": ["management","organisation","strategy","leadership","behaviour"],        "loc": "North America"},
    {"name": "European Academy of Management Conference",       "acr": "EURAM", "pub": "EURAM",    "rank": "B",  "acc": 0.40, "fee": 400,  "indexed": True, "jt": False, "tags": ["management","organisation","strategy","innovation","sustainability"],   "loc": "Europe"},
]

_RANK_SCORES = {"A*": 1.0, "A": 0.8, "B": 0.6, "C": 0.4}


def _to_fit(c: dict) -> ConferenceFit:
    return ConferenceFit(
        name=c["name"], acronym=c["acr"], publisher=c["pub"],
        ranking=c["rank"], acceptance_rate=c["acc"],
        topics=c["tags"], is_indexed=c["indexed"],
        offers_journal_track=c.get("jt", False),
        registration_fee_usd=c.get("fee", 500),
        location=c.get("loc", "International"),
        presentation_types=["oral", "poster"],
    )


def _scope_hit(text: str, discipline: str, tags: list[str]) -> float:
    combined = text.lower() + " " + discipline.lower()
    hits = sum(1 for t in tags if t in combined)
    return min(1.0, hits / max(len(tags) * 0.4, 1))


def analyze_conference_fit(
    text: str,
    discipline: str,
    manuscript_quality: float,
) -> list[ConferenceFit]:
    scored: list[tuple[float, ConferenceFit]] = []
    for c in _CONFERENCES:
        scope = _scope_hit(text, discipline, c["tags"])
        if scope == 0.0:
            continue

        rank_score = _RANK_SCORES.get(c["rank"], 0.5)
        q = manuscript_quality / 100.0
        acc_prob = c["acc"] * (0.4 + 0.6 * q) * (0.6 + 0.4 * scope)
        acc_prob = round(min(0.90, max(0.02, acc_prob)), 3)

        jt_bonus = 0.15 if c.get("jt") else 0.0
        network = round(rank_score * 0.8 + 0.2, 3)
        career = round(rank_score * 0.7 + scope * 0.3, 3)
        pub_val = round((0.5 if c.get("indexed") else 0.1) + jt_bonus, 3)
        overall = round(
            0.35 * scope + 0.25 * acc_prob + 0.20 * network
            + 0.10 * career + 0.10 * pub_val,
            3,
        )

        fit = _to_fit(c)
        fit.research_fit = round(scope, 3)
        fit.acceptance_probability = acc_prob
        fit.networking_value = network
        fit.career_value = career
        fit.publication_value = pub_val
        fit.overall_score = overall
        fit.rationale = (
            f"{c['name']} ({c['rank']}) aligns {scope:.0%} with your research area "
            f"with estimated {acc_prob:.0%} acceptance probability."
        )
        scored.append((overall, fit))

    scored.sort(key=lambda x: -x[0])
    return [f for _, f in scored]
