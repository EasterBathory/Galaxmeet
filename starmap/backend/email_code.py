import random, time, os, ssl, smtplib
from email.mime.text import MIMEText
from email.header import Header
from typing import Dict

_rate: Dict[str, float] = {}

def gen_code() -> str:
    return str(random.randint(100000, 999999))

def send_email_code(to_email: str, code: str) -> bool:
    now = time.time()
    if _rate.get(to_email, 0) + 60 > now:
        raise ValueError("Too frequent, please retry after 60 seconds")
    _rate[to_email] = now

    smtp_host = os.getenv("SMTP_HOST", "smtp.qq.com")
    smtp_port = int(os.getenv("SMTP_PORT", 465))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")

    body = (
        '<div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px;'
        'background:#0d1117;color:#e6edf3;border-radius:12px">'
        '<h2 style="color:#58a6ff">Galaxmeet</h2>'
        '<p style="color:#8b949e">您正在进行身份验证</p>'
        '<div style="background:#21262d;border-radius:8px;padding:20px;text-align:center;'
        f'letter-spacing:8px;font-size:32px;font-weight:800;color:#e6edf3">{code}</div>'
        '<p style="color:#8b949e;font-size:13px">验证码5分钟内有效，请勿泄露给他人。</p>'
        '</div>'
    )

    msg = MIMEText(body, "html", "utf-8")
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg["Subject"] = Header("Galaxmeet Code " + code, "utf-8")

    ctx = ssl.create_default_context()
    # 用 localhost 避免 socket.getfqdn() 解析中文主机名报错
    with smtplib.SMTP_SSL(smtp_host, smtp_port, local_hostname="localhost", context=ctx) as s:
        s.login(smtp_user, smtp_pass)
        s.sendmail(smtp_user, [to_email], msg.as_bytes())
    return True
