import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Generate unique payment IDs
payment_ids = [f'payment_{i}' for i in range(10000)]

# Generate order IDs (assuming 1000 unique orders)
order_ids = [f'order_{i}' for i in range(1000)] * 10

# Generate customer IDs (assuming 500 unique customers)
customer_ids = [f'customer_{i}' for i in range(500)] * 20

# Generate random amounts
amounts = np.random.uniform(10, 1000, size=10000)

# Generate payment methods
payment_methods = np.random.choice(['credit_card', 'paypal', 'bank_transfer', 'cash'], size=10000, p=[0.6, 0.2, 0.1, 0.1])

# Generate payment statuses
payment_statuses = np.random.choice(['success', 'failed', 'refund'], size=10000, p=[0.9, 0.05, 0.05])

# Generate timestamps
start_date = datetime(2022, 1, 1)
end_date = datetime(2023, 1, 1)
time_between_dates = end_date - start_date
days_between_dates = time_between_dates.days
random_days = np.random.randint(days_between_dates, size=10000)
created_at = [start_date + timedelta(days=int(random_day)) for random_day in random_days]

# Create a DataFrame
data = {'payment_id': payment_ids,
        'order_id': order_ids,
        'customer_id': customer_ids,
        'amount': amounts,
        'payment_method': payment_methods,
        'payment_status': payment_statuses,
        'created_at': created_at}

df = pd.DataFrame(data)

# Save the DataFrame as a Parquet file
df.to_csv('./sds/payments.csv', index=False)