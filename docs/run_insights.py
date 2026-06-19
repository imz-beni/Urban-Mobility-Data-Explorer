"""
run_insights.py — Execute the three insight queries from insights.sql
against the taxi.db database and print formatted results.

Usage:
    python docs/run_insights.py
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'taxi.db')
SQL_PATH = os.path.join(os.path.dirname(__file__), 'insights.sql')


def run():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    with open(SQL_PATH, 'r') as f:
        raw = f.read()

    queries = []
    for block in raw.split(';'):
        lines = [l for l in block.strip().split('\n')
                 if l.strip() and not l.strip().startswith('--')]
        sql = '\n'.join(lines).strip()
        if sql:
            queries.append(sql)

    titles = [
        'INSIGHT 1 — Trip demand by borough',
        'INSIGHT 2 — Average fare per mile by time of day',
        'INSIGHT 3 — Average speed by time of day (congestion)',
    ]

    for i, sql in enumerate(queries):
        title = titles[i] if i < len(titles) else f'Query {i+1}'
        print(f'\n{"=" * 60}')
        print(f'  {title}')
        print(f'{"=" * 60}')

        rows = conn.execute(sql).fetchall()
        if not rows:
            print('  (no results)')
            continue

        cols = rows[0].keys()
        widths = []
        for col in cols:
            w = max(len(col), max(len(str(row[col])) for row in rows))
            widths.append(w)

        header = '  '.join(col.ljust(w) for col, w in zip(cols, widths))
        print(f'  {header}')
        print(f'  {"-" * len(header)}')
        for row in rows:
            line = '  '.join(str(row[col]).ljust(w) for col, w in zip(cols, widths))
            print(f'  {line}')

    conn.close()
    print()


if __name__ == '__main__':
    run()
