import sqlite3
import random
import os
from datetime import datetime, timedelta
from faker import Faker

# Initialize Faker for generating realistic data
fake = Faker()

DB_PATH = 'data/bank_data.db'

def init_db():
    """Initialize the database with required tables"""
    # Create data directory if it doesn't exist
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create table for account balances
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS account_balance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id TEXT,
        balance REAL,
        last_updated TEXT
    )
    ''')
    
    # Create table for loan status
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS loan_status (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id TEXT,
        loan_amount REAL,
        interest_rate REAL,
        status TEXT,
        last_updated TEXT
    )
    ''')
    
    conn.commit()
    conn.close()

def generate_account_id():
    """Generate a realistic bank account ID"""
    return f"ACC{random.randint(100000, 999999)}"

def generate_balance():
    """Generate realistic account balances"""
    # Most accounts will have modest balances, some will have high balances
    balance_type = random.choices(
        ['low', 'medium', 'high', 'very_high'],
        weights=[40, 35, 20, 5]
    )[0]
    
    if balance_type == 'low':
        return round(random.uniform(0, 5000), 2)
    elif balance_type == 'medium':
        return round(random.uniform(5000, 50000), 2)
    elif balance_type == 'high':
        return round(random.uniform(50000, 200000), 2)
    else:  # very_high
        return round(random.uniform(200000, 1000000), 2)

def generate_loan_data():
    """Generate realistic loan data"""
    loan_types = {
        'personal': {'min': 1000, 'max': 50000, 'rate_range': (5.5, 15.0)},
        'auto': {'min': 10000, 'max': 80000, 'rate_range': (3.0, 8.0)},
        'mortgage': {'min': 100000, 'max': 800000, 'rate_range': (3.5, 7.0)},
        'business': {'min': 5000, 'max': 500000, 'rate_range': (4.0, 12.0)}
    }
    
    loan_type = random.choice(list(loan_types.keys()))
    loan_info = loan_types[loan_type]
    
    loan_amount = round(random.uniform(loan_info['min'], loan_info['max']), 2)
    interest_rate = round(random.uniform(*loan_info['rate_range']), 2)
    
    status_options = ['active', 'pending', 'approved', 'rejected', 'paid_off', 'defaulted']
    status_weights = [50, 10, 15, 8, 12, 5]  # Active loans are most common
    status = random.choices(status_options, weights=status_weights)[0]
    
    return loan_amount, interest_rate, status

def generate_timestamp():
    """Generate a random timestamp within the last 2 years"""
    start_date = datetime.now() - timedelta(days=730)
    end_date = datetime.now()
    
    time_between = end_date - start_date
    days_between = time_between.days
    random_days = random.randrange(days_between)
    
    random_date = start_date + timedelta(days=random_days)
    return random_date.strftime('%Y-%m-%d %H:%M:%S')

def populate_account_balances(num_accounts=500):
    """Populate account_balance table with fake data"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Clear existing data
    cursor.execute('DELETE FROM account_balance')
    
    # Generate unique account IDs
    account_ids = set()
    while len(account_ids) < num_accounts:
        account_ids.add(generate_account_id())
    
    account_data = []
    for account_id in account_ids:
        balance = generate_balance()
        last_updated = generate_timestamp()
        account_data.append((account_id, balance, last_updated))
    
    cursor.executemany('''
        INSERT INTO account_balance (account_id, balance, last_updated)
        VALUES (?, ?, ?)
    ''', account_data)
    
    conn.commit()
    conn.close()
    print(f"✓ Generated {num_accounts} account balance records")

def populate_loan_status(num_loans=300, existing_accounts_ratio=0.7):
    """Populate loan_status table with fake data"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Clear existing data
    cursor.execute('DELETE FROM loan_status')
    
    # Get some existing account IDs to create realistic relationships
    cursor.execute('SELECT account_id FROM account_balance ORDER BY RANDOM() LIMIT ?', 
                   (int(num_loans * existing_accounts_ratio),))
    existing_accounts = [row[0] for row in cursor.fetchall()]
    
    loan_data = []
    
    # Create loans for existing accounts
    for account_id in existing_accounts:
        loan_amount, interest_rate, status = generate_loan_data()
        last_updated = generate_timestamp()
        loan_data.append((account_id, loan_amount, interest_rate, status, last_updated))
    
    # Create loans for new account IDs
    remaining_loans = num_loans - len(existing_accounts)
    new_account_ids = set()
    while len(new_account_ids) < remaining_loans:
        new_account_ids.add(generate_account_id())
    
    for account_id in new_account_ids:
        loan_amount, interest_rate, status = generate_loan_data()
        last_updated = generate_timestamp()
        loan_data.append((account_id, loan_amount, interest_rate, status, last_updated))
    
    cursor.executemany('''
        INSERT INTO loan_status (account_id, loan_amount, interest_rate, status, last_updated)
        VALUES (?, ?, ?, ?, ?)
    ''', loan_data)
    
    conn.commit()
    conn.close()
    print(f"✓ Generated {num_loans} loan status records")

def show_sample_data():
    """Display sample data from both tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n" + "="*60)
    print("SAMPLE ACCOUNT BALANCES")
    print("="*60)
    cursor.execute('SELECT * FROM account_balance LIMIT 5')
    for row in cursor.fetchall():
        print(f"ID: {row[0]}, Account: {row[1]}, Balance: ${row[2]:,.2f}, Updated: {row[3]}")
    
    print("\n" + "="*60)
    print("SAMPLE LOAN STATUS")
    print("="*60)
    cursor.execute('SELECT * FROM loan_status LIMIT 5')
    for row in cursor.fetchall():
        print(f"ID: {row[0]}, Account: {row[1]}, Loan: ${row[2]:,.2f}, Rate: {row[3]}%, Status: {row[4]}, Updated: {row[5]}")
    
    # Show some statistics
    print("\n" + "="*60)
    print("DATABASE STATISTICS")
    print("="*60)
    
    cursor.execute('SELECT COUNT(*) FROM account_balance')
    account_count = cursor.fetchone()[0]
    print(f"Total Accounts: {account_count}")
    
    cursor.execute('SELECT COUNT(*) FROM loan_status')
    loan_count = cursor.fetchone()[0]
    print(f"Total Loans: {loan_count}")
    
    cursor.execute('SELECT AVG(balance) FROM account_balance')
    avg_balance = cursor.fetchone()[0]
    print(f"Average Account Balance: ${avg_balance:,.2f}")
    
    cursor.execute('SELECT status, COUNT(*) FROM loan_status GROUP BY status')
    print("\nLoan Status Distribution:")
    for status, count in cursor.fetchall():
        print(f"  {status}: {count}")
    
    conn.close()

def setup_bank_database(num_accounts=500, num_loans=300):
    """
    Complete setup function to initialize and populate the bank database
    
    Args:
        num_accounts (int): Number of account balance records to generate
        num_loans (int): Number of loan status records to generate
    """
    
    # Initialize database
    init_db()
    print("✓ Database initialized")
    
    # Populate with fake data
    populate_account_balances(num_accounts)
    populate_loan_status(num_loans)
    
    # Show sample data
    show_sample_data()
    
    print(f"\n🎉 Database setup complete! Saved to: {DB_PATH}")

# Main execution (for running as standalone script)
if __name__ == "__main__":
    setup_bank_database()