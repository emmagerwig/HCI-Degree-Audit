"""
degree_audit_api.py

A mock backend that serves degree audit data over HTTP, built with FastAPI.

Run with:
    pip install fastapi uvicorn
    python degree_audit_api.py

API is available at http://localhost:8002

Endpoints:
    GET  /program
    GET  /requirements
    GET  /requirements/{req_id}
    GET  /requirements/{req_id}/courses
    GET  /progress
    POST /plan/add      body: {"req_id": int, "code": str}
    POST /plan/remove   body: {"req_id": int, "code": str}
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Degree Audit API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------
# In-memory "database"
# ---------------------------------------------------------------------

PROGRAM = {
    "student": "Kacey Musgraves",
    "major": "B.S. Computer Science",
    "catalog_year": "2024-2025",
    "advisor": "Prof. Parton",
    "total_credits_required": 120,
    "total_credits_completed": 78,
}

REQUIREMENTS = [
    {
        "id": 1,
        "name": "Core CS Requirements",
        "credits_required": 36,
        "courses": [
            {"code": "CS 101", "title": "Intro to Programming", "credits": 4, "status": "completed"},
            {"code": "CS 212", "title": "Data Structures & Algorithms", "credits": 4, "status": "in_progress"},
            {"code": "CS 250", "title": "Computer Systems", "credits": 4, "status": "completed"},
            {"code": "CS 301", "title": "Algorithms", "credits": 4, "status": "needed"},
            {"code": "CS 340", "title": "Human-Computer Interaction", "credits": 4, "status": "in_progress"},
            {"code": "CS 401", "title": "Software Engineering", "credits": 4, "status": "planned"},
            {"code": "CS 410", "title": "Operating Systems", "credits": 4, "status": "needed"},
            {"code": "CS 420", "title": "Senior Capstone", "credits": 4, "status": "needed"},
            {"code": "CS 150", "title": "Discrete Math for CS", "credits": 4, "status": "completed"},
        ],
    },
    {
        "id": 2,
        "name": "Math & Science",
        "credits_required": 20,
        "courses": [
            {"code": "MATH 151", "title": "Calculus I", "credits": 4, "status": "completed"},
            {"code": "MATH 152", "title": "Calculus II", "credits": 4, "status": "completed"},
            {"code": "MATH 220", "title": "Linear Algebra", "credits": 4, "status": "completed"},
            {"code": "STAT 210", "title": "Probability & Statistics", "credits": 4, "status": "completed"},
            {"code": "PHYS 101", "title": "Physics I", "credits": 4, "status": "completed"},
        ],
    },
    {
        "id": 3,
        "name": "General Education",
        "credits_required": 32,
        "courses": [
            {"code": "ENGL 150", "title": "Technical Writing", "credits": 4, "status": "in_progress"},
            {"code": "HIST 101", "title": "World History", "credits": 4, "status": "completed"},
            {"code": "PHIL 110", "title": "Intro to Ethics", "credits": 4, "status": "completed"},
            {"code": "ART 105", "title": "Art Appreciation", "credits": 4, "status": "completed"},
            {"code": "COMM 130", "title": "Public Speaking", "credits": 4, "status": "completed"},
            {"code": "SOC 101", "title": "Intro to Sociology", "credits": 4, "status": "completed"},
            {"code": "LANG 201", "title": "Intermediate Spanish", "credits": 4, "status": "planned"},
            {"code": "ENV 100", "title": "Environmental Science", "credits": 4, "status": "needed"},
        ],
    },
    {
        "id": 4,
        "name": "Free Electives",
        "credits_required": 32,
        "courses": [
            {"code": "MUS 110", "title": "Intro to Music", "credits": 3, "status": "completed"},
            {"code": "BUS 200", "title": "Intro to Business", "credits": 4, "status": "completed"},
            {"code": "CS 495", "title": "Independent Study", "credits": 4, "status": "planned"},
            {"code": "PSY 101", "title": "Intro to Psychology", "credits": 4, "status": "needed"},
        ],
    },
]


# ---------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------

class PlanAction(BaseModel):
    req_id: int
    code: str

def _get_requirement_or_404(req_id: int) -> dict:
    for r in REQUIREMENTS:
        if r["id"] == req_id:
            return r
    raise HTTPException(status_code=404, detail="Requirement category not found")

def _get_course_or_404(req: dict, code: str) -> dict:
    for c in req["courses"]:
        if c["code"] == code:
            return c
    raise HTTPException(status_code=404, detail="Course not found in this requirement")

def _credits_by_status(courses: list, status: str) -> int:
    return sum(c["credits"] for c in courses if c["status"] == status)

def _summarize(req: dict) -> dict:
    summary = dict(req)
    summary["credits_completed"] = _credits_by_status(req["courses"], "completed")
    summary["credits_in_progress"] = _credits_by_status(req["courses"], "in_progress")
    summary["credits_planned"] = _credits_by_status(req["courses"], "planned")
    return summary

@app.get("/program")
def get_program():
    return PROGRAM

@app.get("/requirements")
def list_requirements():
    return [_summarize(r) for r in REQUIREMENTS]

@app.get("/requirements/{req_id}")
def get_requirement(req_id: int):
    return _summarize(_get_requirement_or_404(req_id))

@app.get("/requirements/{req_id}/courses")
def get_requirement_courses(req_id: int):
    req = _get_requirement_or_404(req_id)
    return req["courses"]

@app.get("/progress")
def get_progress():
    total_required = sum(r["credits_required"] for r in REQUIREMENTS)
    all_courses = [c for r in REQUIREMENTS for c in r["courses"]]
    completed = _credits_by_status(all_courses, "completed")
    in_progress = _credits_by_status(all_courses, "in_progress")
    planned = _credits_by_status(all_courses, "planned")
    projected = completed + in_progress + planned
    return {
        "total_credits_required": total_required,
        "total_credits_completed": completed,
        "total_credits_projected": projected,
        "percent_complete": round(100 * completed / total_required, 1),
        "percent_projected": round(100 * projected / total_required, 1),
    }

@app.post("/plan/add")
def add_to_plan(action: PlanAction):
    req = _get_requirement_or_404(action.req_id)
    course = _get_course_or_404(req, action.code)
    if course["status"] != "needed":
        raise HTTPException(status_code=400, detail="Course is not available to add to plan")
    course["status"] = "planned"
    return course

@app.post("/plan/remove")
def remove_from_plan(action: PlanAction):
    req = _get_requirement_or_404(action.req_id)
    course = _get_course_or_404(req, action.code)
    if course["status"] != "planned":
        raise HTTPException(status_code=400, detail="Course is not currently planned")
    course["status"] = "needed"
    return course

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)