"""Skill taxonomy: canonical names, categories and aliases.

Normalising free-text skills ("ml", "ui/ux", "reactjs") to canonical names lets the
matcher compare students and projects reliably. Categories give *partial* credit when a
student has a related skill (e.g. Flask vs Django) even if it is not an exact match.
"""
import re

CATEGORIES = {
    "Programming": ["Python", "Java", "JavaScript", "TypeScript", "C", "C++", "Go", "Rust", "Dart", "Kotlin", "Swift", "R"],
    "AI & Data": ["Machine Learning", "Deep Learning", "Natural Language Processing", "Computer Vision",
                  "Artificial Intelligence", "Data Analysis", "Data Visualization", "Statistics",
                  "TensorFlow", "PyTorch", "Pandas"],
    "Web": ["Web Development", "HTML/CSS", "React", "Vue", "Next.js", "Node.js", "Django", "Flask",
            "REST APIs", "Tailwind CSS"],
    "Databases": ["Databases", "SQL", "PostgreSQL", "MySQL", "MongoDB", "Firebase", "System Design"],
    "Design": ["UI/UX Design", "Figma", "Graphic Design", "Prototyping", "User Research"],
    "Mobile": ["Flutter", "Android", "iOS", "React Native"],
    "Cloud & DevOps": ["Docker", "AWS", "Linux", "Git", "CI/CD", "Cloud Computing", "Kubernetes"],
    "Hardware": ["IoT", "Arduino", "Embedded Systems", "Robotics", "Raspberry Pi"],
    "Product & Communication": ["Project Management", "Technical Writing", "Presentation", "Marketing", "Public Speaking"],
}

ALIASES = {
    "ml": "Machine Learning", "machine-learning": "Machine Learning",
    "dl": "Deep Learning", "nlp": "Natural Language Processing",
    "cv": "Computer Vision", "ai": "Artificial Intelligence",
    "data science": "Data Analysis", "data analytics": "Data Analysis", "analytics": "Data Analysis",
    "dataviz": "Data Visualization", "data viz": "Data Visualization", "visualization": "Data Visualization",
    "tf": "TensorFlow", "torch": "PyTorch",
    "py": "Python", "python3": "Python", "js": "JavaScript", "ts": "TypeScript", "cpp": "C++",
    "golang": "Go", "node": "Node.js", "nodejs": "Node.js", "node js": "Node.js",
    "reactjs": "React", "react.js": "React", "vuejs": "Vue", "vue.js": "Vue", "nextjs": "Next.js",
    "html": "HTML/CSS", "css": "HTML/CSS", "html5": "HTML/CSS", "html/css": "HTML/CSS", "html & css": "HTML/CSS",
    "web dev": "Web Development", "frontend": "Web Development", "front-end": "Web Development",
    "backend": "Web Development", "full stack": "Web Development", "fullstack": "Web Development",
    "rest": "REST APIs", "rest api": "REST APIs", "api": "REST APIs", "apis": "REST APIs",
    "db": "Databases", "database": "Databases", "dbms": "Databases", "postgres": "PostgreSQL",
    "mongo": "MongoDB", "mongo db": "MongoDB",
    "ui": "UI/UX Design", "ux": "UI/UX Design", "ui/ux": "UI/UX Design", "ui ux": "UI/UX Design",
    "ux design": "UI/UX Design", "ui design": "UI/UX Design", "design": "UI/UX Design",
    "wireframing": "Prototyping", "user testing": "User Research",
    "graphics": "Graphic Design", "photoshop": "Graphic Design",
    "app development": "Flutter", "mobile development": "Android",
    "ci": "CI/CD", "cicd": "CI/CD", "devops": "CI/CD", "cloud": "Cloud Computing",
    "amazon web services": "AWS", "k8s": "Kubernetes", "github": "Git",
    "embedded": "Embedded Systems", "internet of things": "IoT", "rpi": "Raspberry Pi",
    "pm": "Project Management", "management": "Project Management", "writing": "Technical Writing",
    "slides": "Presentation", "public-speaking": "Public Speaking",
}

DOMAINS = ["AI", "Healthcare", "Education", "Fintech", "Sustainability", "IoT", "Robotics", "Mobile",
           "Web apps", "Cloud", "Open source", "Social impact", "E-commerce", "Gaming", "Data science",
           "Design", "Language", "Mental health"]

_CANON = {}
_CATEGORY = {}
for _cat, _names in CATEGORIES.items():
    for _n in _names:
        _CANON[_n.lower()] = _n
        _CATEGORY[_n] = _cat


def normalize_skill(raw):
    key = re.sub(r"\s+", " ", str(raw).strip().lower())
    if not key:
        return None
    if key in _CANON:
        return _CANON[key]
    if key in ALIASES:
        return ALIASES[key]
    return " ".join(w.capitalize() if w.islower() else w for w in str(raw).strip().split())


def normalize_skills(items):
    seen, out = set(), []
    for raw in items or []:
        s = normalize_skill(raw)
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def normalize_tags(items):
    seen, out = set(), []
    for raw in items or []:
        t = re.sub(r"\s+", " ", str(raw).strip())
        if t and t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
    return out


def category_of(skill):
    return _CATEGORY.get(skill, "Other")


def catalog():
    return [{"name": n, "category": c} for n, c in sorted(_CATEGORY.items(), key=lambda x: (x[1], x[0]))]
