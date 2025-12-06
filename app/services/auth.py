"""
Authentication utilities for validating JWT tokens from Neon Auth (Stack Auth).
Neon Auth syncs users directly to neon_auth.users_sync table in your database.
"""
import os
from typing import Optional

import httpx
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_db

load_dotenv()

STACK_PROJECT_ID = os.getenv("STACK_PROJECT_ID")

security = HTTPBearer(auto_error=False)

_jwks_cache = {}


class TokenUser(BaseModel):
    id: str
    email: Optional[str] = None
    name: Optional[str] = None


class NeonAuthUser(BaseModel):
    id: str
    email: Optional[str] = None
    name: Optional[str] = None
    raw: Optional[dict] = None


async def get_stack_auth_jwks():
    if not STACK_PROJECT_ID:
        raise HTTPException(status_code=500, detail="STACK_PROJECT_ID not configured")
    
    cache_key = f"stack_{STACK_PROJECT_ID}"
    if cache_key in _jwks_cache:
        return _jwks_cache[cache_key]
    
    jwks_url = f"https://api.stack-auth.com/api/v1/projects/{STACK_PROJECT_ID}/.well-known/jwks.json"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(jwks_url)
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to fetch JWKS")
        jwks = response.json()
        _jwks_cache[cache_key] = jwks
        return jwks


async def verify_stack_auth_token(token: str) -> TokenUser:
    try:
        jwks = await get_stack_auth_jwks()
        
        headers = jwt.get_unverified_headers(token)
        kid = headers.get("kid")
        
        key = None
        for k in jwks.get("keys", []):
            if k.get("kid") == kid:
                key = k
                break
        
        if not key:
            raise HTTPException(status_code=401, detail="Invalid token key")
        
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256", "ES256"],
            options={"verify_aud": False},
        )
        
        return TokenUser(
            id=payload.get("sub"),
            email=payload.get("email"),
            name=payload.get("name"),
        )
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


async def get_neon_auth_user(
    user_id: str,
    db: AsyncSession,
) -> Optional[NeonAuthUser]:
    try:
        result = await db.execute(
            text("SELECT id, name, email, raw FROM neon_auth.users_sync WHERE id = :user_id"),
            {"user_id": user_id}
        )
        row = result.fetchone()
        
        if not row:
            return None
        
        return NeonAuthUser(
            id=str(row[0]),
            name=row[1],
            email=row[2],
            raw=row[3] if row[3] else None,
        )
    except Exception:
        await db.rollback()
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: AsyncSession = Depends(get_db),
) -> NeonAuthUser:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token_user = await verify_stack_auth_token(credentials.credentials)
    
    neon_user = await get_neon_auth_user(token_user.id, db)
    
    if neon_user:
        return neon_user
    
    return NeonAuthUser(
        id=token_user.id,
        email=token_user.email,
        name=token_user.name,
    )


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[NeonAuthUser]:
    if not credentials:
        return None
    
    try:
        token_user = await verify_stack_auth_token(credentials.credentials)
        neon_user = await get_neon_auth_user(token_user.id, db)
        return neon_user if neon_user else NeonAuthUser(
            id=token_user.id,
            email=token_user.email,
            name=token_user.name,
        )
    except HTTPException:
        return None


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> str:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token_user = await verify_stack_auth_token(credentials.credentials)
    return token_user.id
