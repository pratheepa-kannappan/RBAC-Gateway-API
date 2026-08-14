from database import get_db_connection

conn = get_db_connection()

if conn:
    print("SUCCESS")
    conn.close()
else:
    print("FAILED")
