
def _split_sql_statements(sql: str) -> list[str]:
    stmts, current, depth = [], [], 0
    for line in sql.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        depth += stripped.count("(") - stripped.count(")")
        current.append(line)
        if stripped.endswith(";") and depth <= 0:
            stmt = "\n".join(current).strip()
            if stmt:
                stmts.append(stmt)
            current, depth = [], 0
    if current:
        stmt = "\n".join(current).strip().rstrip(";")
        if stmt:
            stmts.append(stmt)
    return stmts


async def _do_backup(context) -> bytes:
    from database import get_conn
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)
    tables = [row[0] for row in cur.fetchall()]
    lines = []
    for table in tables:
        cur.execute("""
            SELECT column_name, data_type, character_maximum_length, is_nullable, column_default
            FROM information_schema.columns WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
        """, (table,))
        col_defs = []
        for col_name, data_type, char_max_len, is_nullable, col_default in cur.fetchall():
            if data_type in ("character varying", "varchar"):
                type_str = f"VARCHAR({char_max_len})" if char_max_len else "TEXT"
            elif data_type == "character":
                type_str = f"CHAR({char_max_len})" if char_max_len else "CHAR"
            else:
                type_str = data_type.upper()
            col_defs.append(f"    {col_name} {type_str}{'' if is_nullable == 'YES' else ' NOT NULL'}{f' DEFAULT {col_default}' if col_default else ''}")
        lines += [f"-- Table: {table}", f"CREATE TABLE IF NOT EXISTS {table} (", ",\n".join(col_defs), ");", ""]
        cur.execute(f'SELECT * FROM "{table}"')
        rows = cur.fetchall(); col_names = [desc[0] for desc in cur.description]
        for row in rows:
            vals = ", ".join("'" + str(v).replace("'", "''") + "'" if v is not None else "NULL" for v in row)
            lines.append(f"INSERT INTO {table} ({', '.join(col_names)}) VALUES ({vals}) ON CONFLICT DO NOTHING;")
        lines.append("")
    conn.close()
    return "\n".join(lines).encode("utf-8")
