import sqlite3

class DatabaseConnection:
    """
    A class-based context manager for handling database connections automatically.
    """
    
    def __init__(self, db_path="example.db"):
        """
        Initialize the DatabaseConnection with a database path.
        
        Args:
            db_path (str): Path to the SQLite database file
        """
        self.db_path = db_path
        self.connection = None
        self.cursor = None
    
    def __enter__(self):
        """
        Enter the context manager - open database connection.
        
        Returns:
            cursor: Database cursor for executing queries
        """
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.cursor = self.connection.cursor()
            return self.cursor
        except sqlite3.Error as e:
            print(f"Error connecting to database: {e}")
            raise
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the context manager - close database connection.
        
        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        """
        if self.cursor:
            self.cursor.close()
        if self.connection:
            if exc_type is None:
                # No exception occurred, commit changes
                self.connection.commit()
            else:
                # Exception occurred, rollback changes
                self.connection.rollback()
            self.connection.close()
        
        # Return False to propagate any exceptions
        return False

# Example usage
if __name__ == "__main__":
    # First, let's create a sample database with some data
    def setup_database():
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
                (5, "Eve Wilson", 45, "eve@example.com")
            ]
            
            cursor.executemany("""
                INSERT OR REPLACE INTO users (id, name, age, email) 
                VALUES (?, ?, ?, ?)
            """, sample_users)
            
            conn.commit()
            print("Database setup complete.")
    
    # Set up the database
    setup_database()
    
    # Use the context manager to query the database
    print("\nUsing DatabaseConnection context manager:")
    try:
        with DatabaseConnection("example.db") as cursor:
            cursor.execute("SELECT * FROM users")
            results = cursor.fetchall()
            
            print("Results from 'SELECT * FROM users':")
            print("-" * 50)
            for row in results:
                print(f"ID: {row[0]}, Name: {row[1]}, Age: {row[2]}, Email: {row[3]}")
                
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")