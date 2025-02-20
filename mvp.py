import os
from dotenv import load_dotenv

load_dotenv()


# 1. 업비트 차트 데이터 가져오기 (30일 데이터)
import pyupbit

df = pyupbit.get_ohlcv("KRW-BTC", count=30, interval="day")
print(df.to_json())


# 2. OpenAI에게 데이터 제공하고 판단받기
from openai import OpenAI

client = OpenAI()


response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": 'You are an expert in Bitcoin investing. Tell me whether to buy, sell, or hold at the moment based on the chart data provided. Response in Json format.\n\nResponse Example:\n{decision: "buy", "reason": "some technical reason"}\n{decision: "sell", "reason": "some technical reason"}\n{decision: "hold", "reason": "some technical reason"}\n\n\n',
                }
            ],
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "```User 메시지에 입력된 차트 데이터 ```"}
            ],
        },
        {
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": '{\n  "decision": "hold",\n  "reason": "The chart data indicates some volatility with recent high price peaks and dips, but there is no clear uptrend or downtrend. Although there was significant trading volume and value spikes recently, likely driven by short-term market sentiment, it\'s advisable to hold as the market may stabilize or trend clearer soon. The decision avoids potential losses from premature selling or buying."\n}\n```',
                }
            ],
        },
    ],
    response_format={"type": "text"},
    temperature=1,
    max_completion_tokens=2048,
    top_p=1,
    frequency_penalty=0,
    presence_penalty=0,
)
