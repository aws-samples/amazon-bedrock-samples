import sqlite3
from faker import Faker
import random

# Initialize Faker
fake = Faker()

# Shoe categories and their related attributes
SHOE_CATEGORIES = {
    "Running": {
        "brands": ["Nike", "Adidas", "Brooks", "Asics", "New Balance"],
        "features": ["Cushioning", "Breathable", "Lightweight", "Stability"],
        "price_range": (80, 200),
    },
    "Hiking": {
        "brands": ["Merrell", "Columbia", "The North Face", "Salomon", "Keen"],
        "features": ["Waterproof", "Durable", "Ankle Support", "Grip"],
        "price_range": (100, 250),
    },
    "Casual": {
        "brands": ["Vans", "Converse", "Puma", "Reebok", "Skechers"],
        "features": ["Comfortable", "Stylish", "Versatile", "Classic"],
        "price_range": (50, 120),
    },
    "Basketball": {
        "brands": ["Nike", "Jordan", "Under Armour", "Adidas", "Puma"],
        "features": ["Ankle Support", "Court Grip", "Cushioning", "Durability"],
        "price_range": (90, 200),
    },
}


def create_database():
    conn = sqlite3.connect("shoe_store.db")
    cursor = conn.cursor()

    # Create shoes table
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS shoes (
        id INTEGER PRIMARY KEY,
        name TEXT,
        brand TEXT,
        category TEXT,
        features TEXT,
        price REAL,
        size REAL,
        color TEXT,
        stock INTEGER
    )
    """
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        name TEXT,
        email TEXT UNIQUE,
        phone TEXT,
        address TEXT,
        city TEXT,
        state TEXT,
        zip_code TEXT,
        preferred_category TEXT,
        created_at TEXT
    )
    """
    )

    # Create shopping cart table
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS shopping_cart (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        shoe_id INTEGER,
        quantity INTEGER,
        size REAL,
        added_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (shoe_id) REFERENCES shoes (id)
    )
    """
    )
    conn.commit()
    return conn, cursor


def generate_shoe_data(num_records):
    conn, cursor = create_database()

    for _ in range(num_records):
        # Randomly select a category and its attributes
        category = random.choice(list(SHOE_CATEGORIES.keys()))
        category_data = SHOE_CATEGORIES[category]

        # Generate shoe data
        brand = random.choice(category_data["brands"])
        features = ", ".join(
            random.sample(category_data["features"], k=random.randint(2, 4))
        )
        price = round(random.uniform(*category_data["price_range"]), 2)
        size = round(random.uniform(6.0, 13.0), 1)
        color = fake.color_name()
        stock = random.randint(0, 50)
        name = f"{brand} {category} {fake.word().title()}"

        # Insert data into database
        cursor.execute(
            """
        INSERT INTO shoes (name, brand, category, features, price, size, color, stock)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (name, brand, category, features, price, size, color, stock),
        )

    conn.commit()
    conn.close()


def generate_user_data(num_users):
    conn, cursor = create_database()

    for _ in range(num_users):
        name = fake.name()
        email = fake.email()
        phone = fake.phone_number()
        address = fake.street_address()
        city = fake.city()
        state = fake.state()
        zip_code = fake.zipcode()
        preferred_category = random.choice(list(SHOE_CATEGORIES.keys()))
        created_at = fake.date_time_this_year().isoformat()

        try:
            cursor.execute(
                """
            INSERT INTO users (name, email, phone, address, city, state, zip_code, preferred_category, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    name,
                    email,
                    phone,
                    address,
                    city,
                    state,
                    zip_code,
                    preferred_category,
                    created_at,
                ),
            )
        except sqlite3.IntegrityError:
            # Skip if email already exists
            continue

    conn.commit()
    conn.close()


def generate_cart_data(num_records):
    conn = sqlite3.connect("shoe_store.db")
    cursor = conn.cursor()

    # Get all user IDs
    cursor.execute("SELECT id FROM users")
    user_ids = [row[0] for row in cursor.fetchall()]

    # Get all shoe IDs and their current stock
    cursor.execute("SELECT id, stock FROM shoes")
    shoe_data = cursor.fetchall()

    if not user_ids or not shoe_data:
        conn.close()
        return

    for _ in range(num_records):
        user_id = random.choice(user_ids)
        shoe_id, current_stock = random.choice(shoe_data)

        # Generate random quantity (1-3 items) and ensure it doesn't exceed stock
        quantity = min(random.randint(1, 3), current_stock)
        size = round(random.uniform(6.0, 13.0), 1)
        added_at = fake.date_time_this_year().isoformat()

        try:
            # Add to cart
            cursor.execute(
                """
            INSERT INTO shopping_cart (user_id, shoe_id, quantity, size, added_at)
            VALUES (?, ?, ?, ?, ?)
            """,
                (user_id, shoe_id, quantity, size, added_at),
            )

            # Update stock
            cursor.execute(
                """
            UPDATE shoes 
            SET stock = stock - ? 
            WHERE id = ?
            """,
                (quantity, shoe_id),
            )

        except sqlite3.IntegrityError:
            continue

    conn.commit()
    conn.close()


def display_results(shoes):
    if not shoes:
        print("No shoes found matching your preferences.")
        return

    print("\nFound the following shoes:")
    print("-" * 80)
    for shoe in shoes:
        print(f"Name: {shoe[1]}")
        print(f"Brand: {shoe[2]}")
        print(f"Category: {shoe[3]}")
        print(f"Features: {shoe[4]}")
        print(f"Price: ${shoe[5]:.2f}")
        print(f"Size: {shoe[6]}")
        print(f"Color: {shoe[7]}")
        print(f"Stock: {shoe[8]}")
        print("-" * 80)


if __name__ == "__main__":
    # Generate initial data
    generate_shoe_data(100)
    generate_user_data(10)
    generate_cart_data(10)
