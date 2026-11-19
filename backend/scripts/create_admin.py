"""Bootstrap Admin tường minh từ terminal máy chủ, không có mật khẩu mặc định."""
import argparse
import asyncio
import getpass
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from sqlalchemy import select
from app.core.database import AsyncSessionLocal,engine
from app.core.security import get_password_hash
from app.models.identity import User,UserRole
from app.schemas.identity import UserRegisterRequest

async def create(email,name,password):
    # Dùng cùng validation đầu vào; role ADMIN chỉ được đặt ở CLI này.
    payload=UserRegisterRequest(email=email,password=password,full_name=name)
    async with AsyncSessionLocal() as db:
        existing=(await db.execute(select(User).where(User.email==str(payload.email).lower()))).scalar_one_or_none()
        if existing:
            raise ValueError("Tài khoản đã tồn tại; CLI không tự nâng quyền hay đổi mật khẩu.")
        db.add(User(email=str(payload.email).lower(),full_name=payload.full_name,hashed_password=get_password_hash(password),role=UserRole.ADMIN,is_active=True))
        await db.commit()
    await engine.dispose()

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--email",required=True);parser.add_argument("--name",required=True);args=parser.parse_args()
    password=getpass.getpass("Mật khẩu Admin (ẩn khi nhập): ")
    if password != getpass.getpass("Nhập lại mật khẩu: "):
        raise SystemExit("Mật khẩu xác nhận không khớp.")
    try:
        asyncio.run(create(args.email,args.name,password))
    except Exception:
        raise SystemExit("Không tạo được Admin. Kiểm tra đầu vào, tài khoản tồn tại và DB máy chủ; không có thay đổi quyền tự động.") from None
    print("Đã tạo Admin. Không lưu hoặc in mật khẩu.")
