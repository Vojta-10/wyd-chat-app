from app.core.exceptions import EmailAlreadyRegistered, UsernameTaken


def extract_db_error_index_constraint_and_raise_error(e):
    dbapi_error = e.orig
    asyncpg_error = getattr(dbapi_error, "__cause__", None)

    constraint_name = getattr(asyncpg_error, "constraint_name", None)
    if constraint_name == "ix_users_email":
        raise EmailAlreadyRegistered()
    elif constraint_name == "ix_users_username":
        raise UsernameTaken()
    else:
        raise  # noqa: PLE0704
