import os
from dotenv import load_dotenv
import json
import pyupbit
import pandas as pd
from datetime import datetime, timedelta
load_dotenv()


class CryptoDataCollector:
    def __init__(self, ticker="KRW-BTC"):
        self.ticker = ticker
        self.access = os.getenv('UPBIT_ACCESS_KEY')
        self.secret = os.getenv('UPBIT_SECRET_KEY')
        self.upbit = pyupbit.Upbit(self.access, self.secret)


    def get_current_status(self):
        """현재 투자 상태 조회"""
        try:
            krw_balance = float(self.upbit.get_balance("KRW"))  # 보유 현금
            crypto_balance = float(self.upbit.get_balance(self.ticker))  # 보유 암호화폐
            avg_buy_price = float(self.upbit.get_avg_buy_price(self.ticker))  # 평균 매수가
            current_price = float(pyupbit.get_current_price(self.ticker))  # 현재가

            total_value = krw_balance + (crypto_balance * current_price)

            return {
                "krw_balance": krw_balance,
                "crypto_balance": crypto_balance,
                "avg_buy_price": avg_buy_price,
                "current_price": current_price,
                "total_value": total_value,
                "unrealized_profit": ((current_price - avg_buy_price) * crypto_balance) if crypto_balance else 0
            }
        except Exception as e:
            print(f"Error in get_current_status: {e}")
            return None


    def get_orderbook_data(self):
        """호가 데이터 조회"""
        try:
            orderbook = pyupbit.get_orderbook(ticker="KRW-BTC")

            if not orderbook or len(orderbook) == 0:
                return None

            #orderbook = orderbook[0]  # 첫 번째 요소가 현재 호가 정보

            ask_prices = []
            ask_sizes = []
            bid_prices = []
            bid_sizes = []

            for unit in orderbook['orderbook_units'][:5]:
                ask_prices.append(unit['ask_price'])
                ask_sizes.append(unit['ask_size'])
                bid_prices.append(unit['bid_price'])
                bid_sizes.append(unit['bid_size'])

            return {
                "timestamp": datetime.fromtimestamp(orderbook['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S'),
                "total_ask_size": float(orderbook['total_ask_size']),
                "total_bid_size": float(orderbook['total_bid_size']),
                "ask_prices": ask_prices,
                "ask_sizes": ask_sizes,
                "bid_prices": bid_prices,
                "bid_sizes": bid_sizes
            }
        except Exception as e:
            print(f"Error in get_orderbook_data: {e}")
            return None


    def get_ohlcv_data(self):
        """차트 데이터 수집"""
        try:
            # 30일 일봉 데이터
            daily_data = pyupbit.get_ohlcv(self.ticker, interval="day", count=30)

            # 24시간 시간봉 데이터
            hourly_data = pyupbit.get_ohlcv(self.ticker, interval="minute60", count=24)

            # 이동평균선 계산
            daily_data['MA5'] = daily_data['close'].rolling(window=5).mean()
            daily_data['MA20'] = daily_data['close'].rolling(window=20).mean()

            # DataFrame을 dict로 변환시 datetime index 처리
            daily_data_dict = []
            for index, row in daily_data.iterrows():
                day_data = row.to_dict()
                day_data['date'] = index.strftime('%Y-%m-%d')
                daily_data_dict.append(day_data)

            hourly_data_dict = []
            for index, row in hourly_data.iterrows():
                hour_data = row.to_dict()
                hour_data['date'] = index.strftime('%Y-%m-%d %H:%M:%S')
                hourly_data_dict.append(hour_data)

            return {
                "daily_data": daily_data_dict,
                "hourly_data": hourly_data_dict
            }
        except Exception as e:
            print(f"Error in get_ohlcv_data: {e}")
            return None


def ai_trading():
    try:
        collector = CryptoDataCollector("KRW-BTC")

        # 1. 현재 투자 상태 조회
        current_status = collector.get_current_status()
        print("\n=== Current Investment Status ===")
        print(json.dumps(current_status, indent=2))

        # 2. 호가 데이터 조회
        orderbook_data = collector.get_orderbook_data()
        print("\n=== Current Orderbook ===")
        print(json.dumps(orderbook_data, indent=2))

        # 3. 차트 데이터 수집
        ohlcv_data = collector.get_ohlcv_data()

        # 4. OpenAI에 데이터 제공
        # from openai import OpenAI
        # client = OpenAI()

        # 4. Cerebras SDK를 사용하여 OpenAI에 데이터 제공
        from cerebras.cloud.sdk import Cerebras

        client = Cerebras(
            api_key=os.environ.get(
                "CEREBRAS_API_KEY"
            ),  # This is the default and can be omitted
        )

        # 분석을 위한 데이터 준비
        analysis_data = {
            "current_status": current_status,
            "orderbook": orderbook_data,
            "ohlcv": ohlcv_data
        }

        response = client.chat.completions.create(
            model="llama-3.3-70b",
            messages=[
                {
                    "role": "system",
                    "content": """You are an expert in Bitcoin investing. Analyze the provided data and make a decision based on:
                    1. Current market status
                    2. Orderbook analysis (market depth)
                    3. Technical analysis (OHLCV data)
                    4. Current position status

                    Your response should be in the following format:
                    {
                        "decision": "<buy/sell/hold>",
                        "reason": "<detailed analysis>",
                        "risk_level": "<low/medium/high>",
                        "confidence_score": <0-100>
                    }"""
                },
                {
                    "role": "user",
                    "content": f"Please analyze this market data and provide your decision: {json.dumps(analysis_data)}"
                }
            ]
        )


        result_text = response.choices[0].message.content
        # 응답에서 JSON 부분만 추출
        try:
            result = json.loads(result_text)
        except json.JSONDecodeError:
            # JSON 파싱 실패 시 텍스트에서 JSON 형식 찾기
            import re
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                raise Exception("Failed to parse AI response")


        print("\n=== AI Analysis Result ===")
        print(json.dumps(result, indent=2))


        # 5. 거래 실행
        if result['decision'] == "buy" and result.get('confidence_score', 0) > 70:
            krw = collector.upbit.get_balance("KRW")
            if krw > 5000:  # 최소 주문금액
                order = collector.upbit.buy_market_order(collector.ticker, krw * 0.9995)
                print("\n=== Buy Order Executed ===")
                print(json.dumps(order, indent=2))

        elif result['decision'] == "sell" and result.get('confidence_score', 0) > 70:
            btc = collector.upbit.get_balance(collector.ticker)
            current_price = pyupbit.get_current_price(collector.ticker)

            if btc * current_price > 5000:
                order = collector.upbit.sell_market_order(collector.ticker, btc)
                print("\n=== Sell Order Executed ===")
                print(json.dumps(order, indent=2))


    except Exception as e:
        print(f"Error in ai_trading: {e}")


if __name__ == "__main__":
    import time

    print("Starting Bitcoin Trading Bot...")
    ai_trading()
    # while True:
    #     try:
    #         ai_trading()
    #         time.sleep(60)  # 1분 간격으로 실행
    #     except Exception as e:
    #         print(f"Error in main loop: {e}")
    #         time.sleep(60)  # 에러 발생 시에도 1분 대기
