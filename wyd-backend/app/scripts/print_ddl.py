# Run from wyd-backend/: uv run python -m app.scripts.print_ddl
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from app.models.user import User

table = User.metadata.tables["users"]
print(CreateTable(table).compile(dialect=postgresql.dialect()))  # type: ignore[no-untyped-call]
for ix in table.indexes:
    print(CreateIndex(ix).compile(dialect=postgresql.dialect()))  # type: ignore[no-untyped-call]
