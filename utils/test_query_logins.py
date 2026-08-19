# query_logins.py
import argparse
import sys
from sqlite_manager import DatabaseManager

DEFAULT_DB="test_attempts.db"
TABLE_NAME="attempts"

def query_by_day(db, day, profile=None, limit=None):
    """
    Query records for a specific day of the week.
    
    Args:
        db: DatabaseManager instance
        day: Day abbreviation (e.g., 'Mon', 'Tue')
        profile: Optional profile filter
        limit: Optional limit on number of records
    
    Returns:
        List of records
    """
    where_clause = "day = ?"
    params = [day]
    
    if profile:
        where_clause += " AND profile = ?"
        params.append(profile)
    
    return db.select(
        TABLE_NAME,
        where=where_clause,
        params=tuple(params),
        order_by="queue ASC",
        limit=limit
    )

def query_weekdays(db, profile=None, limit=None):
    """
    Query records for weekdays (Mon-Fri).
    
    Args:
        db: DatabaseManager instance
        profile: Optional profile filter
        limit: Optional limit on number of records
    
    Returns:
        List of records
    """
    weekdays = ('MON', 'TUE', 'WED', 'THU', 'FRI')
    placeholders = ', '.join(['?'] * len(weekdays))
    
    where_clause = f"day IN ({placeholders})"
    params = list(weekdays)
    
    if profile:
        where_clause += " AND profile = ?"
        params.append(profile)
    
    return db.select(
        TABLE_NAME,
        where=where_clause,
        params=tuple(params),
        order_by="queue ASC",
        limit=limit
    )

def query_weekends(db, profile=None, limit=None):
    """
    Query records for weekends (Sat-Sun).
    
    Args:
        db: DatabaseManager instance
        profile: Optional profile filter
        limit: Optional limit on number of records
    
    Returns:
        List of records
    """
    weekends = ('SAT', 'SUN')
    placeholders = ', '.join(['?'] * len(weekends))
    
    where_clause = f"day IN ({placeholders})"
    params = list(weekends)
    
    if profile:
        where_clause += " AND profile = ?"
        params.append(profile)
    
    return db.select(
        TABLE_NAME,
        where=where_clause,
        params=tuple(params),
        order_by="queue ASC",
        limit=limit
    )

def display_results(records, title):
    """
    Display query results in a formatted table.
    
    Args:
        records: List of record dictionaries
        title: Title for the output section
    """
    if not records:
        print(f"\n{title}")
        print("No records found.")
        return
    
    print(f"\n{title}")
    print("=" * 100)
    print(f"{'ID':<4} {'Profile':<10} {'ExecDate':<25} {'BookDate':<10} {'Day':<7} {'PH':<4} {'Offset':<6} {'Early':<5} {'Queue':<8} {'Note':<20}")
    print("-" * 100)
    
    for record in records:
        print(f"{record['id']:<4} {record['profile']:<10} {record['execdate'][:23]:<25} "
              f"{record['bookdate']:<10} {record['day']:<7} {record['ph']:<4} "
              f"{record['offset']:<6} {record['tooearly']:<5} {record['queue']:<8} "
              f"{record['note']:<20}")
    
    print("=" * 100)
    print(f"Total records: {len(records)}")

def main():
    parser = argparse.ArgumentParser(
        description="Query records from the test database with various filters.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Query all records for Monday
  python query_logins.py --day Mon
  
  # Query weekdays (MON-FRI) with profile filter
  python query_logins.py --weekdays --profile test_profile_1
  
  # Query weekends (SAT-SUN) showing top 5 results
  python query_logins.py --weekends --limit 5
  
  # Query specific day with profile and limit
  python query_logins.py --day Wed --profile profile_2 --limit 10
        """
    )
    
    # Create mutually exclusive group for query type
    query_group = parser.add_mutually_exclusive_group(required=True)
    query_group.add_argument(
        '--day',
        type=str,
        help='Specific day of week (e.g., MON, TUE, WED, THU, FRI, SAT, SUN)'
    )
    query_group.add_argument(
        '--weekdays',
        action='store_true',
        help='Query all weekdays (MON-FRI)'
    )
    query_group.add_argument(
        '--weekends',
        action='store_true',
        help='Query all weekends (SAT-SUN)'
    )
    
    # Optional filters
    parser.add_argument(
        '--profile',
        type=str,
        help='Filter records by profile name'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit the number of results (e.g., --limit 10)'
    )
    parser.add_argument(
        '--db',
        type=str,
        default=DEFAULT_DB,
        help=f'Path to the database file (default: {DEFAULT_DB})'
    )
    
    args = parser.parse_args()
    
    # Validate day parameter
    valid_days = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
    if args.day and args.day.upper() not in valid_days:
        print(f"Error: Invalid day '{args.day}'. Must be one of: {', '.join(valid_days)}", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Initialize database connection
        db = DatabaseManager(args.db)
        
        # Execute query based on arguments
        if args.day:
            records = query_by_day(db, args.day.upper(), args.profile, args.limit)
            display_results(records, f"Records for {args.day} (ordered by queue ASC)")
        elif args.weekdays:
            records = query_weekdays(db, args.profile, args.limit)
            display_results(records, "Weekday Records (Mon-Fri, ordered by queue ASC)")
        elif args.weekends:
            records = query_weekends(db, args.profile, args.limit)
            display_results(records, "Weekend Records (Sat-Sun, ordered by queue ASC)")
            
    except FileNotFoundError:
        print(f"Error: Database file '{args.db}' not found.", file=sys.stderr)
        print("Please run test_db_manager.py first to create the database.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()