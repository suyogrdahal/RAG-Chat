# backend/scripts/reset_password.py
import argparse
from app.core.security import hash_password
from app.db.models import User
from app.db.session import SessionLocal


def reset_password(email: str, new_password: str) -> None:
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.email == email).first()
        if user is None:
            print(f"User with email {email} not found.")
            return
        user.password_hash = hash_password(new_password)
        session.add(user)
        session.commit()
        print(f"Password reset for {email}")
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset a user's password (testing only).")
    parser.add_argument("--email", required=True, help="User email")
    parser.add_argument("--password", required=True, help="test")
    args = parser.parse_args()
    reset_password(args.email, args.password)


if __name__ == "__main__":
    main()
