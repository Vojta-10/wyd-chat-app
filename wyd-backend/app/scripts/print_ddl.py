# Run from wyd-backend/: uv run python -m app.scripts.print_ddl
from app.models.user import User
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

table = User.__table__
print(CreateTable(table).compile(dialect=postgresql.dialect()))  # type: ignore
for ix in table.indexes:  # type: ignore
    print(CreateIndex(ix).compile(dialect=postgresql.dialect()))
