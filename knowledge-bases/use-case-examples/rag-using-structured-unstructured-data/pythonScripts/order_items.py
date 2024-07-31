import pandas as pd
import numpy as np
from uuid import uuid4

# Generate 10000 order_item_id
order_item_ids = [str(uuid4()) for _ in range(10000)]

# Generate 1000 order_id
order_ids = [str(uuid4()) for _ in range(1000)]

# Generate 500 product_id
product_ids = [str(uuid4()) for _ in range(500)]

# Generate random quantities
quantities = np.random.randint(1, 11, size=10000)

# Generate random prices
prices = np.random.uniform(10, 100, size=10000)

# Create a DataFrame
data = {
    'order_item_id': order_item_ids,
    'order_id': np.random.choice(order_ids, size=10000, replace=True),
    'product_id': np.random.choice(product_ids, size=10000, replace=True),
    'quantity': quantities,
    'price': prices
}

df = pd.DataFrame(data)

# Save the DataFrame as a Parquet file
df.to_csv('./sds/order_items.csv', index=False)