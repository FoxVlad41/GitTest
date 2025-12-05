from fastapi import APIRouter,Depends, HTTPException, Request, status
from sqlmodel import select, Session
from database.connection import get_session
from models.users import User, UserSignIn

user_router = APIRouter(
    tags=["User"]
)

@user_router.post("/signup")
async def sign_new_user(user: User, session: Session = Depends(get_session)) -> dict:
    statement = select(User).where(User.email == user.email)
    existing_user = session.exec(statement).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with email provided exists already."
        )
    
    # Создаем нового пользователя
    new_user = User(
        email=user.email,
        password=user.password,
        events=[]
    )
    
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    
    return {
        "message": "User created successfully"
    }


@user_router.post("/signin")
async def sign_user_in(user: UserSignIn) -> dict:
    if user.email not in users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not exist"
        )

    if users[user.email].password != user.password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Wrong credential passed"
        )

    return {
        "message": "User signed in successfully"
    }

async def sign_user_in(user: UserSignIn, session: Session = Depends(get_session)) -> dict:
    statement = select(User).where(User.email == user.email)
    user_exist = session.exec(statement).first()
    
    if not user_exist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not exist"
        )
    
    if user_exist.password == user.password:
        return {
            "message": "User signed in successfully"
        }
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Wrong credential passed"
    )

@user_router.get("/")
async def retrieve_all_users(session: Session = Depends(get_session)):
    statement = select(User)
    users = session.exec(statement).all()
    return users

# Получение пользователя по ID
@user_router.get("/{id}")
async def retrieve_user(id: int, session: Session = Depends(get_session)):
    user = session.get(User, id)
    if user:
        return user
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User with supplied ID does not exist"
    )