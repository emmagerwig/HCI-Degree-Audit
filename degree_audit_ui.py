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

# colors for each course status in the tables
STATUS_COLORS = {
    "completed": "text-green-700",
    "in_progress": "text-blue-700",
    "planned": "text-amber-500",
    "needed": "text-red-700",
}

# Kaitlyn: the header toggle binds to this same dict
# Brendan: default is False normal mode, loaded from the API in main_page
state = {"plan_mode": False}

# Brendan: plan mode styling shared by the border and the projected bar
PLAN_COLOR_NAME = "orange"  # Quasar orange
PLAN_COLOR = "#ff9800"
expanded = {}  # Brendan: req_id -> open/closed, so refreshes keep dropdowns as they were


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


# Brendan: saves the plan mode choice to the API
def set_plan_mode(e):
    api_post("/mode", {"plan_mode": bool(e.value)})


# Kaitlyn: new helper so the body and the header summary update together
# whenever the plan changes the header shows the projected %
def refresh_all():
    render_audit.refresh()
    header_summary.refresh()


def add_to_plan(req_id: int, code: str):
    if api_post("/plan/add", {"req_id": req_id, "code": code}):
        refresh_all()


def remove_from_plan(req_id: int, code: str):
    if api_post("/plan/remove", {"req_id": req_id, "code": code}):
        refresh_all()


# Kaitlyn: work

@ui.refreshable
def header_summary():
    """Compact progress numbers shown in the header (common region + similarity)."""
    progress = api_get("/progress")
    completed = progress.get("percent_complete", 0)
    projected = progress.get("percent_projected", 0)
    with ui.row().classes("items-center gap-6"):
        with ui.column().classes("gap-0"):
            ui.label("Completed").classes("text-xs text-gray-500 uppercase")
            ui.label(f"{completed}%").classes("text-lg font-bold")
        # Kaitlyn: projected only shows in plan mode, same as Brendan's projected bar
        with ui.column().classes("gap-0").bind_visibility_from(state, "plan_mode"):
            ui.label("Projected").classes("text-xs text-gray-500 uppercase")
            ui.label(f"{projected}%").classes("text-lg font-bold")


def render_mode_toggle():
    # Brendan's plan mode switch, moved here from render_audit so it sits in the header
    ui.switch("Plan Mode", on_change=set_plan_mode).bind_value(state, "plan_mode")


def render_header():
    """Persistent header: ui.header is fixed to the top, so it stays visible on scroll."""
    program = api_get("/program")
    with ui.header(elevated=True).classes(
        "bg-white text-black items-center justify-between px-6 py-3"
    ):
        # Left: identity proximity: title + metadata grouped
        with ui.column().classes("gap-0"):
            ui.label(program.get("major", "")).classes("text-xl font-bold")
            ui.label(
                f'{program.get("student", "")} | Catalog {program.get("catalog_year", "")} '
                f'| Advisor: {program.get("advisor", "")}'
            ).classes("text-sm text-gray-600")

        # Right: summary + mode toggle grouped as "status / controls"
        with ui.row().classes("items-center gap-8"):
            header_summary()
            render_mode_toggle()


# Main Page

@ui.page("/")
def main_page():
    # Brendan: load the saved plan mode and draw the plan mode border overlay
    state["plan_mode"] = bool(api_get("/mode").get("plan_mode", False))
    ui.element("div").classes(
        f"fixed inset-0 pointer-events-none z-[9999] border-8 border-[{PLAN_COLOR}]"
    ).bind_visibility_from(state, "plan_mode")

    # Kaitlyn: header first, then everything else in one centered column
    # max-w-3xl matches Emma's requirement cards so everything shares one left edge
    render_header()
    with ui.column().classes("w-full max-w-3xl mx-auto gap-4 p-4"):
        render_audit()


@ui.refreshable
def render_audit():
    # Kaitlyn: removed the program = api_get("/program") call and the two
    # labels (major, student/catalog/advisor) because the header shows them now
    progress = api_get("/progress")
    requirements = api_get("/requirements")

    percent_complete = progress.get("percent_complete", 0)
    percent_projected = progress.get("percent_projected", 0)


    ui.label(f'Completed: {percent_complete}%')
    ui.linear_progress(value=percent_complete / 100, size="20px", show_value=False).classes("w-1/2")

    # Brendan: projected bar only shows in plan mode, in the plan color
    ui.label(f'Projected with plan: {percent_projected}%').bind_visibility_from(state, "plan_mode")
    ui.linear_progress(value=percent_projected / 100, size="20px", show_value=False).props(f"color={PLAN_COLOR_NAME}").classes("w-1/2").bind_visibility_from(state, "plan_mode")

    # Kaitlyn: Brendan's Plan Mode switch was here, moved to render_mode_toggle() in the header

    ui.separator()


    for req in requirements:
        planned_note = f' (+{req["credits_planned"]} planned)' if req["credits_planned"] else ""
        with ui.card().classes('no-shadow border border-gray-200 w-full mx-auto'):
            # Kaitlyn: dropped max-w-3xl here since the parent column
            # already sets the width; w-full keeps the cards aligned with it, can be overridden by the parent column if needed
            # Brendan: expanded dict keeps each dropdown open/closed across refreshes
            expanded.setdefault(str(req["id"]), False)
            with ui.expansion(
                f'{req["name"]} ({req["credits_completed"]}/{req["credits_required"]} credits{planned_note})'
            ).classes("w-full").bind_value(expanded, str(req["id"])):
                render_courses(req["id"], req["courses"])


def render_courses(req_id: int, courses: list):
    with ui.grid(columns=4).classes("gap-0 w-full"):
        for c in courses:
            status_text = STATUS_LABELS.get(c["status"], c["status"])
            box = f'border p-2 {STATUS_COLORS[c["status"]]}'
            ui.label(f'{c["code"]}: {c["title"]}').classes(box)
            ui.label(f'Credits: {c["credits"]}').classes(box)
            ui.label(status_text).classes(box)

            # todo?: buttons are only visible in plan mode
            # need to remove the "planned" state in normal mode
            if c["status"] == "needed":
                with ui.element("div").classes("w-full h-full"):
                    ui.button(
                        "+ Add to Plan",
                        on_click=lambda req_id=req_id, code=c["code"]: add_to_plan(req_id, code),
                    ).classes("w-full h-full").bind_visibility_from(state, "plan_mode")
            elif c["status"] == "planned":
                with ui.element("div").classes("w-full h-full"):
                    ui.button(
                        "- Remove from Plan",
                        on_click=lambda req_id=req_id, code=c["code"]: remove_from_plan(req_id, code),
                    ).classes("w-full h-full").bind_visibility_from(state, "plan_mode")
            else:
                ui.label("")


ui.run(port=8081, title="Mock Degree Audit")