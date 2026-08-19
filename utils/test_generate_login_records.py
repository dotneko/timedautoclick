# test_db_manager.py
from sqlite_manager import DatabaseManager
import datetime
import random

DEFAULT_DB="test_attempts.db"
TABLE_NAME="attempts"

def main():
    # Initialize the database manager
    db = DatabaseManager(DEFAULT_DB)
    
    # Define table schema
    columns = {
        "id": "INTEGER",
        "profile": "TEXT",
        "execdate": "TEXT",
        "bookdate": "TEXT",
        "day": "TEXT",           # day of the week as 3-letter abbreviation
        "ph": "INTEGER",       # 0 for false, 1 for true
        "offset": "INTEGER",
        "tooearly": "INTEGER",          # 0 for false, 1 for true
        "queue": "INTEGER",
        "note": "TEXT",
    }
    
    # Create the table if it doesn't exist
    print("Creating table if it doesn't exist...")
    db.create_table(
        table_name=TABLE_NAME,
        columns=columns,
        primary_key="id"
    )
    print("Table created/verified.")
    print("-" * 50)
    
    # 1. INSERT a single record (CREATE)
    print("1. INSERTING a default record...")
    today = datetime.datetime.now()
    book_datetime = today + datetime.timedelta(days=6)

    sample_data = {
        "profile": "default",
        "execdate": today.strftime("%Y-%m-%d %H:%M:%S.%f"),
        "bookdate": book_datetime.strftime("%Y-%m-%d"),
        "day": book_datetime.strftime("%a").upper(),  # 3-letter day abbreviation
        "ph": 0,
        "offset": 0,
        "tooearly": 0,
        "queue": 10,
        "note": "sample data",
    }
    
    row_id = db.insert(TABLE_NAME, sample_data)
    print(f"Inserted record with ID: {row_id}")
    print("-" * 50)
    
    # 2. INSERT multiple records
    NUM_RECORDS = 100
    MAX_PROFILE = 3
    print("2. INSERTING multiple records...")
    records = []
    #days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    profile = 1
    for i in range(1, NUM_RECORDS):
        base_date = datetime.datetime.now() - datetime.timedelta(days=NUM_RECORDS) + datetime.timedelta(days=i)
        book_date = base_date + datetime.timedelta(days=6)
        offset = random.randint(0,500)
        rand_time_str = f"06:59:59.{1000-offset}"
        record = {
            "profile": f"profile{profile}",
            "execdate": base_date.strftime("%Y-%m-%d ") + rand_time_str,
            "bookdate": book_date.strftime("%Y-%m-%d"),
            "day": book_date.strftime("%a").upper(),
            "ph": 0 if random.random() < 0.8 else 1,
            "offset": offset,
            "tooearly": 0 if random.random() < 0.9 else 1,
            "queue": random.randint(0, 10000),
            "note": "" if random.random() < 0.95 else "some reason",
        }
        records.append(record)
        profile += 1
        if profile > MAX_PROFILE:
            profile = 1
    
    rows_inserted = db.insert_many(TABLE_NAME, records)
    print(f"Inserted {rows_inserted} records")
    print("-" * 50)
    
    # 3. SELECT (READ) all records
    print("3. READING all records:")
    all_records = db.select(TABLE_NAME)
    for record in all_records:
        print(f"  ID: {record['id']}, Profile: {record['profile']}, "
              f"ExecDate: {record['execdate']}, BookDate: {record['bookdate']}, Day: {record['day']}, "
              f"Queue: {record['queue']}")
    print(f"Total records: {len(all_records)}")
    print("-" * 50)
    
    # 4. SELECT with conditions
    print("4. SELECTING records with conditions (offset > 0 AND tooearly = 1):")
    filtered_records = db.select(
        TABLE_NAME,
        where="offset > ? AND tooearly = ?",
        params=(0, 1)
    )
    for record in filtered_records:
        print(f"  ID: {record['id']}, Profile: {record['profile']}, "
              f"Offset: {record['offset']}, Too Early: {record['tooearly']}")
    print(f"Found {len(filtered_records)} records")
    print("-" * 50)
    
    
    # 6. SELECT with order and limit
    print("6. SELECTING with ORDER BY and LIMIT (top 10 records by queue):")
    top_records = db.select(
        TABLE_NAME,
        columns=["id", "profile", "queue", "bookdate"],
        order_by="queue ASC",
        limit=10
    )
    for record in top_records:
        print(f"  ID: {record['id']}, Profile: {record['profile']}, "
              f"Queue: {record['queue']}, BookDate: {record['bookdate']}")
    print("-" * 50)
    
    # 9. RAW SQL query example
    print("9. RAW SQL query (SELECT all records where day is weekend):")
    weekend_records = db.execute_raw(
        "SELECT * FROM attempts WHERE day IN (?, ?)",
        ("SAT", "SUN")
    )
    for record in weekend_records:
        print(f"  ID: {record['id']}, Profile: {record['profile']}, "
              f"Day: {record['day']}")
    print(f"Weekend records: {len(weekend_records)}")
    print("-" * 50)

if __name__ == "__main__":
    main()