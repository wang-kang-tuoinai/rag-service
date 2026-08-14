import time, requests
from pathlib import Path

OUT = Path("docs/go-official")
OUT.mkdir(parents=True, exist_ok=True)

session = requests.Session()
session.headers.update({"User-Agent": "RAGBot/1.0 (wangkang5156@gmail.com)"})   # 写个能标识自己的 UA

for i in range(6236, 6252):
    url = f"https://learnku.com/docs/effective-go/{i}.md"
    try:
        r = session.get(url, timeout=10)
        r.raise_for_status()
        r.encoding = "utf-8"          # 中文站点建议显式指定,避免乱码
    except Exception as e:
        print(f"[FAIL] {i}: {e}")
        continue
    (OUT / f"{i}.md").write_text(r.text, encoding="utf-8")
    print(f"[OK] {i}  {len(r.text)} 字")
    time.sleep(1)  