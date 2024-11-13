---
tags:
    - Agent/ Code-Interpreter
    - RAG/ Data-Ingestion
---

!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/agents-and-function-calling/bedrock-agents/test-agent/generate_syntetic_data.ipynb){:target="_blank"}"

<h2>Support notebook to generate test data</h2>

This notebook generates test data for [Amazon Bedrock Agents](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html) chat with a document and code interpretation capabilities.

<h2>Create synthetic stock price data</h2>
We will use a CSV of stock price data for the non-existent company 'FAKECO'; we create it here.


```python
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
def make_synthetic_stock_data(filename):
    # Define the start and end dates
    start_date = datetime(2023, 6, 27)
    end_date = datetime(2024, 6, 27)

    # Create a date range
    date_range = pd.date_range(start_date, end_date, freq='D')

    # Initialize lists to store the data
    symbol = []
    dates = []
    open_prices = []
    high_prices = []
    low_prices = []
    close_prices = []
    adj_close_prices = []
    volumes = []

    # Set the initial stock price
    initial_price = 100.0

    # Generate plausible stock prices
    for date in date_range:
        symbol.append('FAKECO')
        dates.append(date)
        open_price = np.round(initial_price + np.random.uniform(-1, 1), 2)
        high_price = np.round(open_price + np.random.uniform(0, 5), 2)
        low_price = np.round(open_price - np.random.uniform(0, 5), 2)
        close_price = np.round(np.random.uniform(low_price, high_price), 2)
        adj_close_price = close_price
        volume = np.random.randint(1000, 10000000)

        open_prices.append(open_price)
        high_prices.append(high_price)
        low_prices.append(low_price)
        close_prices.append(close_price)
        adj_close_prices.append(adj_close_price)
        volumes.append(volume)

        initial_price = close_price

    # Create a DataFrame
    data = {
        'Symbol': symbol,
        'Date': dates,
        'Open': open_prices,
        'High': high_prices,
        'Low': low_prices,
        'Close': close_prices,
        'Adj Close': adj_close_prices,
        'Volume': volumes
    }

    stock_data = pd.DataFrame(data)

    # Save the dataframe
    stock_data.to_csv(filename, index=False)
```

<h3>Save data</h3>


```python
<h2>Insure the output directory exists</h2>
import os
if not os.path.exists('output'):
    os.makedirs('output')

stock_file = os.path.join('output', 'FAKECO.csv')
if not os.path.exists(stock_file):
    make_synthetic_stock_data(stock_file)
```
