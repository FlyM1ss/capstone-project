from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db_session
from app.models.schemas import LoginRequest, UserOut
from app.services.auth import authenticate_user, create_access_token

router = APIRouter()


@router.post("/auth/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db_session)):
    user = await authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"access_token": token, "token_type": "bearer", "user": UserOut.model_validate(user)}
