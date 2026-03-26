from fastapi import FastAPI, Depends, HTTPException, Header, UploadFile
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

from database import engine, get_db, Base
from models import User, EmailCode, SavedPoint
from auth import hash_password, verify_password, create_token, decode_token
from email_code import send_email_code, gen_code

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Galaxmeet API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Auth helpers ──
def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "未登录")
    uid = decode_token(authorization.split(" ", 1)[1])
    if not uid:
        raise HTTPException(401, "Token 无效或已过期")
    user = db.get(User, uid)
    if not user or not user.is_active:
        raise HTTPException(401, "账号不存在或已禁用")
    return user

# ── Schemas ──
class SendCodeReq(BaseModel):
    email: EmailStr
    purpose: str = "register"

class RegisterReq(BaseModel):
    email: EmailStr
    code: str
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_len(cls, v):
        if not 2 <= len(v) <= 20:
            raise ValueError("用户名长度 2-20 位")
        return v

    @field_validator("password")
    @classmethod
    def password_len(cls, v):
        if len(v) < 6:
            raise ValueError("密码至少 6 位")
        return v

class LoginReq(BaseModel):
    email: EmailStr
    code: str = ""
    password: str = ""

class UpdateProfileReq(BaseModel):
    username: Optional[str] = None
    bio: Optional[str] = None
    lang: Optional[str] = None

class ChangePasswordReq(BaseModel):
    email: EmailStr
    code: str
    new_password: str

class SavePointReq(BaseModel):
    name: str
    lat: float
    lng: float
    note: str = ""

# ════════════════════════════════════════
#  Email Code
# ════════════════════════════════════════
@app.post("/api/email/send")
async def api_send_code(req: SendCodeReq, db: Session = Depends(get_db)):
    exists = db.query(User).filter(User.email == req.email).first()
    if req.purpose == "register" and exists:
        raise HTTPException(400, "该邮箱已注册")
    if req.purpose in ("login", "reset") and not exists:
        raise HTTPException(400, "该邮箱未注册")

    code = gen_code()
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    loop = asyncio.get_event_loop()
    try:
        with ThreadPoolExecutor() as pool:
            await asyncio.wait_for(
                loop.run_in_executor(pool, send_email_code, req.email, code),
                timeout=15
            )
    except asyncio.TimeoutError:
        raise HTTPException(500, "邮件发送超时")
    except ValueError as e:
        raise HTTPException(429, str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"邮件发送失败：{type(e).__name__}: {e}")

    db.query(EmailCode).filter(
        EmailCode.email == req.email,
        EmailCode.purpose == req.purpose,
        EmailCode.used == False
    ).update({"used": True})
    db.add(EmailCode(email=req.email, code=code, purpose=req.purpose))
    db.commit()
    return {"ok": True}

def verify_code(db: Session, email: str, code: str, purpose: str):
    cutoff = datetime.utcnow() - timedelta(minutes=5)
    rec = (db.query(EmailCode)
           .filter(EmailCode.email == email, EmailCode.code == code,
                   EmailCode.purpose == purpose, EmailCode.used == False,
                   EmailCode.created_at >= cutoff)
           .order_by(EmailCode.created_at.desc()).first())
    if not rec:
        raise HTTPException(400, "验证码错误或已过期")
    rec.used = True
    db.commit()

# ════════════════════════════════════════
#  Auth
# ════════════════════════════════════════
@app.post("/api/auth/register")
def api_register(req: RegisterReq, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(400, "该邮箱已注册")
    verify_code(db, req.email, req.code, "register")
    user = User(email=req.email, username=req.username, hashed_pw=hash_password(req.password))
    db.add(user); db.commit(); db.refresh(user)
    return {"token": create_token(user.id), "user": _user_dict(user)}

@app.post("/api/auth/login")
def api_login(req: LoginReq, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(400, "邮箱未注册")
    if req.code:
        verify_code(db, req.email, req.code, "login")
    elif req.password:
        if not verify_password(req.password, user.hashed_pw):
            raise HTTPException(400, "密码错误")
    else:
        raise HTTPException(400, "请提供验证码或密码")
    return {"token": create_token(user.id), "user": _user_dict(user)}

@app.post("/api/auth/reset-password")
def api_reset_pw(req: ChangePasswordReq, db: Session = Depends(get_db)):
    if len(req.new_password) < 6:
        raise HTTPException(400, "密码至少 6 位")
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(400, "邮箱未注册")
    verify_code(db, req.email, req.code, "reset")
    user.hashed_pw = hash_password(req.new_password)
    db.commit()
    return {"ok": True}

# ════════════════════════════════════════
#  Profile
# ════════════════════════════════════════
def _user_dict(u: User):
    email = u.email
    masked = email[0] + "***" + email[email.index("@"):]
    return {"id": u.id, "email": masked, "username": u.username,
            "bio": u.bio, "lang": u.lang, "avatar": u.avatar,
            "created_at": str(u.created_at)}

@app.get("/api/me")
def api_me(user: User = Depends(get_current_user)):
    return _user_dict(user)

@app.patch("/api/me")
def api_update_me(req: UpdateProfileReq, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if req.username is not None:
        if not 2 <= len(req.username) <= 20:
            raise HTTPException(400, "用户名长度 2-20 位")
        user.username = req.username
    if req.bio is not None:
        if len(req.bio) > 200:
            raise HTTPException(400, "简介最多 200 字")
        user.bio = req.bio
    if req.lang is not None:
        user.lang = req.lang
    db.commit(); db.refresh(user)
    return _user_dict(user)

@app.post("/api/me/avatar")
async def api_upload_avatar(file: UploadFile, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if file.content_type not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
        raise HTTPException(400, "仅支持 jpg/png/webp/gif")
    data = await file.read()
    if len(data) > 2 * 1024 * 1024:
        raise HTTPException(400, "图片不能超过 2MB")
    import base64
    b64 = base64.b64encode(data).decode()
    user.avatar = f"data:{file.content_type};base64,{b64}"
    db.commit(); db.refresh(user)
    return _user_dict(user)

# ════════════════════════════════════════
#  Saved Points
# ════════════════════════════════════════
@app.get("/api/points")
def api_get_points(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    pts = db.query(SavedPoint).filter(SavedPoint.user_id == user.id).order_by(SavedPoint.created_at.desc()).all()
    return [{"id": p.id, "name": p.name, "lat": p.lat, "lng": p.lng,
             "note": p.note, "created_at": str(p.created_at)} for p in pts]

@app.post("/api/points")
def api_save_point(req: SavePointReq, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    pt = SavedPoint(user_id=user.id, name=req.name, lat=req.lat, lng=req.lng, note=req.note)
    db.add(pt); db.commit(); db.refresh(pt)
    return {"id": pt.id, "name": pt.name, "lat": pt.lat, "lng": pt.lng}

@app.delete("/api/points/{point_id}")
def api_delete_point(point_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    pt = db.query(SavedPoint).filter(SavedPoint.id == point_id, SavedPoint.user_id == user.id).first()
    if not pt:
        raise HTTPException(404, "地点不存在")
    db.delete(pt); db.commit()
    return {"ok": True}

# ════════════════════════════════════════
#  Health
# ════════════════════════════════════════
@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/test-email")
async def test_email():
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    loop = asyncio.get_event_loop()
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")
    def _test():
        import yagmail
        yag = yagmail.SMTP(smtp_user, smtp_pass)
        yag.send(to=smtp_user, subject="test", contents="test email")
        return "ok"
    with ThreadPoolExecutor() as pool:
        result = await asyncio.wait_for(loop.run_in_executor(pool, _test), timeout=20)
    return {"result": result}
