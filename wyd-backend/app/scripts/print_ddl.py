# Run from wyd-backend/: uv run python -m app.scripts.print_ddl
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from app.models.user import User

table = User.__table__
print(CreateTable(table).compile(dialect=postgresql.dialect()))  # type: ignore
for ix in table.indexes:  # type: ignore
    print(CreateIndex(ix).compile(dialect=postgresql.dialect()))
