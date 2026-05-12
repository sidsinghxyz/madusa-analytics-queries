"""Every .sql under queries/ must parse with sqlglot (postgres dialect).

Catches typos before pushing — Generate KB will simply skip un-parseable
files but we want to know about them early."""
from pathlib import Path
import pytest
import sqlglot


SQL_FILES = sorted(Path(__file__).resolve().parent.parent.glob("queries/**/*.sql"))


@pytest.mark.parametrize("sql_path", SQL_FILES, ids=lambda p: str(p.relative_to(p.parent.parent.parent)))
def test_sql_file_parses(sql_path):
    text = sql_path.read_text()
    statements = sqlglot.parse(text, read="postgres")
    assert statements, f"sqlglot returned no statements for {sql_path}"
    for s in statements:
        assert s is not None, f"sqlglot got a None statement in {sql_path}"
