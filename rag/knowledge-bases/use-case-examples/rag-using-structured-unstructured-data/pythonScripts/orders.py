import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()

# Generate customer IDs
customer_ids = [fake.uuid4() for _ in range(1000)]

# Generate order data
orders = []
for _ in range(10000):
    order_id = fake.uuid4()
    customer_id = np.random.choice(customer_ids)
    order_total = round(np.random.uniform(10, 1000), 2)
    order_status = np.random.choice(['pending', 'shipped', 'delivered'])
    payment_method = np.random.choice(['credit_card', 'debit_card', 'paypal', 'cash_on_delivery'])
    shipping_address = fake.address()
    created_at = fake.date_time_between(start_date='-1y', end_date='now')
    updated_at = created_at + timedelta(days=np.random.randint(1, 30))
    orders.append([order_id, customer_id, order_total, order_status, payment_method, shipping_address, created_at, updated_at])

# Create DataFrame
columns = ['order_id', 'customer_id', 'order_total', 'order_status', 'payment_method', 'shipping_address', 'created_at', 'updated_at']
df = pd.DataFrame(orders, columns=columns)

# Convert datetime objects to strings
df['created_at'] = df['created_at'].dt.strftime('%Y-%m-%d %H:%M:%S')
df['updated_at'] = df['updated_at'].dt.strftime('%Y-%m-%d %H:%M:%S')

# Save DataFrame as Parquet file
df.to_csv('./sds/orders.csv', index=False)