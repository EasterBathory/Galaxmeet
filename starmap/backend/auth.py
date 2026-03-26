from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
import os

pwd_ctx = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

def hash_password(pw: str) -> str:
    return pwd_ctx.hash(pw)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)

def create_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=int(os.getenv("JWT_EXPIRE_MINUTES", 10080)))
    return jwt.encode({"sub": str(user_id), "exp": expire}, os.getenv("JWT_SECRET"), algorithm="HS256")

def decode_token(token: str) -> "int | None":
    try:
        payload = jwt.decode(token, os.getenv("JWT_SECRET"), algorithms=["HS256"])
        return int(payload["sub"])
    except JWTError:
        return None
