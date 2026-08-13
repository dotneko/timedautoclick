from sqlite_manager import DatabaseManager

# Initialize the library with a database file
db = DatabaseManager("splogin_log.db")

# 1. Create a table
db.create_table(
    table_name="attempts",
    columns={
        "id": "INTEGER",
        "date": "TEXT",
        "isoday": "INTEGER",
        "tag": "TEXT",
        "offset": "INTEGER",
        "tooearly": "INTEGER",
        "queue": "INTEGER"
    },
    primary_key="id",
)

# 2. Create (Insert) records
user_id = db.insert("attempts", {
    "date": "2026-08-11",
    "isoday": 2,
    "tag": "g",
    "offset": 120,
    "tooearly": 0,
    "queue": 230,
})
print(f"Inserted user with ID: {user_id}")

# Insert multiple records at once
db.insert_many("attempts", [
    {
    "date": "2026-08-12",
    "isoday": 3,
    "tag": "g",
    "offset": 120,
    "tooearly": 0,
    "queue": 8000,
    },
    {
        "date": "2026-08-13",
        "isoday": "4",
        "tag": "g",
        "offset": 125,
        "tooearly": 0,
        "queue": 5000,
    },
])

# 3. Read (Select) records
# Get all users
all_attempts = db.select("attempts")
print("All attempts:", all_attempts)

# Get specific columns with a filter
fast_login = db.select(
    "attempts", 
    columns=["isoday", "offset", "queue"], 
    where="queue < ?", 
    params=(1000,)
)
print("Fast login attempts:", fast_login)

# 4. Update records
rows_updated = db.update(
    "attempts",
    data={"tooearly": 1},
    where="date = ?",
    params=("2026-08-12",)
)
print(f"Updated {rows_updated} row(s)")

# 5. Delete records
rows_deleted = db.delete(
    "attempts",
    where="date = ?",
    params=("2026-08-13",)
)
print(f"Deleted {rows_deleted} row(s)")

# Verify final state
print("Final database state:", db.select("attempts"))   