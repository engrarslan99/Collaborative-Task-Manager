from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import google.oauth2.id_token
from google.auth.transport import requests
from google.cloud import firestore
from datetime import datetime
import starlette.status as status
from typing import List


app = FastAPI()

firestore_db = firestore.Client()
firebase_request_adapter = requests.Request()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def validateFirebaseToken(id_token):
    if not id_token:
        return None

    try:
        user_token = google.oauth2.id_token.verify_firebase_token(
            id_token, firebase_request_adapter)
        return user_token
    except ValueError as err:
        print("Token validation failed:", str(err))
        return None

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)

    boards = []
    if user_token:
        boards = [
            {
                "id": doc.id,
                "data": doc.to_dict()
            }
            for doc in firestore_db.collection("taskBoards")
            .where("members", "array_contains", user_token["email"])
            .stream()
        ]

    return templates.TemplateResponse("main.html", {
        "request": request,
        "user_token": user_token,
        "boards": boards
    })

@app.post("/create-board")
async def create_board(request: Request, board_name: str = Form(...)):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    
    if not user_token:
        return RedirectResponse(url="/", status_code=302)

    board_data = {
        "name": board_name,
        "owner_id": user_token["user_id"],
        "owner_email": user_token["email"],
        "members": [user_token["email"]],
        "created_at": firestore.SERVER_TIMESTAMP
    }
    
    firestore_db.collection("taskBoards").add(board_data)
    return RedirectResponse(url="/", status_code=302)

@app.post("/board/{board_id}/add-member")
async def add_member(request: Request, board_id: str, member_email: str = Form(...)):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    
    if not user_token:
        return RedirectResponse(url="/", status_code=302)
        
    board_ref = firestore_db.collection("taskBoards").document(board_id)
    board = board_ref.get()
    
    if not board.exists:
        return RedirectResponse(url="/", status_code=302)
        
    board_data = board.to_dict()
    
    if board_data["owner_id"] != user_token["user_id"]:
        return RedirectResponse(url=f"/board/{board_id}", status_code=302)

    if member_email not in board_data.get("members", []):
        board_ref.update({
            "members": firestore.ArrayUnion([member_email])
        })
    
    return RedirectResponse(url=f"/board/{board_id}", status_code=302)

@app.post("/board/{board_id}/add-task")
async def add_task(
    request: Request, 
    board_id: str, 
    task_title: str = Form(...),
    due_date: str = Form(...),
    assigned_to: str = Form(None)
):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    
    if not user_token:
        return RedirectResponse(url="/", status_code=302)
        
    board_ref = firestore_db.collection("taskBoards").document(board_id)
    board = board_ref.get()
    
    if not board.exists:
        return RedirectResponse(url="/", status_code=302)
        
    board_data = board.to_dict()
    if user_token["email"] not in board_data.get("members", []):
        return RedirectResponse(url="/", status_code=302)
    
    existing_tasks = board_ref.collection("tasks").where("title", "==", task_title).stream()
    if any(existing_tasks):
        return RedirectResponse(
            url=f"/board/{board_id}?error=A task with the title '{task_title}' already exists in this board.",
            status_code=302
        )
    
    task_data = {
        "title": task_title,
        "due_date": due_date,
        "completed": False,
        "created_by": user_token["email"],
        "created_at": firestore.SERVER_TIMESTAMP,
        "assigned_to": assigned_to if assigned_to else None
    }
    
    board_ref.collection("tasks").add(task_data)
    return RedirectResponse(url=f"/board/{board_id}", status_code=302)

@app.get("/board/{board_id}", response_class=HTMLResponse)
async def view_board(request: Request, board_id: str):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)

    if not user_token:
        return RedirectResponse(url="/", status_code=302)

    board_ref = firestore_db.collection("taskBoards").document(board_id)
    board = board_ref.get()
    
    if not board.exists:
        return RedirectResponse(url="/", status_code=302)

    board_data = board.to_dict()
    if user_token["email"] not in board_data.get("members", []):
        return RedirectResponse(url="/", status_code=302)

    tasks = []
    for doc in board_ref.collection("tasks").stream():
        task_data = doc.to_dict()
        tasks.append({
            "id": doc.id,
            "data": task_data
        })
    
    error_message = request.query_params.get("error", "")

    return templates.TemplateResponse("board.html", {
        "request": request,
        "user_token": user_token,
        "board": {
            "id": board.id,
            "data": board_data
        },
        "tasks": tasks,
        "error_message": error_message
    })

@app.post("/board/{board_id}/task/{task_id}/toggle")
async def toggle_task(request: Request, board_id: str, task_id: str):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    
    if not user_token:
        return RedirectResponse(url="/", status_code=302)
        
    board_ref = firestore_db.collection("taskBoards").document(board_id)
    board = board_ref.get()
    
    if not board.exists:
        return RedirectResponse(url="/", status_code=302)
        
    board_data = board.to_dict()
    if user_token["email"] not in board_data.get("members", []):
        return RedirectResponse(url="/", status_code=302)

    task_ref = board_ref.collection("tasks").document(task_id)
    task = task_ref.get()
    
    if not task.exists:
        return RedirectResponse(url=f"/board/{board_id}", status_code=302)
        
    task_data = task.to_dict()
    update_data = {
        "completed": not task_data.get("completed", False)
    }
    
    if not task_data.get("completed", False):
        update_data["completed_at"] = firestore.SERVER_TIMESTAMP
        update_data["completed_by"] = user_token["email"]
    else:
        update_data["completed_at"] = firestore.DELETE_FIELD
        update_data["completed_by"] = firestore.DELETE_FIELD
    
    task_ref.update(update_data)
    
    return RedirectResponse(url=f"/board/{board_id}", status_code=302)

@app.get("/board/{board_id}/task/{task_id}/edit", response_class=HTMLResponse)
async def edit_task_form(request: Request, board_id: str, task_id: str):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    
    if not user_token:
        return RedirectResponse(url="/", status_code=302)
        
    board_ref = firestore_db.collection("taskBoards").document(board_id)
    board = board_ref.get()
    
    if not board.exists:
        return RedirectResponse(url="/", status_code=302)
        
    board_data = board.to_dict()
    if user_token["email"] not in board_data.get("members", []):
        return RedirectResponse(url="/", status_code=302)
        
    task_ref = board_ref.collection("tasks").document(task_id)
    task = task_ref.get()
    
    if not task.exists:
        return RedirectResponse(url=f"/board/{board_id}", status_code=302)
    
    task_data = task.to_dict()
        
    return templates.TemplateResponse("edit_task.html", {
        "request": request,
        "user_token": user_token,
        "board_id": board_id,
        "board_members": board_data.get("members", []),
        "task": {
            "id": task.id,
            "data": task_data
        }
    })

@app.post("/board/{board_id}/task/{task_id}/edit")
async def edit_task_submit(
    request: Request, 
    board_id: str, 
    task_id: str,
    task_title: str = Form(...),
    due_date: str = Form(...),
    assigned_to: List[str] = Form([])
):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    
    if not user_token:
        return RedirectResponse(url="/", status_code=302)
        
    board_ref = firestore_db.collection("taskBoards").document(board_id)
    board = board_ref.get()
    
    if not board.exists:
        return RedirectResponse(url="/", status_code=302)
        
    board_data = board.to_dict()
    if user_token["email"] not in board_data.get("members", []):
        return RedirectResponse(url="/", status_code=302)
        
    task_ref = board_ref.collection("tasks").document(task_id)
    
    update_data = {
        "title": task_title,
        "due_date": due_date,
        "assigned_to": assigned_to if assigned_to else None
    }
    task_ref.update(update_data)
    
    return RedirectResponse(url=f"/board/{board_id}", status_code=302)

@app.post("/board/{board_id}/task/{task_id}/delete")
async def delete_task(request: Request, board_id: str, task_id: str):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    
    if not user_token:
        return RedirectResponse(url="/", status_code=302)
        
    board_ref = firestore_db.collection("taskBoards").document(board_id)
    board = board_ref.get()
    
    if not board.exists:
        return RedirectResponse(url="/", status_code=302)
        
    board_data = board.to_dict()
    if user_token["email"] not in board_data.get("members", []):
        return RedirectResponse(url="/", status_code=302)
        
    task_ref = board_ref.collection("tasks").document(task_id)
    task_ref.delete()
    
    return RedirectResponse(url=f"/board/{board_id}", status_code=302)

@app.post("/board/{board_id}/rename")
async def rename_board(request: Request, board_id: str, new_board_name: str = Form(...)):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    
    if not user_token:
        return RedirectResponse(url="/", status_code=302)
        
    board_ref = firestore_db.collection("taskBoards").document(board_id)
    board = board_ref.get()
    
    if not board.exists:
        return RedirectResponse(url="/", status_code=302)
        
    board_data = board.to_dict()
    
    if board_data["owner_id"] != user_token["user_id"]:
        return RedirectResponse(url=f"/board/{board_id}", status_code=302)
        
    if new_board_name:
        board_ref.update({"name": new_board_name})
        
    return RedirectResponse(url=f"/board/{board_id}", status_code=302)

@app.post("/board/{board_id}/remove-member")
async def remove_member(request: Request, board_id: str, member_email: str = Form(...)):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    
    if not user_token:
        return RedirectResponse(url="/", status_code=302)
        
    board_ref = firestore_db.collection("taskBoards").document(board_id)
    board = board_ref.get()
    
    if not board.exists:
        return RedirectResponse(url="/", status_code=302)
        
    board_data = board.to_dict()
    

    if board_data["owner_id"] != user_token["user_id"]:
        return RedirectResponse(url=f"/board/{board_id}", status_code=302)
        

    if member_email == board_data["owner_email"]:
        return RedirectResponse(url=f"/board/{board_id}", status_code=302)
        
    tasks_query = board_ref.collection("tasks").where("assigned_to", "==", member_email)
    tasks = tasks_query.stream()
    
    batch = firestore_db.batch()
    
    for task in tasks:
        task_ref = board_ref.collection("tasks").document(task.id)
        batch.update(task_ref, {"assigned_to": None})
    
    batch.update(board_ref, {
        "members": firestore.ArrayRemove([member_email])
    })

    batch.commit()
    
    return RedirectResponse(url=f"/board/{board_id}", status_code=302)

@app.post("/board/{board_id}/delete")
async def delete_board(request: Request, board_id: str):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    
    if not user_token:
        return RedirectResponse(url="/", status_code=302)
        
    board_ref = firestore_db.collection("taskBoards").document(board_id)
    board = board_ref.get()
    
    if not board.exists:
        return RedirectResponse(url="/", status_code=302)
        
    board_data = board.to_dict()
    
    if board_data["owner_id"] != user_token["user_id"]:
        return RedirectResponse(url=f"/board/{board_id}", status_code=302)
    
    tasks = list(board_ref.collection("tasks").stream())
    if tasks:
        return RedirectResponse(
            url=f"/board/{board_id}?error=Cannot delete board: There are {len(tasks)} tasks remaining. Please delete all tasks first.",
            status_code=302
        )
    
    members = board_data.get("members", [])
    if len(members) > 1: 
        return RedirectResponse(
            url=f"/board/{board_id}?error=Cannot delete board: There are {len(members)-1} members remaining. Please remove all members first.",
            status_code=302
        )
    
    board_ref.delete()
    return RedirectResponse(url="/", status_code=302)