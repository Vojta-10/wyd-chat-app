import os
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(script_dir))


from models.user import User
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

table = User.__table__
print(CreateTable(table).compile(dialect=postgresql.dialect()))
for ix in table.indexes:
    print(CreateIndex(ix).compile(dialect=postgresql.dialect()))
