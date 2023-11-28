import sqlite3


def run_query(query):
    db_file = "northwind.db"
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        with conn:
            cur = conn.cursor()
            cur.execute(query)
            column_names = [col[0] for col in cur.description]
            return "success", column_names, cur.fetchall()

    except Exception as e:
        return "fail", "", str(e)
