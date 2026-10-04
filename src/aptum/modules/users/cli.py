"""Operator commands. Shell and database access are the authorization; every change is audited.

    uv run python -m aptum.modules.users.cli set-role --email you@example.com --role admin

Use it once to create the first admin (the user must have logged in at least once), then manage
roles through /admin/users. `--role` takes any role name in the `roles` table (system or custom).
"""

import argparse

from aptum.core.exceptions import AptumError
from aptum.db.session import SessionLocal
from aptum.modules.users.admin_service import UserAdminService


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    set_role = commands.add_parser("set-role", help="Set a user's role by email")
    set_role.add_argument("--email", required=True)
    set_role.add_argument("--role", required=True, help="Role name, e.g. admin")
    args = parser.parse_args()

    with SessionLocal() as db:
        try:
            user = UserAdminService(db).set_role_by_operator(args.email, args.role)
        except AptumError as exc:
            raise SystemExit(f"Error: {exc.detail}") from exc
        print(f"user_id={user.id} email={user.email} role={user.role_name}")


if __name__ == "__main__":
    main()
