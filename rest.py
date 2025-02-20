import os
from dotenv import load_dotenv

load_dotenv()  # .env 파일을 읽어오는 함수.

print(os.getenv("UPBIT_ACCESS_KEY"))
print(os.getenv("UPBIT_SECRET_KEY"))
print(os.getenv("OPENAI_API_KEY"))
