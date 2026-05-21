#!/usr/bin/env python3
"""
Safe SQL Query Examples
Demonstrates secure database query practices that prevent SQL injection
"""

import sqlite3
from typing import Optional, List, Dict


# ==============================================================================
# ✅ SAFE: Using Parameterized Queries
# ==============================================================================

def safe_login_sqlite(username: str, password: str) -> Optional[Dict]:
    """
    SAFE: Login using parameterized queries (SQLite).
    
    This prevents SQL injection by using placeholders.
    The database driver handles escaping automatically.
    """
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # ✅ SAFE: Using ? placeholders
    query = "SELECT * FROM users WHERE username = ? AND password = ?"
    cursor.execute(query, (username, password))
    
    result = cursor.fetchone()
    conn.close()
    
    return result


def safe_search_sqlite(search_term: str) -> List[Dict]:
    """
    SAFE: Search using parameterized queries.
    
    Even with LIKE queries, use parameterization.
    """
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()
    
    # ✅ SAFE: Parameterized LIKE query
    query = "SELECT * FROM products WHERE name LIKE ?"
    cursor.execute(query, (f'%{search_term}%',))
    
    results = cursor.fetchall()
    conn.close()
    
    return results


# ==============================================================================
# ✅ SAFE: Using SQLAlchemy ORM
# ==============================================================================

from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class User(Base):
    """User model for SQLAlchemy ORM."""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True)
    email = Column(String(100))
    password_hash = Column(String(255))


def safe_login_sqlalchemy(username: str, password_hash: str) -> Optional[User]:
    """
    SAFE: Login using SQLAlchemy ORM.
    
    ORM automatically handles parameterization and prevents SQL injection.
    """
    engine = create_engine('sqlite:///users.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # ✅ SAFE: ORM query - automatically parameterized
    user = session.query(User).filter(
        User.username == username,
        User.password_hash == password_hash
    ).first()
    
    session.close()
    return user


def safe_search_sqlalchemy(search_term: str) -> List[User]:
    """
    SAFE: Search using SQLAlchemy ORM with LIKE.
    """
    engine = create_engine('sqlite:///users.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # ✅ SAFE: ORM LIKE query - automatically parameterized
    users = session.query(User).filter(
        User.username.like(f'%{search_term}%')
    ).all()
    
    session.close()
    return users


# ==============================================================================
# ✅ SAFE: Using psycopg2 (PostgreSQL)
# ==============================================================================

import psycopg2


def safe_login_postgresql(username: str, password: str) -> Optional[Dict]:
    """
    SAFE: Login using parameterized queries (PostgreSQL).
    
    Uses %s placeholders for PostgreSQL.
    """
    conn = psycopg2.connect(
        dbname="mydb",
        user="dbuser",
        password="dbpass",
        host="localhost"
    )
    cursor = conn.cursor()
    
    # ✅ SAFE: Using %s placeholders (PostgreSQL style)
    query = "SELECT * FROM users WHERE username = %s AND password = %s"
    cursor.execute(query, (username, password))
    
    result = cursor.fetchone()
    conn.close()
    
    return result


# ==============================================================================
# ✅ SAFE: Dynamic Query Building (Advanced)
# ==============================================================================

def safe_dynamic_filter(filters: Dict[str, str]) -> List[Dict]:
    """
    SAFE: Build dynamic queries safely using parameterization.
    
    Even when building queries dynamically, use parameterization.
    """
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()
    
    # Build WHERE clause safely
    where_clauses = []
    params = []
    
    for field, value in filters.items():
        # ✅ SAFE: Whitelist allowed fields
        allowed_fields = ['name', 'category', 'price']
        if field in allowed_fields:
            where_clauses.append(f"{field} = ?")
            params.append(value)
    
    if where_clauses:
        query = "SELECT * FROM products WHERE " + " AND ".join(where_clauses)
    else:
        query = "SELECT * FROM products"
    
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()
    
    return results


# ==============================================================================
# ❌ VULNERABLE: What NOT to Do (For Educational Purposes Only)
# ==============================================================================

def vulnerable_login_example(username: str, password: str):
    """
    ❌ VULNERABLE: SQL Injection Risk!
    
    This is an example of what NOT to do.
    DO NOT USE THIS CODE IN PRODUCTION!
    
    Attack example:
    username = "admin' OR '1'='1' --"
    This would bypass authentication!
    """
    # ❌ DANGEROUS: String formatting creates SQL injection vulnerability
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    # If executed, this allows SQL injection attacks
    return query  # Not executing to prevent actual harm


# ==============================================================================
# 📚 Best Practices Summary
# ==============================================================================

def sql_security_best_practices():
    """
    Summary of SQL security best practices.
    """
    print("=" * 70)
    print("SQL Security Best Practices")
    print("=" * 70)
    print()
    print("✅ DO:")
    print("  1. Use parameterized queries (?, %s placeholders)")
    print("  2. Use ORM frameworks (SQLAlchemy, Django ORM)")
    print("  3. Whitelist allowed fields for dynamic queries")
    print("  4. Use prepared statements")
    print("  5. Validate and sanitize input")
    print("  6. Use least privilege database accounts")
    print("  7. Enable query logging for monitoring")
    print()
    print("❌ DON'T:")
    print("  1. Use string formatting (f-strings, %, +)")
    print("  2. Concatenate user input into queries")
    print("  3. Trust user input without validation")
    print("  4. Use dynamic SQL without parameterization")
    print("  5. Run database with admin privileges")
    print()
    print("🔍 SQL Injection Attack Examples:")
    print("  - ' OR '1'='1' --")
    print("  - '; DROP TABLE users; --")
    print("  - ' UNION SELECT password FROM users --")
    print()
    print("=" * 70)


# ==============================================================================
# 🧪 Testing Examples
# ==============================================================================

if __name__ == "__main__":
    print("Safe SQL Query Examples")
    print("=" * 70)
    print()
    
    # Show best practices
    sql_security_best_practices()
    
    print("\n✅ Safe Query Examples:")
    print("-" * 70)
    
    # Example 1: Parameterized query
    print("\n1. Parameterized Query (SQLite):")
    print("   query = 'SELECT * FROM users WHERE username = ?'")
    print("   cursor.execute(query, (username,))")
    
    # Example 2: ORM query
    print("\n2. ORM Query (SQLAlchemy):")
    print("   user = session.query(User).filter(User.username == username).first()")
    
    # Example 3: PostgreSQL parameterized
    print("\n3. Parameterized Query (PostgreSQL):")
    print("   query = 'SELECT * FROM users WHERE username = %s'")
    print("   cursor.execute(query, (username,))")
    
    print("\n" + "=" * 70)
    print("⚠️  Always use parameterized queries to prevent SQL injection!")
    print("=" * 70)
