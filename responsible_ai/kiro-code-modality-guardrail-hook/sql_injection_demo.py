#!/usr/bin/env python3
"""
SQL Injection Vulnerability Demo
Educational script showing vulnerable vs safe SQL patterns
"""

# ============================================================================
# VULNERABLE PATTERNS (Should be detected by guardrail)
# ============================================================================

def vulnerable_login_check(username, password):
    """
    VULNERABLE: Uses string formatting with user input
    Allows SQL injection attacks
    """
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    # Execute query...
    return query


def vulnerable_search(search_term):
    """
    VULNERABLE: String concatenation with user input
    """
    query = "SELECT * FROM products WHERE name LIKE '%" + search_term + "%'"
    return query


def vulnerable_delete(user_id):
    """
    VULNERABLE: Direct string interpolation
    """
    query = "DELETE FROM users WHERE id = %s" % user_id
    return query


# ============================================================================
# SAFE PATTERNS (Should pass guardrail validation)
# ============================================================================

def safe_login_check_parameterized(username, password, db_connection):
    """
    SAFE: Uses parameterized queries
    """
    query = "SELECT * FROM users WHERE username=? AND password=?"
    cursor = db_connection.cursor()
    cursor.execute(query, (username, password))
    return cursor.fetchone()


def safe_search_orm(search_term, session):
    """
    SAFE: Uses ORM (SQLAlchemy example)
    """
    from sqlalchemy import select
    from models import Product
    
    stmt = select(Product).where(Product.name.like(f"%{search_term}%"))
    return session.execute(stmt).scalars().all()


def safe_delete_prepared(user_id, db_connection):
    """
    SAFE: Uses prepared statement with parameter binding
    """
    query = "DELETE FROM users WHERE id = ?"
    cursor = db_connection.cursor()
    cursor.execute(query, (user_id,))
    db_connection.commit()


# ============================================================================
# DEMO EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("SQL Injection Vulnerability Demo")
    print("=" * 60)
    print("\nThis script demonstrates vulnerable vs safe SQL patterns")
    print("for educational purposes and guardrail testing.\n")
    
    # Show vulnerable pattern
    print("VULNERABLE PATTERN:")
    print(vulnerable_login_check("admin", "password123"))
    print("\nAttack example:")
    print(vulnerable_login_check("admin' --", "anything"))
    
    print("\n" + "=" * 60)
    print("\nSAFE PATTERN:")
    print("Uses parameterized queries with ? placeholders")
    print("Query: SELECT * FROM users WHERE username=? AND password=?")
    print("Parameters: ('admin', 'password123')")
