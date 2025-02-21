import os
from dotenv import load_dotenv
import json

load_dotenv()


def ai_trading():
    # 1. 업비트 차트 데이터 가져오기 (30일 데이터)
    import pyupbit

    df = pyupbit.get_ohlcv("KRW-BTC", count=30, interval="day")
    # print(df.to_json())

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
                "content": "You are an expert in Bitcoin investing. Tell me whether to buy, sell, or hold at the moment based on the chart data provided. Response in Json format.\n\nResponse Example:\n{decision: 'buy', 'reason': 'some technical reason'}\n{decision: 'sell', 'reason': 'some technical reason'}\n{decision: 'hold', 'reason': 'some technical reason'}\n\n\n",
            },
            {"role": "user", "content": df.to_json()},
        ],
        response_format={"type": "json_object"},  # text 대신 json_object로 수정
    )

    result = response.choices[0].message.content
    result = json.loads(result)
    print(result)
    print(type(result))

    import pyupbit

    access = os.getenv("UPBIT_ACCESS_KEY")
    secret = os.getenv("UPBIT_SECRET_KEY")
    upbit = pyupbit.Upbit(access, secret)

    print("### AI Decision: ", result["decision"].upper(), "###")
    print("### Reason: ", result["reason"], "###")

    if result['decision'] == "buy":
    # 매수
        my_krw =upbit.get_balance("KRW")
        if my_krw*0.9995 > 5000:
            print("### Buy Order Executed ###")
            print(upbit.buy_market_order("KRW-BTC",my_krw*0.9995))


        else :
            print("### Buy Order Failed: Insufficient KRW (less than 5000 KRW) ###")
    elif result['decision'] == "sell":
    # 매도
        my_btc =upbit.get_balance("KRW-BTC")
        current_price = pyupbit.get_orderbook(ticker="KRW-BTC")['orderbook_units'][0]["ask_price"]

        if my_btc*current_price > 5000 :
            print("### Sell Order Executed ###")
            print(upbit.sell_market_order("KRW-BTC",upbit.get_balance("KRW-BTC")))
        else :
            print("### Sell Order Failed: Insufficient BTC (less than 5000 KRW) ###")
    elif result['decision'] == "hold":
    # 보유
        print("sell:",result["reason"])



# if result["decision"] == "buy":
#         # 매수
#         my_krw = upbit.get_balance("KRW")
#         if my_krw * 0.9995 > 5000:
#             print("### Buy Order Executed ###")
#             print(upbit.buy_market_order("KRW-BTC", my_krw * 0.9995))

#         else:
#             print("### Buy Order Failed: Insufficient KRW (less than 5000 KRW) ###")
#     elif result["decision"] == "sell":
#         # 매도
#         my_btc = upbit.get_balance("KRW-BTC")
#         current_price = pyupbit.get_orderbook(ticker="KRW-BTC")["orderbook_units"][0][
#             "ask_price"
#         ]

#         if my_btc * current_price > 5000:
#             print("### Sell Order Executed ###")
#             print(upbit.sell_market_order("KRW-BTC", upbit.get_balance("KRW-BTC")))
#         else:
#             print("### Sell Order Failed: Insufficient BTC (less than 5000 KRW) ###")
#     elif result["decision"] == "hold":
#         # 보유
#         print("sell:", result["reason"])
ai_trading()

# while True:
#     import time

#     # 10초마다 실행
#     time.sleep(10)
#     ai_trading()
