"""
Chapterization logic. Replace the function below with your own version of chapterization logic.
"""

import pandas as pd

def chapterize(df: pd.DataFrame) -> pd.DataFrame:
    df['text'] = df[['file_name', 'chapter_id', 'text']].groupby(['file_name', 'chapter_id'])['text'].transform(lambda x: '\n'.join(x))
    df = df[['file_name', 'chapter_id', 'text']].drop_duplicates()
    return df
