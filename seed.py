"""Demo data so the app is useful on first launch."""
import json

STUDENTS = [
    ("Aarav Menon", "aarav@campus.edu", "Computer Science", "3rd year", "I like turning messy health data into models that help clinicians.",
     ["Python", "Machine Learning", "Pandas", "SQL"], ["AI", "Healthcare", "Data science"], "intermediate", 10),
    ("Priya Raman", "priya@campus.edu", "Information Technology", "3rd year", "Front-end developer who enjoys building clean web apps for students.",
     ["React", "JavaScript", "HTML/CSS", "Node.js"], ["Web apps", "Education", "Fintech"], "intermediate", 8),
    ("Karthik S", "karthik@campus.edu", "Design", "2nd year", "I research how people actually use apps and design flows that make sense.",
     ["UI/UX Design", "Figma", "User Research", "Prototyping"], ["Design", "Education", "Healthcare"], "intermediate", 8),
    ("Meera Iyer", "meera@campus.edu", "Computer Science", "4th year", "Backend and database person. I like schemas, APIs and making things fast.",
     ["Databases", "SQL", "PostgreSQL", "Python", "Flask"], ["Fintech", "Data science", "Web apps"], "advanced", 6),
    ("Rohan Das", "rohan@campus.edu", "Computer Science", "2nd year", "Learning mobile development and keen to build apps that help people.",
     ["Flutter", "Android", "Firebase", "Dart"], ["Mobile", "Social impact", "Mental health"], "beginner", 12),
    ("Sana Khan", "sana@campus.edu", "AI & Data Science", "4th year", "Computer vision for medical imaging and robotics.",
     ["Deep Learning", "PyTorch", "Computer Vision", "Python"], ["AI", "Robotics", "Healthcare"], "advanced", 10),
    ("Dev Patel", "dev@campus.edu", "Electronics", "3rd year", "Sensors, microcontrollers and anything that blinks.",
     ["Arduino", "IoT", "Embedded Systems", "C++"], ["IoT", "Sustainability", "Robotics"], "intermediate", 10),
    ("Ananya Krishnan", "ananya@campus.edu", "Linguistics & CS", "3rd year", "Language technology for education, plus I write clear documentation.",
     ["Natural Language Processing", "Python", "Data Analysis", "Technical Writing"], ["AI", "Education", "Language"], "intermediate", 6),
    ("Lucas Meyer", "lucas@campus.edu", "Computer Science", "4th year", "Exchange student. Infrastructure, automation and open source.",
     ["Docker", "AWS", "Linux", "Git", "CI/CD"], ["Cloud", "Open source"], "advanced", 5),
    ("Isha Verma", "isha@campus.edu", "Visual Communication", "2nd year", "Graphic designer learning to code. Posters, brand and presentations.",
     ["Graphic Design", "Figma", "HTML/CSS", "Presentation"], ["Design", "Social impact", "Education"], "beginner", 10),
    ("Tarun Reddy", "tarun@campus.edu", "Computer Science", "1st year", "Starting out with web development and hungry to join a real team.",
     ["JavaScript", "Vue", "Node.js", "MongoDB", "REST APIs"], ["Web apps", "Fintech", "E-commerce"], "beginner", 12),
    ("Nisha Joseph", "nisha@campus.edu", "Statistics", "3rd year", "I keep teams on track and turn numbers into charts people understand.",
     ["Project Management", "Data Visualization", "Statistics", "Python"], ["Sustainability", "Data science", "Healthcare"], "intermediate", 6),
]

# title, description, owner index (1-based), required, domains, team_size, hours, level, extra member indexes
PROJECTS = [
    ("Diabetic Retinopathy Screener",
     "A model that flags early signs of diabetic retinopathy in retinal photos, wrapped in a simple web app clinics can use to upload scans and review results.",
     6, ["Deep Learning", "Computer Vision", "Python", "React", "UI/UX Design", "Databases"], ["AI", "Healthcare"], 5, 8, "advanced", []),
    ("Campus Study-Buddy Chatbot",
     "A chatbot that answers course questions from lecture notes and suggests study partners. Needs language processing, a clean chat interface and a place to store notes.",
     8, ["Natural Language Processing", "Python", "Flask", "UI/UX Design", "Databases"], ["AI", "Education"], 4, 6, "intermediate", [1]),
    ("Smart Water Usage Monitor",
     "Low-cost sensors that track water use in hostels, send readings to the cloud and show a live dashboard with leak alerts.",
     7, ["IoT", "Arduino", "Flutter", "Data Visualization", "AWS"], ["Sustainability", "IoT"], 4, 8, "intermediate", [12]),
    ("Split-It: Group Expense Tracker",
     "A web app for roommates and trip groups to log shared expenses, see who owes whom and settle up in one tap.",
     2, ["React", "Node.js", "MongoDB", "UI/UX Design"], ["Fintech", "Web apps"], 3, 6, "beginner", [11]),
    ("Open-Source CI Dashboard",
     "A dashboard that pulls build and test results from many repositories and shows flaky tests, build times and deploy history.",
     9, ["Docker", "CI/CD", "React", "REST APIs", "Data Visualization"], ["Open source", "Cloud"], 3, 5, "intermediate", []),
    ("Mood-Lift: Student Wellness App",
     "A mobile app for daily mood check-ins that uses gentle language analysis to suggest breathing exercises and campus counselling resources.",
     5, ["Flutter", "Firebase", "UI/UX Design", "Natural Language Processing"], ["Mental health", "Mobile", "Healthcare"], 4, 10, "beginner", []),
]


def seed_db(db):
    for n, e, major, yr, bio, skills, interests, exp, hrs in STUDENTS:
        db.execute(
            "INSERT INTO students(name,email,major,year,bio,skills,interests,experience,hours_per_week) VALUES (?,?,?,?,?,?,?,?,?)",
            (n, e, major, yr, bio, json.dumps(skills), json.dumps(interests), exp, hrs))
    for t, d, owner, req, doms, size, hrs, lvl, extra in PROJECTS:
        cur = db.execute(
            "INSERT INTO projects(title,description,owner_id,required_skills,domains,team_size,hours_per_week,level) VALUES (?,?,?,?,?,?,?,?)",
            (t, d, owner, json.dumps(req), json.dumps(doms), size, hrs, lvl))
        pid = cur.lastrowid
        db.execute("INSERT INTO members(project_id,student_id,role) VALUES (?,?,?)", (pid, owner, "Owner"))
        for sid in extra:
            db.execute("INSERT INTO members(project_id,student_id,role) VALUES (?,?,?)", (pid, sid, "Member"))
    db.commit()
