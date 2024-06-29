import boto3

bucket = 'bucket' ### REPLACE WITH YOUR AMAZON S3 BUCKET

### Setup boto3 client for Athena
athena = boto3.client('athena', region_name='us-west-2')

### Create the Athena database
athena.start_query_execution(
    QueryString='CREATE DATABASE IF NOT EXISTS acme_bank',
    ResultConfiguration={
        'OutputLocation': f's3://{bucket}/athena/'
    }
)

### Create the transactions table
athena.start_query_execution(
    QueryString=f'''
        CREATE EXTERNAL TABLE IF NOT EXISTS acme_bank.transactions (
            user_id INT,
            user_name STRING,
            transaction_date DATE,
            amount DECIMAL(10,2)
        )
        ROW FORMAT DELIMITED
        FIELDS TERMINATED BY ','
        STORED AS TEXTFILE
        LOCATION 's3://{bucket}/acme/'
    ''',
    ResultConfiguration={
        'OutputLocation': f's3://{bucket}/athena/'
    }
)

### Insert synthetic example data
transactions_data = [
    (1, 'Tom Hanks', '2023-01-01', 500.00),
    (2, 'Meryl Streep', '2023-01-02', 1000.00),
    (3, 'Leonardo DiCaprio', '2023-01-03', 750.00),
    (1, 'Tom Hanks', '2023-01-04', 250.00),
    (2, 'Meryl Streep', '2023-01-05', 1500.00),
    (4, 'Denzel Washington', '2023-01-06', 1200.00),
    (5, 'Cate Blanchett', '2023-01-07', 850.00),
    (6, 'Morgan Freeman', '2023-01-08', 1100.00),
    (7, 'Viola Davis', '2023-01-09', 600.00),
    (8, 'Judi Dench', '2023-01-10', 900.00),
    (9, 'Tom Cruise', '2023-01-11', 1400.00),
    (10, 'Natalie Portman', '2023-01-12', 700.00),
    (11, 'Christian Bale', '2023-01-13', 1300.00),
    (12, 'Tilda Swinton', '2023-01-14', 550.00),
    (13, 'Brad Pitt', '2023-01-15', 1800.00),
    (14, 'Scarlett Johansson', '2023-01-16', 950.00),
    (15, 'Daniel Day-Lewis', '2023-01-17', 1600.00),
    (16, 'Cate Blanchett', '2023-01-18', 1050.00),
    (17, 'Denzel Washington', '2023-01-19', 1250.00),
    (18, 'Meryl Streep', '2023-01-20', 1700.00),
    (19, 'Leonardo DiCaprio', '2023-01-21', 1150.00),
    (20, 'Tom Hanks', '2023-01-22', 900.00),
    (21, 'Viola Davis', '2023-01-23', 650.00),
    (22, 'Morgan Freeman', '2023-01-24', 1350.00),
    (23, 'Judi Dench', '2023-01-25', 800.00),
    (24, 'Tom Cruise', '2023-01-26', 1550.00),
    (25, 'Natalie Portman', '2023-01-27', 750.00),
    (26, 'Christian Bale', '2023-01-28', 1450.00),
    (27, 'Tilda Swinton', '2023-01-29', 650.00),
    (28, 'Brad Pitt', '2023-01-30', 2000.00)
]

### Insert the example data
for transaction in transactions_data:
    athena.start_query_execution(
        QueryString=f"INSERT INTO acme_bank.transactions VALUES ({transaction[0]}, '{transaction[1]}', DATE '{transaction[2]}', {transaction[3]})",
        ResultConfiguration={
            'OutputLocation': f's3://{bucket}/athena/'
        }
    )