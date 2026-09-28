import argparse
import getpass
from datetime import datetime, timezone

from features.auth.passwords import hash_password
from features.auth.repository import AuthRepository
from storage.database import get_database_engine


def create_owner_account(repository: AuthRepository, username: str, password: str) -> None:
    username = username.strip()

    if repository.has_owner():
        raise ValueError("Owner account already exists")

    if username == "":
        raise ValueError("Username cannot be empty")

    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters long")

    repository.create_owner(
        username,
        hash_password(password),
        datetime.now(timezone.utc),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Create the Venus owner account.")
    parser.add_argument("username")
    args = parser.parse_args()

    password = getpass.getpass("Password: ")
    repeated_password = getpass.getpass("Repeat password: ")
    if password != repeated_password:
        print("Passwords do not match.")
        return 1

    repository = AuthRepository(get_database_engine())
    try:
        create_owner_account(repository, args.username, password)
    except ValueError as error:
        print(error)
        return 1

    print(f"Owner '{args.username}' created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
