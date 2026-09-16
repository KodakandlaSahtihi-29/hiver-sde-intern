import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')

apple = pd.read_parquet('data/raw/apple_sample.parquet')
print('Total Apple rows:', len(apple))

count = 0
for idx, row in apple.iterrows():
    conv = str(row['conversation'])
    if 'Customer:' in conv and 'Support:' in conv:
        lines = [l.strip() for l in conv.strip().split('\n') if l.strip()]
        c_msgs = [l for l in lines if l.startswith('Customer:')]
        s_msgs = [l for l in lines if l.startswith('Support:')]
        if c_msgs and s_msgs and len(c_msgs[0]) > 30:
            cid = row.get('conversation_id', f'row_{idx}')
            print(f"=== Thread {cid} ===")
            print("CUSTOMER:", c_msgs[0][:150])
            print("SUPPORT:", s_msgs[0][:150])
            print("-" * 50)
            count += 1
            if count >= 10:
                break
