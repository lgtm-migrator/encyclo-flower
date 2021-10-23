from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Any, List, Dict
from pymongo.mongo_client import MongoClient
import db
import models.user as user_model
from core.security import (
    get_password_hash,
    get_current_active_user,
    get_current_active_superuser,
)

router = APIRouter()


@router.get("/", response_model=List[user_model.User])
async def read_users(
    db: MongoClient = Depends(db.get_db),
    current_user: user_model.User = Depends(get_current_active_superuser),
):
    return list(db.users.find({}))


@router.get("/me", response_model=user_model.User)
async def read_current_user(
    current_user: user_model.User = Depends(get_current_active_user),
):
    return current_user


@router.post("/", response_model=user_model.UserCreateOut)
async def create_user(
    user_in: user_model.UserCreateIn = Body(...), db: MongoClient = Depends(db.get_db)
) -> Any:
    user = db.users.find_one({"username": user_in.username})
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
    user_in.password = get_password_hash(user_in.password)
    inserted_id = db.users.insert_one(user_in.dict()).inserted_id
    user = db.users.find_one({"_id": inserted_id})
    return user
