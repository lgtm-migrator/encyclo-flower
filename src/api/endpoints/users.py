from fastapi import APIRouter, Depends, Response, Request, BackgroundTasks
from fastapi.responses import RedirectResponse
from typing import List, Union
from pymongo.mongo_client import MongoClient
from db import get_db
from models.user import (
    UserOut,
    CreateUserIn,
    UserInDB,
    UpdateUserIn,
    UserMinimalMetadataOut,
)
from core.security import (
    get_password_hash,
    get_current_active_user,
    get_current_active_superuser,
    get_current_user_if_exists,
)
from endpoints.helpers_tools.common_dependencies import QuerySearchPageParams
from endpoints.helpers_tools.user_dependencies import (
    validate_accept_terms_of_service,
    validate_username_and_email_not_in_db,
    validate_current_user_edit_itself,
    validate_match_passwords__new_user,
    get_existing_user,
    get_user_from_email_registration_token,
)
from models.exceptions import (
    ExceptionUserNotPrivilege,
    ExceptionUserNotAuthenticated,
    ExceptionUserNotFound,
    ExceptionUserNotAllowToEditThisUser,
    ExceptionUserNotAcceptTermsOfService,
    ExceptionUserOrEmailAlreadyExists,
    ExceptionPasswordNotMatch,
    DetailUserNotFound,
)
from endpoints.helpers_tools.email import setup_email_verification

router = APIRouter()


@router.get(
    "/",
    response_model=List[UserInDB],
    dependencies=[Depends(get_current_active_superuser)],
    summary="Get all users",
    description="Get all users. Only superusers can do this.",
    responses={
        401: {
            "description": ExceptionUserNotAuthenticated().detail,
            "model": ExceptionUserNotAuthenticated,
        },
        403: {
            "description": ExceptionUserNotPrivilege().detail,
            "model": ExceptionUserNotPrivilege,
        },
    },
)
async def read_users(
    db: MongoClient = Depends(get_db),
    search_params: QuerySearchPageParams = Depends(QuerySearchPageParams),
) -> List[UserInDB]:
    return list(db.users.find({}).skip(search_params.skip).limit(search_params.limit))


@router.get(
    "/me",
    response_class=RedirectResponse,
    summary="Get current user",
    description="Redirect to user profile",
    responses={
        401: {
            "description": ExceptionUserNotAuthenticated().detail,
            "model": ExceptionUserNotAuthenticated,
        }
    },
)
async def read_current_user(
    current_user: UserOut = Depends(get_current_active_user),
) -> RedirectResponse:
    return current_user.username


@router.get(
    "/{username}",
    response_model=UserOut,
    summary="User page",
    description="Get user basic data",
    responses={
        404: {
            "description": DetailUserNotFound().detail,
            "model": DetailUserNotFound,
        },
    },
)
async def read_user(
    requested_user: UserOut = Depends(get_existing_user),
    current_user: UserMinimalMetadataOut = Depends(get_current_user_if_exists),
) -> UserOut:
    """
    exclude email and phone if the requested user is not the current user.
    """

    # TODO: add list of requested user observability
    # TODO: add list of requested user questions
    # TODO: add list of detection user
    # TODO: liked plants (not developed yet)

    if requested_user.username == current_user.username or current_user.is_superuser:
        return requested_user
    return requested_user.dict(exclude={"email", "phone"})


@router.put(
    "/{username}",
    status_code=204,
    summary="Update current user",
    description="Update current user with shown fields",
    dependencies=[Depends(validate_current_user_edit_itself)],
    responses={
        400: {
            "description": ExceptionUserNotAllowToEditThisUser().detail,
            "model": ExceptionUserNotAllowToEditThisUser,
        },
        401: {
            "description": ExceptionUserNotAuthenticated().detail,
            "model": ExceptionUserNotAuthenticated,
        },
        404: {
            "description": ExceptionUserNotFound().detail,
            "model": ExceptionUserNotFound,
        },
    },
)
async def update_user(
    username: str,
    user_in: UpdateUserIn,
    db: MongoClient = Depends(get_db),
):
    db.users.update_one(
        {"username": username},
        {"$set": user_in.dict(exclude_none=True, exclude_unset=True)},
    )
    return Response(status_code=204)


@router.post(
    "/",
    status_code=201,
    dependencies=[
        Depends(validate_accept_terms_of_service),
        Depends(validate_username_and_email_not_in_db),
        Depends(validate_match_passwords__new_user),
    ],
    summary="Create new user",
    description="After registration, user must verify email",
    responses={
        400: {
            "description": "Input Validation",
            "model": Union[
                ExceptionUserNotAcceptTermsOfService,
                ExceptionUserOrEmailAlreadyExists,
                ExceptionPasswordNotMatch,
            ],
        },
    },
)
async def create_user(
    user_in: CreateUserIn,
    request: Request,
    background_tasks: BackgroundTasks,
    db: MongoClient = Depends(get_db),
):
    # TODO: add email verification

    # * hash the password
    hash_password = get_password_hash(user_in.password.get_secret_value())

    # * setup userInDB with hash password
    userInDB = UserInDB(**user_in.dict(exclude={"password"}), password=hash_password)

    # * email verification
    background_tasks.add_task(
        setup_email_verification,
        userInDB.user_id,
        userInDB.email,
        request.base_url,
    )

    # * insert user
    db.users.insert_one(userInDB.dict())

    return Response(status_code=201)


@router.get(
    "/verify-email/{token}",
    status_code=204,
    summary="Verify email",
    description="Verify email with email verification token",
)
async def verify_email(
    user_id: str = Depends(get_user_from_email_registration_token),
    db: MongoClient = Depends(get_db),
):
    db.users.update_one(
        {"user_id": user_id},
        {"$set": {"email_verified": True, "is_active": True}},
    )
    return Response(status_code=204)
