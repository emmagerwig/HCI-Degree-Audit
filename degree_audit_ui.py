"""
degree_audit_ui.py

A simple NiceGUI frontend that pulls data from
degree_audit_api.py and renders a basic degree audit view.

Run with:
    pip install nicegui requests
    python degree_audit_api.py     # in one terminal
    python degree_audit_ui.py      # in another terminal

Then http://localhost:8081 will automatically open.
"""

import requests
from nicegui import ui

API_BASE = "http://localhost:8002"

STATUS_LABELS = {
    "completed": "Completed",
    "in_progress": "In Progress",
    "planned": "Planned",
    "needed": "Needed",
}

STATUS_COLORS = {
    "completed": "text-green-700",
    "in_progress": "text-blue-700",
    "planned": "text-amber-500",
    "needed": "text-red-700"
}

state = {"plan_mode": True}


def api_get(path: str):
    try:
        resp = requests.get(f"{API_BASE}{path}", timeout=5)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        ui.notify(f"Could not reach API: {e}", type="negative")
        return {}

def api_post(path: str, json: dict):
    try:
        resp = requests.post(f"{API_BASE}{path}", json=json, timeout=5)
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        detail = ""
        try:
            detail = e.response.json().get("detail", "")
        except Exception:
            pass
        ui.notify(detail or f"Request failed: {e}", type="negative")
        return False

def add_to_plan(req_id: int, code: str):
    if api_post("/plan/add", {"req_id": req_id, "code": code}):
        render_audit.refresh()

def remove_from_plan(req_id: int, code: str):
    if api_post("/plan/remove", {"req_id": req_id, "code": code}):
        render_audit.refresh()

@ui.page("/")
def main_page():
    render_audit()

@ui.refreshable
def render_audit():
    program = api_get("/program")
    progress = api_get("/progress")
    requirements = api_get("/requirements")

    ui.label(f'{program.get("major", "")}').classes("text-2xl")
    ui.label(
        f'{program.get("student", "")} | Catalog {program.get("catalog_year", "")} '
        f'| Advisor: {program.get("advisor", "")}'
    )
    percent_complete = progress.get("percent_complete", 0)
    percent_projected = progress.get("percent_projected", 0)

    ui.label(f'Completed: {percent_complete}%')
    ui.linear_progress(value=percent_complete / 100).classes("w-1/2")

    ui.label(f'Projected with plan: {percent_projected}%')
    ui.linear_progress(value=percent_projected / 100).classes("w-1/2")

    ui.switch("Plan Mode").bind_value(state, "plan_mode")
    ui.separator()

    for req in requirements:
        planned_note = f' (+{req["credits_planned"]} planned)' if req["credits_planned"] else ""
        with ui.card().classes('no-shadow border border-gray-200 w-full max-w-3xl mx-auto'):
            with ui.expansion(f'{req["name"]} ({req["credits_completed"]}/{req["credits_required"]} credits{planned_note})').classes("w-full"):
                render_courses(req["id"], req["courses"])


def render_courses(req_id: int, courses: list):
    with ui.grid(columns=4).classes("gap-0 w-full"):
        
        for c in courses:
            status_text = STATUS_LABELS.get(c["status"], c["status"])
            box = f'border p-2 {STATUS_COLORS[c["status"]]}'
            ui.label(f'{c["code"]}: {c["title"]}').classes(box)
            ui.label(f'Credits: {c["credits"]}').classes(box)
            ui.label(status_text).classes(box)   

            if c["status"] == "needed":
                with ui.element("div").classes("w-full h-full"):
                    ui.button(
                        "+ Add to Plan",
                        on_click=lambda req_id=req_id, code=c["code"]: add_to_plan(req_id, code),
                    ).classes("w-full h-full").bind_visibility_from(state,"plan_mode")
                    
            elif c["status"] == "planned":
                with ui.element("div").classes("w-full h-full"):
                    ui.button(
                        "- Remove from Plan",
                        on_click=lambda req_id=req_id, code=c["code"]: remove_from_plan(req_id, code),
                    ).classes("w-full h-full").bind_visibility_from(state,"plan_mode")
            else:
                ui.label("")    
                
ui.run(port=8081, title="Mock Degree Audit")