import os
from dotenv import load_dotenv
import json
import pyupbit
import pandas as pd
import ta
from datetime import datetime, timedelta
from openai import OpenAI
from cerebras.cloud.sdk import Cerebras
import time


load_dotenv()


class EnhancedCryptoTrader:
    def __init__(self, ticker="KRW-BTC"):
        self.ticker = ticker
        self.access = os.getenv('UPBIT_ACCESS_KEY')
        self.secret = os.getenv('UPBIT_SECRET_KEY')
        self.upbit = pyupbit.Upbit(self.access, self.secret)
        #self.client = OpenAI()
        self.client = Cerebras(
        api_key=os.environ.get(
            "CEREBRAS_API_KEY"
        ),  # This is the default and can be omitted
    )


    def add_technical_indicators(self, df):
        """기술적 분석 지표 추가"""
        # 볼린저 밴드
        indicator_bb = ta.volatility.BollingerBands(close=df['close'])
        df['bb_high'] = indicator_bb.bollinger_hband()
        df['bb_mid'] = indicator_bb.bollinger_mavg()
        df['bb_low'] = indicator_bb.bollinger_lband()
        df['bb_pband'] = indicator_bb.bollinger_pband()

        # RSI
        df['rsi'] = ta.momentum.RSIIndicator(close=df['close']).rsi()

        # MACD
        macd = ta.trend.MACD(close=df['close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_diff'] = macd.macd_diff()

        # 이동평균선
        df['ma5'] = ta.trend.SMAIndicator(close=df['close'], window=5).sma_indicator()
        df['ma20'] = ta.trend.SMAIndicator(close=df['close'], window=20).sma_indicator()
        df['ma60'] = ta.trend.SMAIndicator(close=df['close'], window=60).sma_indicator()
        df['ma120'] = ta.trend.SMAIndicator(close=df['close'], window=120).sma_indicator()

        # ATR
        df['atr'] = ta.volatility.AverageTrueRange(
            high=df['high'], low=df['low'], close=df['close']
        ).average_true_range()

        return df


    def get_current_status(self):
        """현재 투자 상태 조회"""
        try:
            krw_balance = float(self.upbit.get_balance("KRW"))
            crypto_balance = float(self.upbit.get_balance(self.ticker))
            avg_buy_price = float(self.upbit.get_avg_buy_price(self.ticker))
            current_price = float(pyupbit.get_current_price(self.ticker))

            print("\n=== Current Investment Status ===")
            print(f"보유 현금: {krw_balance:,.0f} KRW")
            print(f"보유 코인: {crypto_balance:.8f} {self.ticker}")
            print(f"평균 매수가: {avg_buy_price:,.0f} KRW")
            print(f"현재가: {current_price:,.0f} KRW")

            total_value = krw_balance + (crypto_balance * current_price)
            unrealized_profit = ((current_price - avg_buy_price) * crypto_balance) if crypto_balance else 0
            profit_percentage = ((current_price / avg_buy_price) - 1) * 100 if crypto_balance else 0

            print(f"미실현 손익: {unrealized_profit:,.0f} KRW ({profit_percentage:.2f}%)")

            return {
                "krw_balance": krw_balance,
                "crypto_balance": crypto_balance,
                "avg_buy_price": avg_buy_price,
                "current_price": current_price,
                "total_value": total_value,
                "unrealized_profit": unrealized_profit,
                "profit_percentage": profit_percentage
            }
        except Exception as e:
            print(f"Error in get_current_status: {e}")
            return None


    def get_orderbook_data(self):
        """호가 데이터 조회"""
        try:
            orderbook = pyupbit.get_orderbook(ticker=self.ticker)
            if not orderbook or len(orderbook) == 0:
                return None

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
        """차트 데이터 수집 및 기술적 분석"""
        try:
            daily_data = pyupbit.get_ohlcv(self.ticker, interval="day", count=30)
            daily_data = self.add_technical_indicators(daily_data)

            hourly_data = pyupbit.get_ohlcv(self.ticker, interval="minute60", count=24)
            hourly_data = self.add_technical_indicators(hourly_data)

            # DataFrame을 dict로 변환
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

            # 최신 기술적 지표 출력
            print("\n=== Latest Technical Indicators ===")
            print(f"RSI: {daily_data['rsi'].iloc[-1]:.2f}")
            print(f"MACD: {daily_data['macd'].iloc[-1]:.2f}")
            print(f"BB Position: {daily_data['bb_pband'].iloc[-1]:.2f}")

            return {
                "daily_data": daily_data_dict[-7:],  # 최근 7일만
                "hourly_data": hourly_data_dict[-6:],  # 최근 6시간만
                "latest_indicators": {
                    "rsi": daily_data['rsi'].iloc[-1],
                    "macd": daily_data['macd'].iloc[-1],
                    "macd_signal": daily_data['macd_signal'].iloc[-1],
                    "bb_position": daily_data['bb_pband'].iloc[-1]
                }
            }
        except Exception as e:
            print(f"Error in get_ohlcv_data: {e}")
            return None


    def get_ai_analysis(self, analysis_data):
        """AI 분석 및 매매 신호 생성"""
        try:
            # 데이터 최적화
            optimized_data = {
                "current_status": analysis_data["current_status"],
                "orderbook": {
                    "timestamp": analysis_data["orderbook"]["timestamp"],
                    "total_ask_size": analysis_data["orderbook"]["total_ask_size"],
                    "total_bid_size": analysis_data["orderbook"]["total_bid_size"],
                    "ask_prices": analysis_data["orderbook"]["ask_prices"][:3],
                    "bid_prices": analysis_data["orderbook"]["bid_prices"][:3],
                },
                "ohlcv": analysis_data["ohlcv"]
            }


            prompt = """분석해서 다음 JSON 형식으로 응답하세요:
{
    "decision": "buy/sell/hold",
    "reason": "분석 설명",
    "risk_level": "low/medium/high",
    "confidence_score": 0-100
}"""


            response = self.client.chat.completions.create(
                model="llama-3.3-70b",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Market data for analysis: {json.dumps(optimized_data)}"}
                ]
            )


            result_text = response.choices[0].message.content

            try:
                result = json.loads(result_text)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    raise Exception("Failed to parse AI response")


            return result


        except Exception as e:
            print(f"Error in get_ai_analysis: {e}")
            return None


    def execute_trade(self, decision, confidence_score):
        """매매 실행"""
        try:
            if decision == "buy" and confidence_score > 70:
                krw = self.upbit.get_balance("KRW")
                if krw > 5000:  # 최소 주문금액
                    order = self.upbit.buy_market_order(self.ticker, krw * 0.9995)
                    print("\n=== Buy Order Executed ===")
                    print(json.dumps(order, indent=2))

            elif decision == "sell" and confidence_score > 70:
                btc = self.upbit.get_balance(self.ticker)
                current_price = pyupbit.get_current_price(self.ticker)

                if btc * current_price > 5000:
                    order = self.upbit.sell_market_order(self.ticker, btc)
                    print("\n=== Sell Order Executed ===")
                    print(json.dumps(order, indent=2))

        except Exception as e:
            print(f"Error in execute_trade: {e}")


def ai_trading():
    try:
        trader = EnhancedCryptoTrader("KRW-BTC")

        # 1. 현재 투자 상태 조회
        current_status = trader.get_current_status()

        # 2. 호가 데이터 조회
        orderbook_data = trader.get_orderbook_data()

        # 3. 차트 데이터 수집
        ohlcv_data = trader.get_ohlcv_data()

        # 4. AI 분석을 위한 데이터 준비
        if all([current_status, orderbook_data, ohlcv_data]):
            analysis_data = {
                "current_status": current_status,
                "orderbook": orderbook_data,
                "ohlcv": ohlcv_data
            }

            # 5. AI 분석 실행
            ai_result = trader.get_ai_analysis(analysis_data)

            if ai_result:
                print("\n=== AI Analysis Result ===")
                print(json.dumps(ai_result, indent=2))

                # 6. 매매 실행
                trader.execute_trade(ai_result['decision'], ai_result['confidence_score'])

    except Exception as e:
        print(f"Error in ai_trading: {e}")


if __name__ == "__main__":
    print("Starting Enhanced Bitcoin Trading Bot...")
    print("Press Ctrl+C to stop")

    while True:
        try:
            ai_trading()
            time.sleep(600)  # 10분 대기
        except KeyboardInterrupt:
            print("\nTrading bot stopped by user")
            break
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(60)  # 에러 발생 시에도 60초 대기
