# test_db_manager.py
from sqlite_manager import DatabaseManager
import datetime
import random

def main():
    # Initialize the database manager
    db = DatabaseManager("test_database.db")
    
    # Define table schema
    columns = {
        "id": "INTEGER",
        "profile": "TEXT",
        "date": "TEXT",
        "exec_time": "TEXT",
        "day": "TEXT",          # day of the week as 3-letter abbreviation
        "offset": "INTEGER",
        "tooearly": "INTEGER",  # 0 for false, 1 for true
        "queue": "INTEGER"
    }
    
    # Create the table if it doesn't exist
    print("Creating table if it doesn't exist...")
    db.create_table(
        table_name="test_records",
        columns=columns,
        primary_key="id"
    )
    print("Table created/verified.")
    print("-" * 50)
    
    # 1. INSERT a single record (CREATE)
    print("1. INSERTING a single record...")
    today = datetime.datetime.now()
    sample_data = {
        "profile": "test_profile_1",
        "date": today.strftime("%Y-%m-%d"),
        "exec_time": today.strftime("%H:%M:%S"),
        "day": today.strftime("%a"),  # 3-letter day abbreviation
        "offset": 0,
        "tooearly": 0,
        "queue": 10
    }
    
    row_id = db.insert("attempts", sample_data)
    print(f"Inserted record with ID: {row_id}")
    print("-" * 50)
    
    # 2. INSERT multiple records
    print("2. INSERTING multiple records...")
    records = []
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    
    for i in range(1, 6):
        base_date = datetime.datetime.now() + datetime.timedelta(days=i)
        record = {
            "profile": f"profile_{i}",
            "date": base_date.strftime("%Y-%m-%d"),
            "exec_time": f"{random.randint(8, 18):02d}:{random.randint(0, 59):02d}:{random.randint(0, 59):02d}",
            "day": days[i % 7],
            "offset": random.randint(-12, 12),
            "tooearly": random.randint(0, 1),
            "queue": random.randint(0, 100)
        }
        records.append(record)
    
    rows_inserted = db.insert_many("test_records", records)
    print(f"Inserted {rows_inserted} records")
    print("-" * 50)
    
    # 3. SELECT (READ) all records
    print("3. READING all records:")
    all_records = db.select("test_records")
    for record in all_records:
        print(f"  ID: {record['id']}, Profile: {record['profile']}, "
              f"Date: {record['date']}, Day: {record['day']}, "
              f"Queue: {record['queue']}")
    print(f"Total records: {len(all_records)}")
    print("-" * 50)
    
    # 4. SELECT with conditions
    print("4. SELECTING records with conditions (offset > 0 AND tooearly = 1):")
    filtered_records = db.select(
        "test_records",
        where="offset > ? AND tooearly = ?",
        params=(0, 1)
    )
    for record in filtered_records:
        print(f"  ID: {record['id']}, Profile: {record['profile']}, "
              f"Offset: {record['offset']}, Too Early: {record['tooearly']}")
    print(f"Found {len(filtered_records)} records")
    print("-" * 50)
    
    # 5. UPDATE a record
    print("5. UPDATING a record (setting tooearly=1 for all records with offset > 5):")
    rows_updated = db.update(
        "test_records",
        data={"tooearly": 1, "queue": 99},
        where="offset > ?",
        params=(5,)
    )
    print(f"Updated {rows_updated} records")
    print("-" * 50)
    
    # 6. SELECT with order and limit
    print("6. SELECTING with ORDER BY and LIMIT (top 3 records by queue):")
    top_records = db.select(
        "test_records",
        columns=["id", "profile", "queue", "date"],
        order_by="queue DESC",
        limit=3
    )
    for record in top_records:
        print(f"  ID: {record['id']}, Profile: {record['profile']}, "
              f"Queue: {record['queue']}, Date: {record['date']}")
    print("-" * 50)
    
    # 7. DELETE a record
    print("7. DELETING a record (deleting ID = 1):")
    rows_deleted = db.delete(
        "test_records",
        where="id = ?",
        params=(1,)
    )
    print(f"Deleted {rows_deleted} records")
    print("-" * 50)
    
    # 8. Verify deletion
    print("8. VERIFYING deletion (records after deletion):")
    remaining_records = db.select("test_records")
    for record in remaining_records:
        print(f"  ID: {record['id']}, Profile: {record['profile']}")
    print(f"Remaining records: {len(remaining_records)}")
    print("-" * 50)
    
    # 9. RAW SQL query example
    print("9. RAW SQL query (SELECT all records where day is weekend):")
    weekend_records = db.execute_raw(
        "SELECT * FROM test_records WHERE day IN (?, ?)",
        ("Sat", "Sun")
    )
    for record in weekend_records:
        print(f"  ID: {record['id']}, Profile: {record['profile']}, "
              f"Day: {record['day']}")
    print(f"Weekend records: {len(weekend_records)}")
    print("-" * 50)
    
    # 10. INSERT with all fields populated
    print("10. INSERTING a fully populated record:")
    full_record = {
        "profile": "complete_profile",
        "date": "2026-08-19",
        "exec_time": "14:30:00",
        "day": "Wed",
        "offset": 5,
        "tooearly": 0,
        "queue": 25
    }
    new_id = db.insert("test_records", full_record)
    print(f"Inserted complete record with ID: {new_id}")
    print("-" * 50)
    
    print("✅ All CRUD operations completed successfully!")

if __name__ == "__main__":
    main()