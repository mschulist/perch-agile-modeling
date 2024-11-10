from datetime import timedelta
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from .lib.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_db,
    hash_password,
)
from .lib.models import Project, Token, User
from .lib.db import AccountsDB
import dotenv

dotenv.load_dotenv()

ACCESS_TOKEN_EXPIRE_MINUTES = 60


app = FastAPI()

db = AccountsDB()


@app.get("/users/me")
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user


@app.post("/token")
async def login_for_access_token(
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)

    response.set_cookie(key="access_token", value=access_token, httponly=True)
    return Token(access_token=access_token, token_type="bearer")


@app.post("/create_project")
async def create_project(
    current_user: Annotated[User, Depends(get_current_user)], name: str, description: str
):
    p = Project(name=name, description=description, owner_id=current_user.id)
    project = db.create_project(p)
    return project


@app.post("/add_user")
async def add_user(name: str, email: str, password: str):
    hashed_password = hash_password(password)
    user = User(name=name, email=email, hashed_password=hashed_password)
    db.add_user(user)
    return user


@app.get("/my_projects")
async def my_projects(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AccountsDB, Depends(get_db)],
):
    user = db.session.merge(current_user)
    return user.owned_projects
