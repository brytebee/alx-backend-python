import pymysql
import csv
import uuid
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database configuration using environment variables
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'port': int(os.getenv('DB_PORT', 3306)),
    'charset': 'utf8mb4',
    'connect_timeout': 10,
    'autocommit': True
}

def connect_db():
    """Connects to the MySQL database server"""
    print(f"Attempting to connect with config: host={DB_CONFIG['host']}, user={DB_CONFIG['user']}, port={DB_CONFIG['port']}")
    try:
        print("Connecting to MySQL server...")
        connection = pymysql.connect(**DB_CONFIG)
        print("✅ Successfully connected to MySQL server")
        return connection
    except pymysql.Error as e:
        print(f"❌ PyMySQL Error: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None

def create_database(connection):
    """Creates the database ALX_prodev if it does not exist"""
    try:
        cursor = connection.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS ALX_prodev")
        print("✅ Database 'ALX_prodev' created successfully or already exists")
        cursor.close()
    except Exception as e:
        print(f"❌ Error creating database: {e}")

def connect_to_prodev():
    """Connects to the ALX_prodev database in MySQL"""
    try:
        config = DB_CONFIG.copy()
        config['database'] = os.getenv('DB_NAME', 'ALX_prodev')
        connection = pymysql.connect(**config)
        print("✅ Successfully connected to ALX_prodev database")
        return connection
    except Exception as e:
        print(f"❌ Error connecting to ALX_prodev database: {e}")
        return None

def create_table(connection):
    """Creates a table user_data if it does not exist with the required fields"""
    try:
        cursor = connection.cursor()
        
        create_table_query = """
        CREATE TABLE IF NOT EXISTS user_data (
            user_id VARCHAR(36) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL,
            age DECIMAL(5,2) NOT NULL,
            INDEX idx_user_id (user_id)
        )
        """
        
        cursor.execute(create_table_query)
        print("✅ Table 'user_data' created successfully or already exists")
        cursor.close()
    except Exception as e:
        print(f"❌ Error creating table: {e}")

def insert_data(connection, data):
    """Inserts data in the database if it does not exist"""
    try:
        cursor = connection.cursor()
        
        # Check if data already exists to avoid duplicates
        check_query = "SELECT COUNT(*) FROM user_data WHERE email = %s"
        cursor.execute(check_query, (data['email'],))
        count = cursor.fetchone()[0]
        
        if count == 0:
            insert_query = """
            INSERT INTO user_data (user_id, name, email, age)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(insert_query, (data['user_id'], data['name'], data['email'], data['age']))
            print(f"✅ Inserted data for {data['name']}")
        else:
            print(f"⚠ Data for {data['email']} already exists, skipping...")
        
        cursor.close()
    except Exception as e:
        print(f"❌ Error inserting data: {e}")

def load_csv_data(csv_filename):
    """Loads data from CSV file and returns a list of dictionaries"""
    data_list = []
    
    if not os.path.exists(csv_filename):
        print(f"❌ CSV file '{csv_filename}' not found!")
        return data_list
    
    try:
        with open(csv_filename, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Generate UUID for user_id if not present in CSV
                if 'user_id' not in row or not row['user_id']:
                    row['user_id'] = str(uuid.uuid4())
                
                # Clean and validate data
                data = {
                    'user_id': row['user_id'],
                    'name': row['name'].strip(),
                    'email': row['email'].strip(),
                    'age': float(row['age'])
                }
                data_list.append(data)
        
        print(f"✅ Loaded {len(data_list)} records from {csv_filename}")
        return data_list
    
    except Exception as e:
        print(f"❌ Error reading CSV file: {e}")
        return data_list

def main():
    """Main function to set up the database and populate it with data"""
    print("🚀 Starting database setup...")
    
    # Debug: Check if .env file exists
    if os.path.exists('.env'):
        print("✅ .env file found")
    else:
        print("⚠ .env file not found, using default values")
    
    # Step 1: Connect to MySQL server
    print("\n--- Step 1: Connecting to MySQL server ---")
    connection = connect_db()
    if not connection:
        print("❌ Failed to connect to MySQL server. Exiting.")
        return
    
    # Step 2: Create database
    print("\n--- Step 2: Creating database ---")
    create_database(connection)
    connection.close()
    
    # Step 3: Connect to ALX_prodev database
    print("\n--- Step 3: Connecting to ALX_prodev database ---")
    prodev_connection = connect_to_prodev()
    if not prodev_connection:
        print("❌ Failed to connect to ALX_prodev database. Exiting.")
        return
    
    # Step 4: Create table
    print("\n--- Step 4: Creating table ---")
    create_table(prodev_connection)
    
    # Step 5: Load data from CSV and insert into database
    print("\n--- Step 5: Loading and inserting data ---")
    csv_filename = os.getenv('CSV_FILE', 'user_data.csv')
    data_list = load_csv_data(csv_filename)
    
    if data_list:
        print(f"\n📊 Inserting {len(data_list)} records into database...")
        for data in data_list:
            insert_data(prodev_connection, data)
    else:
        print("❌ No data to insert. Make sure 'user_data.csv' exists in the same directory.")
    
    # Close connection
    prodev_connection.close()
    print("\n🎉 Database setup completed!")

if __name__ == "__main__":
    main()