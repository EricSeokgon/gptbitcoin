import os
from dotenv import load_dotenv

load_dotenv()


# 1. 업비트 차트 데이터 가져오기 (30일 데이터)
import pyupbit

df = pyupbit.get_ohlcv("KRW-BTC", count=30, interval="day")
print(df.to_json())


# 2. OpenAI에게 데이터 제공하고 판단받기
from cerebras.cloud.sdk import Cerebras

client = Cerebras(
    api_key=os.environ.get(
        "CEREBRAS_API_KEY"
    ),  # This is the default and can be omitted
)


response = client.chat.completions.create(
    model="llama3.1-8b",
    messages=[
        {
            "role": "system",
            "content": "You are an expert in Bitcoin investing. Tell me whether to buy, sell, or hold at the moment based on the chart data provided. Response in Json format",
        },
        {
            "role": "user",
            "content": df.to_json(),
        },
        {
            "role": "assistant",
            "content": "reason : The chart data indicates some volatility with recent high price peaks and dips, but there is no clear uptrend or downtrend. Although there was significant trading volume and value spikes recently, likely driven by short-term market sentiment, it's advisable to hold as the market may stabilize or trend clearer soon. The decision avoids potential losses from premature selling or buying.",
        },
    ],
    response_format={"type": "text"},
)

result = response.choices[0].message.content
print(result)
print(type(result))
