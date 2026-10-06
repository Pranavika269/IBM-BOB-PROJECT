"""ProjectMatch: Flask API + single-page front end.

Run:  python app.py        then open http://127.0.0.1:5000
"""
import json
import os
import re
import sqlite3

from flask import Flask, current_app, g, jsonify, request, send_from_directory

import matching
import skills as sk
from seed import seed_db

BASE = os.path.dirname(os.path.abspath(__file__))

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  major TEXT DEFAULT '',
  year TEXT DEFAULT '',
  bio TEXT DEFAULT '',
  skills TEXT NOT NULL DEFAULT '[]',
  interests TEXT NOT NULL DEFAULT '[]',
  experience TEXT NOT NULL DEFAULT 'beginner',
  hours_per_week INTEGER NOT NULL DEFAULT 5
);
CREATE TABLE IF NOT EXISTS projects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  owner_id INTEGER NOT NULL REFERENCES students(id),
  required_skills TEXT NOT NULL DEFAULT '[]',
  domains TEXT NOT NULL DEFAULT '[]',
  team_size INTEGER NOT NULL DEFAULT 4,
  hours_per_week INTEGER NOT NULL DEFAULT 6,
  level TEXT NOT NULL DEFAULT 'intermediate'
);
CREATE TABLE IF NOT EXISTS members (
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  role TEXT NOT NULL DEFAULT 'Member',
  joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (project_id, student_id)
);
"""


class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message, self.status = message, status


# ------------------------------------------------------------------ database
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DB_PATH"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def student_dict(r):
    return {"id": r["id"], "name": r["name"], "email": r["email"], "major": r["major"], "year": r["year"],
            "bio": r["bio"], "skills": json.loads(r["skills"]), "interests": json.loads(r["interests"]),
            "experience": r["experience"], "hours_per_week": r["hours_per_week"]}


def project_dict(r):
    return {"id": r["id"], "title": r["title"], "description": r["description"], "owner_id": r["owner_id"],
            "required_skills": json.loads(r["required_skills"]), "domains": json.loads(r["domains"]),
            "team_size": r["team_size"], "hours_per_week": r["hours_per_week"], "level": r["level"]}


def all_students(db):
    return [student_dict(r) for r in db.execute("SELECT * FROM students ORDER BY id")]


def all_projects(db):
    return [project_dict(r) for r in db.execute("SELECT * FROM projects ORDER BY id")]


def members_map(db):
    out = {}
    rows = db.execute("""SELECT m.project_id, m.role, s.* FROM members m JOIN students s ON s.id = m.student_id
                         ORDER BY m.joined_at, s.id""")
    for r in rows:
        out.setdefault(r["project_id"], []).append({**student_dict(r), "role": r["role"]})
    return out


def get_student(db, sid):
    r = db.execute("SELECT * FROM students WHERE id=?", (sid,)).fetchone()
    if not r:
        raise ApiError("Student not found", 404)
    return student_dict(r)


def get_project(db, pid):
    r = db.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
    if not r:
        raise ApiError("Project not found", 404)
    return project_dict(r)


def slim(m):
    return {"id": m["id"], "name": m["name"], "role": m.get("role", "Member")}


# ------------------------------------------------------------------ validation
def clean_student(data):
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    if not name:
        raise ApiError("Enter your name.")
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise ApiError("Enter a valid email address.")
    skills = sk.normalize_skills(data.get("skills"))
    if not skills:
        raise ApiError("Add at least one skill so we can find matches.")
    level = str(data.get("experience", "beginner")).lower()
    if level not in matching.LEVELS:
        raise ApiError("Experience must be beginner, intermediate or advanced.")
    try:
        hours = int(data.get("hours_per_week", 5))
    except (TypeError, ValueError):
        raise ApiError("Hours per week must be a number.")
    if not 1 <= hours <= 40:
        raise ApiError("Hours per week must be between 1 and 40.")
    return {"name": name, "email": email, "major": str(data.get("major", "")).strip(),
            "year": str(data.get("year", "")).strip(), "bio": str(data.get("bio", "")).strip(),
            "skills": skills, "interests": sk.normalize_tags(data.get("interests")),
            "experience": level, "hours_per_week": hours}


def clean_project(data):
    title = str(data.get("title", "")).strip()
    desc = str(data.get("description", "")).strip()
    if not title:
        raise ApiError("Give the project a title.")
    if len(desc) < 20:
        raise ApiError("Describe the project in at least a sentence or two (20+ characters).")
    req = sk.normalize_skills(data.get("required_skills"))
    if not req:
        raise ApiError("List at least one skill the project needs.")
    level = str(data.get("level", "intermediate")).lower()
    if level not in matching.LEVELS:
        raise ApiError("Level must be beginner, intermediate or advanced.")
    try:
        size, hours = int(data.get("team_size", 4)), int(data.get("hours_per_week", 6))
    except (TypeError, ValueError):
        raise ApiError("Team size and hours per week must be numbers.")
    if not 2 <= size <= 10:
        raise ApiError("Team size must be between 2 and 10.")
    if not 1 <= hours <= 40:
        raise ApiError("Hours per week must be between 1 and 40.")
    return {"title": title, "description": desc, "required_skills": req,
            "domains": sk.normalize_tags(data.get("domains")), "team_size": size,
            "hours_per_week": hours, "level": level}


# ------------------------------------------------------------------ app factory
def create_app(db_path=None, seed=True):
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config["DB_PATH"] = db_path or os.environ.get("PM_DB", os.path.join(BASE, "projectmatch.db"))

    with sqlite3.connect(app.config["DB_PATH"]) as con:
        con.row_factory = sqlite3.Row
        con.executescript(SCHEMA)
        if seed and con.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0:
            seed_db(con)

    @app.teardown_appcontext
    def close_db(_):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.errorhandler(ApiError)
    def api_error(e):
        return jsonify({"error": e.message}), e.status

    @app.route("/")
    def index():
        return send_from_directory(os.path.join(BASE, "templates"), "index.html")

    # ---- reference data
    @app.get("/api/skills")
    def skills_catalog():
        return jsonify({"skills": sk.catalog(), "domains": sk.DOMAINS})

    # ---- students
    @app.get("/api/students")
    def list_students():
        return jsonify(all_students(get_db()))

    @app.get("/api/students/<int:sid>")
    def read_student(sid):
        return jsonify(get_student(get_db(), sid))

    @app.post("/api/students")
    def create_student():
        db, d = get_db(), clean_student(request.get_json(silent=True) or {})
        try:
            cur = db.execute(
                "INSERT INTO students(name,email,major,year,bio,skills,interests,experience,hours_per_week) VALUES (?,?,?,?,?,?,?,?,?)",
                (d["name"], d["email"], d["major"], d["year"], d["bio"], json.dumps(d["skills"]),
                 json.dumps(d["interests"]), d["experience"], d["hours_per_week"]))
        except sqlite3.IntegrityError:
            raise ApiError("A profile with that email already exists. Pick it from the menu instead.", 409)
        db.commit()
        return jsonify(get_student(db, cur.lastrowid)), 201

    @app.put("/api/students/<int:sid>")
    def update_student(sid):
        db = get_db()
        get_student(db, sid)
        d = clean_student(request.get_json(silent=True) or {})
        try:
            db.execute("""UPDATE students SET name=?,email=?,major=?,year=?,bio=?,skills=?,interests=?,
                          experience=?,hours_per_week=? WHERE id=?""",
                       (d["name"], d["email"], d["major"], d["year"], d["bio"], json.dumps(d["skills"]),
                        json.dumps(d["interests"]), d["experience"], d["hours_per_week"], sid))
        except sqlite3.IntegrityError:
            raise ApiError("Another profile already uses that email.", 409)
        db.commit()
        return jsonify(get_student(db, sid))

    @app.get("/api/students/<int:sid>/recommendations")
    def recommend_projects(sid):
        """Projects ranked for a student."""
        db = get_db()
        me = get_student(db, sid)
        students, projects, mm = all_students(db), all_projects(db), members_map(db)
        model = matching.build_model(students, projects)
        out = []
        for p in projects:
            members = mm.get(p["id"], [])
            is_member = any(m["id"] == sid for m in members)
            full = len(members) >= p["team_size"]
            cov = matching.coverage_map(p["required_skills"], members)
            out.append({**p, "match": matching.score_project(me, p, model),
                        "members": [slim(m) for m in members], "is_member": is_member, "is_full": full,
                        "open_spots": max(0, p["team_size"] - len(members)),
                        "covered_count": sum(1 for ids in cov.values() if ids)})
        out.sort(key=lambda x: (x["is_member"] or (x["is_full"]), -x["match"]["score"]))
        return jsonify(out)

    # ---- projects
    @app.get("/api/projects")
    def list_projects():
        db = get_db()
        mm = members_map(db)
        return jsonify([{**p, "members": [slim(m) for m in mm.get(p["id"], [])]} for p in all_projects(db)])

    @app.post("/api/projects")
    def create_project():
        db, data = get_db(), request.get_json(silent=True) or {}
        owner = get_student(db, int(data.get("owner_id") or 0))
        d = clean_project(data)
        cur = db.execute(
            "INSERT INTO projects(title,description,owner_id,required_skills,domains,team_size,hours_per_week,level) VALUES (?,?,?,?,?,?,?,?)",
            (d["title"], d["description"], owner["id"], json.dumps(d["required_skills"]), json.dumps(d["domains"]),
             d["team_size"], d["hours_per_week"], d["level"]))
        db.execute("INSERT INTO members(project_id,student_id,role) VALUES (?,?,'Owner')", (cur.lastrowid, owner["id"]))
        db.commit()
        return jsonify(get_project(db, cur.lastrowid)), 201

    @app.get("/api/projects/<int:pid>")
    def read_project(pid):
        db = get_db()
        p = get_project(db, pid)
        members = members_map(db).get(pid, [])
        cov = matching.coverage_map(p["required_skills"], members)
        out = {**p, "members": members, "open_spots": max(0, p["team_size"] - len(members)),
               "owner": next((slim(m) for m in members if m["role"] == "Owner"), None),
               "coverage": [{"skill": s, "category": sk.category_of(s), "covered_by": ids} for s, ids in cov.items()],
               "covered_count": sum(1 for ids in cov.values() if ids)}
        viewer = request.args.get("student_id", type=int)
        if viewer:
            me = get_student(db, viewer)
            model = matching.build_model(all_students(db), all_projects(db))
            out["match"] = matching.score_project(me, p, model)
            out["is_member"] = any(m["id"] == viewer for m in members)
            out["viewer_skills"] = me["skills"]
        return jsonify(out)

    @app.get("/api/projects/<int:pid>/teammates")
    def recommend_teammates(pid):
        """Students ranked by how well they fill the project's remaining skill gaps."""
        db = get_db()
        p = get_project(db, pid)
        members = members_map(db).get(pid, [])
        ids = {m["id"] for m in members}
        students = all_students(db)
        model = matching.build_model(students, all_projects(db))
        out = []
        for s in students:
            if s["id"] in ids:
                continue
            out.append({**s, "fit": matching.candidate_fit(s, p, members, model)})
        out.sort(key=lambda x: -x["fit"]["score"])
        limit = request.args.get("limit", 8, type=int)
        return jsonify(out[:limit])

    @app.post("/api/projects/<int:pid>/suggest-team")
    def suggest_team(pid):
        """Greedy, balance-aware suggestion for the remaining open spots."""
        db = get_db()
        p = get_project(db, pid)
        members = members_map(db).get(pid, [])
        ids = {m["id"] for m in members}
        students = all_students(db)
        model = matching.build_model(students, all_projects(db))
        slots = max(0, p["team_size"] - len(members))
        result = matching.suggest_team(p, members, [s for s in students if s["id"] not in ids], slots, model)
        result["open_spots"] = slots
        return jsonify(result)

    # ---- team formation
    @app.post("/api/projects/<int:pid>/members")
    def add_member(pid):
        db = get_db()
        p = get_project(db, pid)
        sid = (request.get_json(silent=True) or {}).get("student_id")
        s = get_student(db, int(sid or 0))
        n = db.execute("SELECT COUNT(*) FROM members WHERE project_id=?", (pid,)).fetchone()[0]
        if db.execute("SELECT 1 FROM members WHERE project_id=? AND student_id=?", (pid, s["id"])).fetchone():
            raise ApiError(f"{s['name']} is already on this team.", 409)
        if n >= p["team_size"]:
            raise ApiError("This team is full.", 409)
        db.execute("INSERT INTO members(project_id,student_id,role) VALUES (?,?,'Member')", (pid, s["id"]))
        db.commit()
        return jsonify({"ok": True, "student": s["name"]}), 201

    @app.delete("/api/projects/<int:pid>/members/<int:sid>")
    def remove_member(pid, sid):
        db = get_db()
        get_project(db, pid)
        row = db.execute("SELECT role FROM members WHERE project_id=? AND student_id=?", (pid, sid)).fetchone()
        if not row:
            raise ApiError("That student is not on this team.", 404)
        if row["role"] == "Owner":
            raise ApiError("The project owner can't leave their own team.", 409)
        db.execute("DELETE FROM members WHERE project_id=? AND student_id=?", (pid, sid))
        db.commit()
        return jsonify({"ok": True})

    return app


if __name__ == "__main__":
    create_app().run(debug=True, port=int(os.environ.get("PORT", 5000)))
