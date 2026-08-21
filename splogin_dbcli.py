#!/usr/bin/env python3
"""
Command-line utility for managing SP Login Tracker database.
Provides CRUD operations for tracking login attempts.
"""

import argparse
import sys
import json
from datetime import datetime
from typing import Optional
from utils.sqlite_manager import DatabaseManager

from utils.config_manager import ConfigManager

DEFAULT_CONFIG = "splogin_config.yaml"
DEFAULT_DB = "test_attempts.db"
TABLE_NAME = "attempts"

class SPLoginTrackerCLI:
    """Command-line interface for SP Login Tracker database operations."""
    
    def __init__(self, db_path: str = DEFAULT_DB):
        """Initialize the CLI with database path."""
        self.db = DatabaseManager(db_path)
        self.table_name = TABLE_NAME
        self._init_database()
    
    def _init_database(self):
        """Initialize the database schema if it doesn't exist."""
        columns = {
            "id": "INTEGER",
            "profile": "TEXT",
            "execdate": "TEXT",
            "bookdate": "TEXT",
            "day": "TEXT",
            "ph": "INTEGER",
            "offset": "INTEGER",
            "tooearly": "INTEGER",
            "queue": "INTEGER",
            "note": "TEXT",
        }
        self.db.create_table(self.table_name, columns, primary_key="id")
    
    def _validate_date(self, date_str: str) -> bool:
        """Validate date format dd-mm-yyyy."""
        try:
            datetime.strptime(date_str, "%d-%m-%Y")
            return True
        except ValueError:
            return False
    
    def _validate_day(self, day_str: str) -> bool:
        """Validate day is a 3-letter abbreviation."""
        valid_days = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
        return day_str.upper() in valid_days
    
    def _validate_boolean(self, value: str) -> bool:
        """Validate boolean value (0 or 1)."""
        return value in ["0", "1"]
    
    def create(self, profile: str, execdate: str, bookdate: str, day: str,
               ph: int, offset: int, tooearly: int, queue: int, note: str = ""):
        """Insert a new record."""
        # Validate inputs
        if not self._validate_date(execdate):
            print(f"Error: Invalid execdate format '{execdate}'. Use dd-mm-yyyy")
            return
        if not self._validate_date(bookdate):
            print(f"Error: Invalid bookdate format '{bookdate}'. Use dd-mm-yyyy")
            return
        if not self._validate_day(day):
            print(f"Error: Invalid day '{day}'. Use 3-letter abbreviation (MON, TUE, etc.)")
            return
        
        data = {
            "profile": profile,
            "execdate": execdate,
            "bookdate": bookdate,
            "day": day.upper(),
            "ph": ph,
            "offset": offset,
            "tooearly": tooearly,
            "queue": queue,
            "note": note,
        }
        
        try:
            row_id = self.db.insert(self.table_name, data)
            print(f"✅ Record inserted successfully with ID: {row_id}")
        except Exception as e:
            print(f"❌ Error inserting record: {e}")
    
    def read(self, record_id: Optional[int] = None, profile: Optional[str] = None,
             limit: Optional[int] = None, all_records: bool = False):
        """Read records from the database."""
        try:
            if record_id:
                # Read specific record by ID
                results = self.db.select(
                    self.table_name,
                    where="id = ?",
                    params=(record_id,)
                )
                if results:
                    print(json.dumps(results[0], indent=2, default=str))
                else:
                    print(f"❌ No record found with ID: {record_id}")
            elif profile:
                # Read records by profile
                results = self.db.select(
                    self.table_name,
                    where="profile = ?",
                    params=(profile,),
                    order_by="id DESC",
                    limit=limit
                )
                if results:
                    for record in results:
                        print(json.dumps(record, indent=2, default=str))
                        print("-" * 40)
                else:
                    print(f"❌ No records found for profile: {profile}")
            elif all_records:
                # Read all records
                results = self.db.select(
                    self.table_name,
                    order_by="id DESC",
                    limit=limit
                )
                if results:
                    print(f"Found {len(results)} records:")
                    for record in results:
                        print(json.dumps(record, indent=2, default=str))
                        print("-" * 40)
                else:
                    print("ℹ️ No records found in the database")
            else:
                # Default: show last 10 records
                results = self.db.select(
                    self.table_name,
                    order_by="id DESC",
                    limit=limit or 10
                )
                if results:
                    print(f"Showing last {len(results)} records:")
                    for record in results:
                        print(json.dumps(record, indent=2, default=str))
                        print("-" * 40)
                else:
                    print("ℹ️ No records found in the database")
        except Exception as e:
            print(f"❌ Error reading records: {e}")

    def list(self, limit=100):
        """
        Display query results in a formatted table.
        
        Args:
            records: List of record dictionaries
            title: Title for the output section
        """
        # Read all records
        records = self.db.select(
            self.table_name,
            order_by="id DESC",
            limit=limit
        )

        if not records:
            print("No records found.")
            return
        
        print("=" * 100)
        print(f"{'ID':<4} {'Profile':<9} {'ExecDate':<24} {'BookDate':<11} {'Day':<5} {'PH':<4} {'Offset':<6} {'Early':<5} {'Queue':<8} {'Note':<20}")
        print("-" * 100)
        
        for record in records:
            print(f"{record['id']:<4} {record['profile']:<9} {record['execdate'][:23]:<24} "
                f"{record['bookdate']:<11} {record['day']:<5} {record['ph']:<4} "
                f"{record['offset']:<6} {record['tooearly']:<5} {record['queue']:<8}"
                f"{record['note']:<20}")
        
        print("=" * 100)
        print(f"Total records: {len(records)}")

    def update(self, record_id: int, **kwargs):
        """Update a record by ID."""
        # Validate the record exists
        existing = self.db.select(self.table_name, where="id = ?", params=(record_id,))
        if not existing:
            print(f"❌ No record found with ID: {record_id}")
            return
        
        # Validate inputs
        if "execdate" in kwargs and kwargs["execdate"]:
            if not self._validate_date(kwargs["execdate"]):
                print(f"Error: Invalid execdate format '{kwargs['execdate']}'. Use dd-mm-yyyy")
                return
        if "bookdate" in kwargs and kwargs["bookdate"]:
            if not self._validate_date(kwargs["bookdate"]):
                print(f"Error: Invalid bookdate format '{kwargs['bookdate']}'. Use dd-mm-yyyy")
                return
        if "day" in kwargs and kwargs["day"]:
            if not self._validate_day(kwargs["day"]):
                print(f"Error: Invalid day '{kwargs['day']}'. Use 3-letter abbreviation")
                return
        
        # Remove None values
        update_data = {k: v for k, v in kwargs.items() if v is not None}
        
        if not update_data:
            print("ℹ️ No fields to update")
            return
        
        try:
            # Update the record
            rows_affected = self.db.update(
                self.table_name,
                update_data,
                "id = ?",
                (record_id,)
            )
            
            if rows_affected > 0:
                print(f"✅ Record ID {record_id} updated successfully")
            else:
                print(f"❌ No changes made to record ID {record_id}")
        except Exception as e:
            print(f"❌ Error updating record: {e}")
    
    def delete(self, record_id: Optional[int] = None, profile: Optional[str] = None):
        """Delete records from the database."""
        try:
            if record_id:
                # Delete by ID
                rows_affected = self.db.delete(
                    self.table_name,
                    "id = ?",
                    (record_id,)
                )
                if rows_affected > 0:
                    print(f"✅ Record ID {record_id} deleted successfully")
                else:
                    print(f"❌ No record found with ID: {record_id}")
            elif profile:
                # Delete by profile
                rows_affected = self.db.delete(
                    self.table_name,
                    "profile = ?",
                    (profile,)
                )
                if rows_affected > 0:
                    print(f"✅ Deleted {rows_affected} records for profile: {profile}")
                else:
                    print(f"❌ No records found for profile: {profile}")
            else:
                print("❌ Please specify either --id or --profile to delete")
        except Exception as e:
            print(f"❌ Error deleting records: {e}")
    
    def count(self, profile: Optional[str] = None):
        """Count records in the database."""
        try:
            if profile:
                results = self.db.select(
                    self.table_name,
                    columns=["COUNT(*) as count"],
                    where="profile = ?",
                    params=(profile,)
                )
                count = results[0]["count"] if results else 0
                print(f"📊 Total records for profile '{profile}': {count}")
            else:
                results = self.db.select(
                    self.table_name,
                    columns=["COUNT(*) as count"]
                )
                count = results[0]["count"] if results else 0
                print(f"📊 Total records in database: {count}")
        except Exception as e:
            print(f"❌ Error counting records: {e}")


def main():
    """Main entry point for the command-line utility."""

    # Load the configuration
    config = ConfigManager(DEFAULT_CONFIG)
    default_db = config.get_default('db')
    parser = argparse.ArgumentParser(
        description="SP Login Tracker Database Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a new record
  python cli.py create --profile "User1" --execdate "15-01-2026" --bookdate "20-01-2026" --day "MON" --ph 0 --offset 1000 --tooearly 0 --queue 5 --note "First attempt"

  # Read all records
  python cli.py read --all

  # Read a specific record by ID
  python cli.py read --id 1

  # Read records for a profile
  python cli.py read --profile "User1" --limit 5

  # Update a record
  python cli.py update --id 1 --queue 10 --note "Updated note"

  # Delete a record
  python cli.py delete --id 1

  # Delete all records for a profile
  python cli.py delete --profile "User1"

  # Count records
  python cli.py count
  python cli.py count --profile "User1"
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new record")
    create_parser.add_argument("--profile", required=True, help="Profile name")
    create_parser.add_argument("--execdate", required=True, help="Execution date (dd-mm-yyyy)")
    create_parser.add_argument("--bookdate", required=True, help="Booking date (dd-mm-yyyy)")
    create_parser.add_argument("--day", required=True, help="Day of week (3-letter abbreviation)")
    create_parser.add_argument("--ph", required=True, type=int, choices=[0, 1], help="Public holiday (0 or 1)")
    create_parser.add_argument("--offset", required=True, type=int, help="Milliseconds offset")
    create_parser.add_argument("--tooearly", required=True, type=int, choices=[0, 1], help="Too early attempt (0 or 1)")
    create_parser.add_argument("--queue", required=True, type=int, help="Queue number")
    create_parser.add_argument("--note", default="", help="Additional notes")
    
    # Read command
    read_parser = subparsers.add_parser("read", help="Read records")
    read_group = read_parser.add_mutually_exclusive_group()
    read_group.add_argument("--id", type=int, help="Read record by ID")
    read_group.add_argument("--profile", help="Read records by profile")
    read_group.add_argument("--all", action="store_true", help="Read all records")
    read_parser.add_argument("--limit", type=int, help="Limit number of records")

    # List command
    list_parser = subparsers.add_parser("list", help="List records")
    list_parser.add_argument("--limit", type=int, help="Limit number of records")

    # Update command
    update_parser = subparsers.add_parser("update", help="Update a record")
    update_parser.add_argument("--id", required=True, type=int, help="Record ID to update")
    update_parser.add_argument("--profile", help="Update profile name")
    update_parser.add_argument("--execdate", help="Update execution date (dd-mm-yyyy)")
    update_parser.add_argument("--bookdate", help="Update booking date (dd-mm-yyyy)")
    update_parser.add_argument("--day", help="Update day of week (3-letter abbreviation)")
    update_parser.add_argument("--ph", type=int, choices=[0, 1], help="Update public holiday (0 or 1)")
    update_parser.add_argument("--offset", type=int, help="Update milliseconds offset")
    update_parser.add_argument("--tooearly", type=int, choices=[0, 1], help="Update too early attempt (0 or 1)")
    update_parser.add_argument("--queue", type=int, help="Update queue number")
    update_parser.add_argument("--note", help="Update additional notes")
    
    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete records")
    delete_group = delete_parser.add_mutually_exclusive_group(required=True)
    delete_group.add_argument("--id", type=int, help="Delete record by ID")
    delete_group.add_argument("--profile", help="Delete all records for a profile")
    
    # Count command
    count_parser = subparsers.add_parser("count", help="Count records")
    count_parser.add_argument("--profile", help="Count records for a specific profile")
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Initialize the CLI
    cli = SPLoginTrackerCLI(db_path=default_db)
    
    # Execute the command
    if args.command == "create":
        cli.create(
            args.profile, args.execdate, args.bookdate, args.day,
            args.ph, args.offset, args.tooearly, args.queue, args.note
        )
    elif args.command == "read":
        cli.read(args.id, args.profile, args.limit, args.all)
    elif args.command == "list":
        cli.list(args.limit)
    elif args.command == "update":
        # Build kwargs from args
        update_fields = {}
        for field in ["profile", "execdate", "bookdate", "day", "ph", 
                     "offset", "tooearly", "queue", "note"]:
            if hasattr(args, field) and getattr(args, field) is not None:
                update_fields[field] = getattr(args, field)
        cli.update(args.id, **update_fields)
    elif args.command == "delete":
        cli.delete(args.id, args.profile)
    elif args.command == "count":
        cli.count(args.profile)
    else:
        print(f"❌ Unknown command: {args.command}")
        sys.exit(1)


if __name__ == "__main__":
    main()