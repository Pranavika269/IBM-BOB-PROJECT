"""The ProjectMatch matching engine (pure Python, no heavy dependencies).

Student -> project fit  = skills (45%) + interests (25%) + time (15%) + experience (15%)
Project -> teammate fit = gap-filling skills (55%) + interests (20%) + time (15%) + variety (10%)

Interest fit blends tag overlap with a TF-IDF cosine similarity between the student's
bio/interests and the project description, so "I like building tools for hospitals" can
still match a project tagged "healthcare".
"""
import math
import re
from collections import Counter

from skills import category_of

LEVELS = {"beginner": 1, "intermediate": 2, "advanced": 3}
RELATED_CREDIT = 0.4

STOP = set("""a an and are as at be but by for from has have i in is it its of on or our that the their this to
we with you your will can into using use build building app apps project projects want like need who help helps
students student team""".split())


# ---------------------------------------------------------------- text similarity
def tokenize(text):
    return [t for t in re.findall(r"[a-z][a-z+#.]{1,}", (text or "").lower()) if t not in STOP]


class TextModel:
    """Tiny TF-IDF model fitted on all student and project documents."""

    def __init__(self, docs):
        n = len(docs)
        df = Counter()
        for d in docs:
            df.update(set(tokenize(d)))
        self.idf = {t: math.log((1 + n) / (1 + c)) + 1 for t, c in df.items()}

    def vec(self, text):
        return {t: c * self.idf.get(t, 1.0) for t, c in Counter(tokenize(text)).items()}

    @staticmethod
    def cosine(a, b):
        if not a or not b:
            return 0.0
        dot = sum(v * b.get(t, 0.0) for t, v in a.items())
        na = math.sqrt(sum(v * v for v in a.values()))
        nb = math.sqrt(sum(v * v for v in b.values()))
        return dot / (na * nb) if na and nb else 0.0


def student_doc(s):
    return " ".join([s.get("bio", ""), " ".join(s.get("interests", [])), " ".join(s.get("skills", []))])


def project_doc(p):
    return " ".join([p.get("title", ""), p.get("description", ""), " ".join(p.get("domains", [])),
                     " ".join(p.get("required_skills", []))])


def build_model(students, projects):
    return TextModel([student_doc(s) for s in students] + [project_doc(p) for p in projects])


# ---------------------------------------------------------------- helpers
def credit(skill, have, have_cats):
    if skill in have:
        return 1.0
    cat = category_of(skill)
    if cat != "Other" and cat in have_cats:
        return RELATED_CREDIT
    return 0.0


def categories(skills):
    return {category_of(s) for s in skills if category_of(s) != "Other"}


def shared_interests(interests, domains):
    out = []
    for d in domains:
        dl = d.lower()
        for i in interests:
            il = i.lower()
            if il == dl or (len(il) >= 3 and (il in dl or dl in il)):
                out.append(d)
                break
    return out


def interest_score(student, project, model):
    shared = shared_interests(student.get("interests", []), project.get("domains", []))
    dom = len(shared) / len(project["domains"]) if project.get("domains") else 0.0
    cos = model.cosine(model.vec(student_doc(student)), model.vec(project_doc(project)))
    return min(1.0, 0.6 * dom + 0.4 * min(1.0, cos * 3)), shared


def time_score(student, project):
    need = project.get("hours_per_week") or 0
    return min(1.0, student.get("hours_per_week", 0) / need) if need else 1.0


def experience_score(student, project):
    diff = LEVELS.get(project.get("level", "intermediate"), 2) - LEVELS.get(student.get("experience", "intermediate"), 2)
    if diff == 0:
        return 1.0
    if diff < 0:          # student is more experienced than the project asks
        return 0.8 if diff == -1 else 0.6
    return 0.6 if diff == 1 else 0.25   # project is a stretch


def coverage_map(required, members):
    """skill -> list of member ids who have that exact skill."""
    return {s: [m["id"] for m in members if s in m.get("skills", [])] for s in required}


# ---------------------------------------------------------------- student -> project
def score_project(student, project, model):
    have, cats = set(student["skills"]), categories(student["skills"])
    req = project["required_skills"]
    exact = [s for s in req if s in have]
    related = [s for s in req if s not in have and credit(s, have, cats) > 0]
    total = sum(credit(s, have, cats) for s in req)
    skills = min(1.0, total / max(1, min(len(req), 3)))
    interests, shared = interest_score(student, project, model)
    time_fit = time_score(student, project)
    exp_fit = experience_score(student, project)
    overall = 0.45 * skills + 0.25 * interests + 0.15 * time_fit + 0.15 * exp_fit

    reasons = []
    if exact:
        reasons.append("Your " + _join(exact[:3]) + " fills " + ("a gap" if len(exact) == 1 else "key gaps") + " here")
    elif related:
        reasons.append("Related skills: " + _join(related[:2]))
    if shared:
        reasons.append("You share an interest in " + _join(shared[:2]))
    if time_fit < 1:
        reasons.append(f"Needs {project['hours_per_week']} hrs/week; you have {student['hours_per_week']}")
    if exp_fit < 0.7 and LEVELS.get(project["level"], 2) > LEVELS.get(student["experience"], 2):
        reasons.append("A stretch for your level, good for learning")
    return {
        "score": round(100 * overall),
        "parts": {"skills": round(100 * skills), "interests": round(100 * interests),
                  "time": round(100 * time_fit), "experience": round(100 * exp_fit)},
        "matched_skills": exact, "related_skills": related,
        "to_learn": [s for s in req if s not in exact and s not in related],
        "shared_interests": shared, "reasons": reasons,
    }


# ---------------------------------------------------------------- project -> teammate
def candidate_fit(cand, project, members, model):
    req = project["required_skills"]
    covered = {s for s, ids in coverage_map(req, members).items() if ids}
    gaps = [s for s in req if s not in covered]
    have, cats = set(cand["skills"]), categories(cand["skills"])
    fills = [s for s in gaps if s in have]
    if gaps:
        gap_fit = min(1.0, sum(credit(s, have, cats) for s in gaps) / max(1, min(len(gaps), 2)))
    else:
        gap_fit = 0.5
    interests, shared = interest_score(cand, project, model)
    time_fit = time_score(cand, project)
    team_cats = categories([s for m in members for s in m["skills"]])
    cand_cats = categories(cand["skills"])
    variety = len(cand_cats - team_cats) / max(1, len(cand_cats))
    overall = 0.55 * gap_fit + 0.20 * interests + 0.15 * time_fit + 0.10 * variety
    return {
        "score": round(100 * overall),
        "fills": fills,
        "adds_categories": sorted(cand_cats - team_cats),
        "shared_interests": shared,
        "parts": {"gaps": round(100 * gap_fit), "interests": round(100 * interests),
                  "time": round(100 * time_fit), "variety": round(100 * variety)},
    }


def suggest_team(project, members, candidates, slots, model):
    """Greedy team builder: repeatedly add the person who closes the most skill gaps,
    breaking ties by category variety and overall fit."""
    req = project["required_skills"]
    team, chosen = list(members), []
    pool = list(candidates)

    def covered(t):
        return sum(1 for ids in coverage_map(req, t).values() if ids)

    for _ in range(max(0, slots)):
        best, best_val = None, 0.0
        for c in pool:
            fit = candidate_fit(c, project, team, model)
            gain = covered(team + [c]) - covered(team)
            val = gain + 0.25 * len(fit["adds_categories"]) + 0.5 * fit["score"] / 100
            if val > best_val:
                best, best_val = (c, fit), val
        if not best:
            break
        c, fit = best
        chosen.append({**c, "fit": fit})
        team.append(c)
        pool.remove(c)

    cov = coverage_map(req, team)
    return {
        "team": chosen,
        "covered": sum(1 for ids in cov.values() if ids),
        "total": len(req),
        "missing": [s for s, ids in cov.items() if not ids],
        "categories": sorted(categories([s for m in team for s in m["skills"]])),
    }


def _join(items):
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]
