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
import requests


load_dotenv()


class EnhancedCryptoTrader:
    def __init__(self, ticker="KRW-BTC"):
        self.ticker = ticker
        self.access = os.getenv('UPBIT_ACCESS_KEY')
        self.secret = os.getenv('UPBIT_SECRET_KEY')
        self.upbit = pyupbit.Upbit(self.access, self.secret)
        self.client = Cerebras(
        api_key=os.environ.get(
            "CEREBRAS_API_KEY"
        ),  # This is the default and can be omitted
    )
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.fear_greed_api = "https://api.alternative.me/fng/"

    def get_crypto_news(self):
        """비트코인 관련 최신 뉴스 조회"""
        try:
            base_url = "https://serpapi.com/search.json"
            params = {
                "engine": "google_news",
                "q": "bitcoin crypto trading",
                "api_key": self.serpapi_key,
                "gl": "us",  # 미국 뉴스
                "hl": "en"   # 영어 뉴스
            }

            response = requests.get(base_url, params=params)
            if response.status_code == 200:
                news_data = response.json()

                if 'news_results' not in news_data:
                    return None

                processed_news = []
                for news in news_data['news_results'][:5]:  # 상위 5개 뉴스만 처리
                    processed_news.append({
                        'title': news.get('title', ''),
                        'link': news.get('link', ''),
                        'source': news.get('source', {}).get('name', ''),
                        'date': news.get('date', ''),
                        'snippet': news.get('snippet', '')
                    })

                print("\n=== Latest Crypto News ===")
                for news in processed_news:
                    print(f"\nTitle: {news['title']}")
                    print(f"Source: {news['source']}")
                    print(f"Date: {news['date']}")

                return processed_news

            return None
        except Exception as e:
            print(f"Error in get_crypto_news: {e}")
            return None



    def get_fear_greed_index(self, limit=7):
        """공포탐욕지수 데이터 조회"""
        try:
            response = requests.get(f"{self.fear_greed_api}?limit={limit}")
            if response.status_code == 200:
                data = response.json()

                # 최신 공포탐욕지수 출력
                latest = data['data'][0]
                print("\n=== Fear and Greed Index ===")
                print(f"Current Value: {latest['value']} ({latest['value_classification']})")

                # 7일간의 데이터 가공
                processed_data = []
                for item in data['data']:
                    processed_data.append({
                        'date': datetime.fromtimestamp(int(item['timestamp'])).strftime('%Y-%m-%d'),
                        'value': int(item['value']),
                        'classification': item['value_classification']
                    })

                # 추세 분석
                values = [int(item['value']) for item in data['data']]
                avg_value = sum(values) / len(values)
                trend = 'Improving' if values[0] > avg_value else 'Deteriorating'

                return {
                    'current': {
                        'value': int(latest['value']),
                        'classification': latest['value_classification']
                    },
                    'history': processed_data,
                    'trend': trend,
                    'average': avg_value
                }

            return None
        except Exception as e:
            print(f"Error in get_fear_greed_index: {e}")
            return None

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
                "ohlcv": analysis_data["ohlcv"],
                "fear_greed": analysis_data["fear_greed"]  # 공포탐욕지수 데이터 추가
            }


            prompt = """Analyze the cryptocurrency market based on the following data and generate trading signals:
1. Technical Indicators (RSI, MACD, Bollinger Bands, etc.)
2. Order Book Data (Buy/Sell Volume)
3. Fear & Greed Index


Please consider the following key points:
- Fear & Greed Index below 20 (Extreme Fear) may present buying opportunities
- Fear & Greed Index above 80 (Extreme Greed) may present selling opportunities
- The trend of the Fear & Greed Index is also a crucial indicator


Please respond in the following JSON format:
{
    "decision": "buy/sell/hold",
    "reason": "detailed analysis explanation",
    "risk_level": "low/medium/high",
    "confidence_score": 0-100,
    "market_sentiment": "current market sentiment analysis"
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


    def execute_trade(self, decision, confidence_score, fear_greed_value):
        """매매 실행 (공포탐욕지수 고려)"""
        try:
            # 공포탐욕지수에 따른 매매 비율 조정
            if decision == "buy":
                # 극도의 공포 상태(0-25)에서는 더 과감한 매수
                if fear_greed_value <= 25:
                    trade_ratio = 0.9995  # 최대 매수
                elif fear_greed_value <= 40:
                    trade_ratio = 0.7  # 중간 매수
                else:
                    trade_ratio = 0.5  # 소액 매수

                if confidence_score > 70:
                    krw = self.upbit.get_balance("KRW")
                    if krw > 5000:
                        order = self.upbit.buy_market_order(self.ticker, krw * trade_ratio)
                        print("\n=== Buy Order Executed ===")
                        print(f"Trade Ratio: {trade_ratio * 100}%")
                        print(json.dumps(order, indent=2))

            elif decision == "sell":
                # 극도의 탐욕 상태(75-100)에서는 더 과감한 매도
                if fear_greed_value >= 75:
                    trade_ratio = 1.0  # 전량 매도
                elif fear_greed_value >= 60:
                    trade_ratio = 0.7  # 일부 매도
                else:
                    trade_ratio = 0.5  # 소량 매도

                if confidence_score > 70:
                    btc = self.upbit.get_balance(self.ticker)
                    current_price = pyupbit.get_current_price(self.ticker)

                    if btc * current_price > 5000:
                        sell_amount = btc * trade_ratio
                        order = self.upbit.sell_market_order(self.ticker, sell_amount)
                        print("\n=== Sell Order Executed ===")
                        print(f"Trade Ratio: {trade_ratio * 100}%")
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

        # 4. 공포탐욕지수 조회
        fear_greed_data = trader.get_fear_greed_index()

        # 5. 뉴스 데이터 조회
        news_data = trader.get_crypto_news()

        # 6. AI 분석을 위한 데이터 준비
        if all([current_status, orderbook_data, ohlcv_data, fear_greed_data]):
            analysis_data = {
                "current_status": current_status,
                "orderbook": orderbook_data,
                "ohlcv": ohlcv_data,
                "fear_greed": fear_greed_data
            }

            # 7. AI 분석 실행
            ai_result = trader.get_ai_analysis(analysis_data)

            if ai_result:
                print("\n=== AI Analysis Result ===")
                print(json.dumps(ai_result, indent=2))

                # 8. 매매 실행 (공포탐욕지수 고려)
                trader.execute_trade(
                    ai_result['decision'],
                    ai_result['confidence_score'],
                    fear_greed_data['current']['value']
                )

    except Exception as e:
        print(f"Error in ai_trading: {e}")


if __name__ == "__main__":
    print("Starting Enhanced Bitcoin Trading Bot with Fear & Greed Index...")
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
            time.sleep(60)  # 에러 발생 시 60초 대기
