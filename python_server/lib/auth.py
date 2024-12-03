from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi.security import OAuth2PasswordBearer
import jwt
import numpy as np
from python_server.lib.models import TokenData, User
from fastapi import Depends, HTTPException, status
import bcrypt

from .db import AccountsDB
from dotenv import load_dotenv
import os

from google.cloud import storage

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY") or "test"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_db():
    db = AccountsDB()
    try:
        yield db
    finally:
        del db


def create_access_token(data: dict[Any, Any], expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    db: Annotated[AccountsDB, Depends(get_db)],
    token: Annotated[str, Depends(oauth2_scheme)],
):
    cred_except = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str | None = payload.get("sub")
        if email is None:
            raise cred_except
        token_data = TokenData(email=email)
    except jwt.InvalidTokenError:
        raise cred_except

    user = db.get_user(token_data.email)
    if user is None:
        raise cred_except
    return user


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def authenticate_user(db: AccountsDB, email: str, password: str) -> User | None:
    user = db.get_user(email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def get_temp_gs_url(filepath: str) -> str:
    """
    Given a filepath beginning with gs://, return a temporary signed URL.
    """
    if not filepath.startswith("gs://"):
        raise ValueError("Filepath must begin with gs://")

    storage_client = storage.Client()
    bucket_name = filepath.split("/")[2]
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob("/".join(filepath.split("/")[3:]))
    return blob.generate_signed_url(expiration=timedelta(days=1), method="GET")


def convert_eval_metrics_to_json(eval_metrics: dict[str, Any]):
    """
    Convert evaluation metrics to JSON format.
    """
    eval = {}

    # these keys have very long arrays so we don't want to send them
    bad_keys = {"eval_ids", "eval_preds", "eval_labels"}
    for key, value in eval_metrics.items():
        if key in bad_keys:
            continue
        if isinstance(value, np.ndarray):
            value = value.tolist()
            eval[key] = value
        elif isinstance(value, float):
            eval[key] = round(value, 4)

    return eval
