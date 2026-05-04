import pandas as pd
from collections import Counter
df = pd.read_parquet('gretel_sql_cache.parquet')
print('Total rows:', len(df))
print('Columns:', list(df.columns))
cats = Counter(df['sql_complexity'].str.lower().str.strip())
print('Complexity distribution:')
for k,v in cats.most_common():
    print(' ', k, ':', v)
