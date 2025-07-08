import sqlite3

class ExecuteQuery:
    """
    A reusable class-based context manager that handles database connections
    and executes queries with parameters.
    """
    
    def __init__(self, db_path="example.db", query=None, params=None):
        """
        Initialize the ExecuteQuery context manager.
        
        Args:
            db_path (str): Path to the SQLite database file
            query (str): SQL query to execute
            params (tuple): Parameters for the query
        """
        self.db_path = db_path
        self.query = query
        self.params = params or ()
        self.connection = None
        self.cursor = None
        self.results = None
    
    def __enter__(self):
        """
        Enter the context manager - open connection and execute query.
        
        Returns:
            self: Returns self to allow access to results
        """
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.cursor = self.connection.cursor()
            
            if self.query:
                if self.params:
                    self.cursor.execute(self.query, self.params)
                else:
                    self.cursor.execute(self.query)
                
                # Fetch results for SELECT queries
                if self.query.strip().upper().startswith('SELECT'):
                    self.results = self.cursor.fetchall()
            
            return self
            
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            raise
        except Exception as e:
            print(f"Unexpected error: {e}")
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
    
    def get_results(self):
        """
        Get the results of the executed query.
        
        Returns:
            list: Query results
        """
        return self.results

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
                (5, "Eve Wilson", 45, "eve@example.com"),
                (6, "Frank Miller", 22, "frank@example.com"),
                (7, "Grace Lee", 38, "grace@example.com")
            ]
            
            cursor.executemany("""
                INSERT OR REPLACE INTO users (id, name, age, email) 
                VALUES (?, ?, ?, ?)
            """, sample_users)
            
            conn.commit()
            print("Database setup complete.")
    
    # Set up the database
    setup_database()
    
    # Use the ExecuteQuery context manager
    print("\nUsing ExecuteQuery context manager:")
    try:
        query = "SELECT * FROM users WHERE age > ?"
        params = (25,)
        
        with ExecuteQuery("example.db", query, params) as executor:
            results = executor.get_results()
            
            print(f"Results from '{query}' with parameter {params[0]}:")
            print("-" * 60)
            
            if results:
                for row in results:
                    print(f"ID: {row[0]}, Name: {row[1]}, Age: {row[2]}, Email: {row[3]}")
            else:
                print("No results found.")
                
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    
    # Example with different query and parameters
    print("\nAnother example - users older than 40:")
    try:
        with ExecuteQuery("example.db", "SELECT name, age FROM users WHERE age > ?", (40,)) as executor:
            results = executor.get_results()
            
            print("Users older than 40:")
            print("-" * 30)
            for row in results:
                print(f"Name: {row[0]}, Age: {row[1]}")
                
    except Exception as e:
        print(f"Error: {e}")