from typing import NoReturn

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import EmailAlreadyRegistered, UsernameTaken


# TODO(test): an IntegrityError from any other constraint is re-raised
#   unchanged (not mapped to a 409, not swallowed)
def extract_db_error_index_constraint_and_raise_error(e: IntegrityError) -> NoReturn:
    dbapi_error = e.orig
    asyncpg_error = getattr(dbapi_error, "__cause__", None)

    constraint_name = getattr(asyncpg_error, "constraint_name", None)
    if constraint_name == "ix_users_email":
        raise EmailAlreadyRegistered()
    elif constraint_name == "ix_users_username":
        raise UsernameTaken()
    else:
        raise e
