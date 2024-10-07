import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Generate unique review IDs
review_ids = [f'review_{i}' for i in range(10000)]

# Generate product IDs
product_ids = [f'product_{i}' for i in range(1000)]

# Generate customer IDs
customer_ids = [f'customer_{i}' for i in range(5000)]

# Generate ratings
ratings = np.random.randint(1, 6, size=10000)

# Generate created_at timestamps
start_date = datetime(2020, 1, 1)
end_date = datetime(2023, 1, 1)
time_between_dates = end_date - start_date
days_between_dates = time_between_dates.days
random_days = np.random.randint(days_between_dates, size=10000)
created_at = [start_date + timedelta(days=int(random_day)) for random_day in random_days]

# Create a DataFrame
data = {
    'review_id': review_ids,
    'product_id': np.random.choice(product_ids, size=10000),
    'customer_id': np.random.choice(customer_ids, size=10000),
    'rating': ratings,
    'created_at': created_at
}
df = pd.DataFrame(data)

# Save the DataFrame as a Parquet file
df.to_csv('./sds/reviews.csv', index=False)