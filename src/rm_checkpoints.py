import os
from dotenv import load_dotenv
assert load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
import psycopg

if __name__ == "__main__":
    conn = psycopg.connect(os.environ.get("COMMPASS_DSN"))
    thread_id = input("Enter the thread_id to clear: ")
    with conn.cursor() as curs:
        curs.execute("DELETE FROM commpass_schema.checkpoints WHERE thread_id=%s;", (thread_id,))
        print(curs.rowcount)
        print(curs.pgresult)
        curs.execute("DELETE FROM commpass_schema.checkpoint_writes WHERE thread_id=%s;", (thread_id,))
        print(curs.rowcount)
        print(curs.pgresult)
        curs.execute("DELETE FROM commpass_schema.checkpoint_blobs WHERE thread_id=%s;", (thread_id,))
        print(curs.rowcount)
        print(curs.pgresult)
    commit = input("Commit changes? (y/n): ")
    if commit.lower() == "y":
        conn.commit()
    conn.close()