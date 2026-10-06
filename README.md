# ProjectMatch

An AI-assisted platform that matches students to projects and teammates based on skills, interests,
experience and availability, then helps them form balanced teams.

```
Student profile -> Matching engine -> Recommended projects & teammates -> Team formation
```

## Run it

Requires Python 3.9+.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000. The database (`projectmatch.db`, SQLite) is created on first run and filled with
12 demo students and 6 demo projects. Delete the file to reset. Run the tests with
`python -m unittest discover -s tests -v`.

## What you can do

- **Discover**: see every project ranked for the selected student, with a match score and the reasons behind it.
- **Skill coverage board**: each project's required skills appear as slots that fill as teammates join.
- **Recommended teammates**: ranked by how many of the *missing* skills they bring, plus interests and time.
- **Suggest a balanced team**: one click picks the people who close the most gaps and adds variety.
- **Join / add / leave**: simple team formation. The owner can't leave their own project.
- **Post a project** and **edit your profile** (or create a new one). Use the "Signed in as" menu to switch demo users.

## How matching works (`matching.py`)

Student -> project fit:

| Signal | Weight | How it's measured |
|---|---|---|
| Skills | 45% | Exact skill = 1.0, same-category skill = 0.4 (e.g. Flask vs Django). Capped so nobody needs *every* skill, because teammates fill the rest. |
| Interests | 25% | Overlap with project topics, blended with TF-IDF cosine similarity between your bio/interests and the project text. |
| Time | 15% | Your weekly hours vs hours the project needs. |
| Experience | 15% | Closeness of your level to the project level. A stretch scores lower than a comfortable fit. |

Project -> teammate fit: 55% gap-filling skills, 20% interests, 15% time, 10% variety (new skill categories for the team).
The balanced-team suggestion is a greedy algorithm that repeatedly adds the person with the biggest marginal skill coverage.

Skills are normalised through `skills.py` ("ml" -> Machine Learning, "ui/ux" -> UI/UX Design), so free-text input still matches.

## Project layout

```
app.py          Flask API, SQLite schema, validation
matching.py     Scoring, TF-IDF, team suggestion
skills.py       Skill taxonomy, categories, aliases
seed.py         Demo students and projects
templates/      index.html (single page)
static/         css/style.css, js/app.js (vanilla JS, no build step)
tests/          API and matching tests
```

## API

| Method | Path | Purpose |
|---|---|---|
| GET/POST | `/api/students` | List / create profiles |
| GET/PUT | `/api/students/<id>` | Read / update a profile |
| GET | `/api/students/<id>/recommendations` | Ranked projects with score breakdown |
| GET/POST | `/api/projects` | List / post projects |
| GET | `/api/projects/<id>?student_id=` | Detail, skill coverage, match for a viewer |
| GET | `/api/projects/<id>/teammates` | Ranked candidate teammates |
| POST | `/api/projects/<id>/suggest-team` | Balanced team for the open spots |
| POST/DELETE | `/api/projects/<id>/members[/<student_id>]` | Join, add or leave a team |

## Known limits and next steps

This is an MVP. There is **no login**: anyone can act as any student (the profile menu is for demos), and adding
a teammate is immediate rather than an invite they accept. Before real use, add:

1. Authentication (e.g. university SSO) and invite / request-to-join with accept and decline.
2. Sentence embeddings (e.g. `sentence-transformers`) in place of TF-IDF for deeper interest matching.
3. Availability by time slot instead of hours per week, plus notifications and team chat.
4. PostgreSQL and a production server (`gunicorn`) instead of SQLite and Flask's dev server.
