import asyncio
import aiosqlite
import sqlite3

async def async_fetch_users():
    """
    Asynchronously fetch all users from the database.
    
    Returns:
        list: All users from the database
    """
    async with aiosqlite.connect("example.db") as db:
        async with db.execute("SELECT * FROM users") as cursor:
            results = await cursor.fetchall()
            print(f"async_fetch_users() - Found {len(results)} users")
            return results

async def async_fetch_older_users():
    """
    Asynchronously fetch users older than 40 from the database.
    
    Returns:
        list: Users older than 40
    """
    async with aiosqlite.connect("example.db") as db:
        async with db.execute("SELECT * FROM users WHERE age > ?", (40,)) as cursor:
            results = await cursor.fetchall()
            print(f"async_fetch_older_users() - Found {len(results)} users older than 40")
            return results

async def fetch_concurrently():
    """
    Execute both query functions concurrently using asyncio.gather().
    
    Returns:
        tuple: Results from both queries
    """
    print("Starting concurrent database queries...")
    
    # Use asyncio.gather to run both queries concurrently
    all_users, older_users = await asyncio.gather(
        async_fetch_users(),
        async_fetch_older_users()
    )
    
    print("\nConcurrent queries completed!")
    
    # Display results
    print("\nAll Users:")
    print("-" * 50)
    for user in all_users:
        print(f"ID: {user[0]}, Name: {user[1]}, Age: {user[2]}, Email: {user[3]}")
    
    print("\nUsers Older Than 40:")
    print("-" * 50)
    for user in older_users:
        print(f"ID: {user[0]}, Name: {user[1]}, Age: {user[2]}, Email: {user[3]}")
    
    return all_users, older_users

def setup_database():
    """
    Set up the database with sample data.
    """
    with sqlite3.connect("example.db") as conn:
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                email TEXT UNIQUE
            )
        """)
        
        # Insert sample data
        sample_users = [
            (1, "Alice Johnson", 28, "alice@example.com"),
            (2, "Bob Smith", 35, "bob@example.com"),
            (3, "Charlie Brown", 42, "charlie@example.com"),
            (4, "Diana Prince", 30, "diana@example.com"),
            (5, "Eve Wilson", 45, "eve@example.com"),
            (6, "Frank Miller", 22, "frank@example.com"),
            (7, "Grace Lee", 38, "grace@example.com"),
            (8, "Henry Davis", 50, "henry@example.com"),
            (9, "Iris Chen", 33, "iris@example.com"),
            (10, "Jack Thompson", 41, "jack@example.com")
        ]
        
        cursor.executemany("""
            INSERT OR REPLACE INTO users (id, name, age, email) 
            VALUES (?, ?, ?, ?)
        """, sample_users)
        
        conn.commit()
        print("Database setup complete.")

# Example usage
if __name__ == "__main__":
    # Set up the database
    setup_database()
    
    # Run the concurrent fetch
    print("\nRunning concurrent database queries...")
    try:
        asyncio.run(fetch_concurrently())
    except Exception as e:
        print(f"Error during concurrent execution: {e}")
    
    print("\nConcurrent database operations completed successfully!")