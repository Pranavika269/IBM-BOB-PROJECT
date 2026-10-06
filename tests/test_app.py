import os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import create_app
import matching
from skills import normalize_skills


class MatchingTests(unittest.TestCase):
    def test_aliases(self):
        self.assertEqual(normalize_skills(["ml", "UI/UX", "reactjs", "Python", "python"]),
                         ["Machine Learning", "UI/UX Design", "React", "Python"])


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.client = create_app(self.tmp.name).test_client()

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_python_ml_student_gets_ai_project_first(self):
        recs = self.client.get("/api/students/1/recommendations").get_json()  # Aarav: Python + ML
        open_recs = [r for r in recs if not r["is_member"] and not r["is_full"]]
        self.assertIn("Diabetic", open_recs[0]["title"])
        self.assertGreater(open_recs[0]["match"]["score"], open_recs[-1]["match"]["score"])

    def test_teammates_fill_gaps(self):
        mates = self.client.get("/api/projects/1/teammates").get_json()  # Retinopathy needs React, UI/UX, Databases
        top_fills = set(sum([m["fit"]["fills"] for m in mates[:3]], []))
        self.assertTrue(top_fills & {"React", "UI/UX Design", "Databases"})
        self.assertNotIn(6, [m["id"] for m in mates])  # owner is not suggested

    def test_suggest_and_join_flow(self):
        r = self.client.post("/api/projects/1/suggest-team").get_json()
        self.assertEqual(len(r["team"]), 4)
        self.assertGreaterEqual(r["covered"], 5)
        for s in r["team"]:
            self.assertEqual(self.client.post("/api/projects/1/members", json={"student_id": s["id"]}).status_code, 201)
        full = self.client.post("/api/projects/1/members", json={"student_id": 11})
        self.assertEqual(full.status_code, 409)

    def test_owner_cannot_leave_and_validation(self):
        self.assertEqual(self.client.delete("/api/projects/1/members/6").status_code, 409)
        bad = self.client.post("/api/students", json={"name": "X", "email": "nope", "skills": ["Python"]})
        self.assertEqual(bad.status_code, 400)

    def test_create_profile_and_project(self):
        s = self.client.post("/api/students", json={"name": "Zoe", "email": "zoe@campus.edu", "skills": ["py", "ml"],
                             "interests": ["AI"], "experience": "beginner", "hours_per_week": 6})
        self.assertEqual(s.status_code, 201)
        self.assertEqual(s.get_json()["skills"], ["Python", "Machine Learning"])
        p = self.client.post("/api/projects", json={"owner_id": s.get_json()["id"], "title": "Test", "description": "A project long enough to pass.",
                             "required_skills": ["python", "figma"], "team_size": 3})
        self.assertEqual(p.status_code, 201)
        detail = self.client.get(f"/api/projects/{p.get_json()['id']}?student_id=1").get_json()
        self.assertEqual(len(detail["members"]), 1)


if __name__ == "__main__":
    unittest.main()
