from __future__ import annotations

from uuid import uuid4

from app.core.security import create_access_token


def main() -> None:
    token = create_access_token(
        {
            "sub": str(uuid4()),
            "org_id": str(uuid4()),
            "role": "admin",
        },
        expires_minutes=1,
    )
    print(token)


if __name__ == "__main__":
    main()
