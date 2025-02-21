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
import base64
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


load_dotenv()


def capture_full_page(url, output_path):
    """웹 페이지 캡처 함수"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # 헤드리스 모드
    chrome_options.add_argument('--start-maximized')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 20)

    try:
        driver.get(url)
        time.sleep(5)  # 초기 로딩 대기

        # 시간 설정 버튼 클릭
        time_button = wait.until(EC.element_to_be_clickable((By.XPATH,
            "/html/body/div[1]/div[2]/div[3]/div/section[1]/article[1]/div/span[2]/div/div/div[1]/div[1]/div/cq-menu[1]/span/cq-clickable")))
        time_button.click()
        time.sleep(1)

        # 1시간 옵션 클릭
        hour_option = wait.until(EC.element_to_be_clickable((By.XPATH,
            "/html/body/div[1]/div[2]/div[3]/div/section[1]/article[1]/div/span[2]/div/div/div[1]/div[1]/div/cq-menu[1]/cq-menu-dropdown/cq-item[8]")))
        hour_option.click()
        time.sleep(3)

        # 전체 페이지 높이 구하기
        total_height = driver.execute_script("return document.body.scrollHeight")
        driver.set_window_size(1920, total_height)

        # 스크린샷 캡처
        driver.save_screenshot(output_path)
        print(f"Screenshot saved as: {output_path}")
        return True

    except Exception as e:
        print(f"Error in capture_full_page: {e}")
        return False

    finally:
        driver.quit()


class EnhancedCryptoTrader:
    def __init__(self, ticker="KRW-BTC"):
        self.ticker = ticker
        self.access = os.getenv('UPBIT_ACCESS_KEY')
        self.secret = os.getenv('UPBIT_SECRET_KEY')
        self.serpapi_key = os.getenv('SERPAPI_KEY')
        self.upbit = pyupbit.Upbit(self.access, self.secret)
        self.client = Cerebras(
        api_key=os.environ.get(
            "CEREBRAS_API_KEY"
        ),  # This is the default and can be omitted
    )
        self.fear_greed_api = "https://api.alternative.me/fng/"



    def get_fear_greed_index(self, limit=7):
        """공포탐욕지수 데이터 조회"""
        try:
            response = requests.get(f"{self.fear_greed_api}?limit={limit}")
            if response.status_code == 200:
                data = response.json()

                latest = data['data'][0]
                print("\n=== Fear and Greed Index ===")
                print(f"Current Value: {latest['value']} ({latest['value_classification']})")

                processed_data = []
                for item in data['data']:
                    processed_data.append({
                        'date': datetime.fromtimestamp(int(item['timestamp'])).strftime('%Y-%m-%d'),
                        'value': int(item['value']),
                        'classification': item['value_classification']
                    })

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

            print("\n=== Latest Technical Indicators ===")
            print(f"RSI: {daily_data['rsi'].iloc[-1]:.2f}")
            print(f"MACD: {daily_data['macd'].iloc[-1]:.2f}")
            print(f"BB Position: {daily_data['bb_pband'].iloc[-1]:.2f}")

            return {
                "daily_data": daily_data_dict[-7:],
                "hourly_data": hourly_data_dict[-6:],
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
    def capture_and_analyze_chart(self):
        """차트 캡처 및 분석"""
        try:
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"chart_{current_time}.png"

            url = f"https://upbit.com/exchange?code=CRIX.UPBIT.{self.ticker}"
            capture_success = capture_full_page(url, screenshot_path)

            if not capture_success:
                return None

            # 이미지를 base64로 인코딩
            with open(screenshot_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode("utf-8")

            # OpenAI Vision API 호출
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Analyze this cryptocurrency chart and provide insights about: 1) Current trend 2) Key support/resistance levels 3) Technical indicator signals 4) Notable patterns"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500
            )

            # 분석 결과 처리
            analysis_result = response.choices[0].message.content

            # 임시 파일 삭제
            os.remove(screenshot_path)

            return analysis_result

        except Exception as e:
            print(f"Error in capture_and_analyze_chart: {e}")
            if os.path.exists(screenshot_path):
                os.remove(screenshot_path)
            return None


    def get_crypto_news(self):
        """비트코인 관련 최신 뉴스 조회"""
        try:
            base_url = "https://serpapi.com/search.json"
            params = {
                "engine": "google_news",
                "q": "bitcoin crypto trading",
                "api_key": self.serpapi_key,
                "gl": "us",
                "hl": "en"
            }

            response = requests.get(base_url, params=params)
            if response.status_code == 200:
                news_data = response.json()

                if 'news_results' not in news_data:
                    return None

                processed_news = []
                for news in news_data['news_results'][:5]:
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


    # [이전 코드의 나머지 메서드들은 그대로 유지...]
    # get_fear_greed_index, add_technical_indicators, get_current_status,
    # get_orderbook_data, get_ohlcv_data 메서드들은 변경 없이 유지


    def get_ai_analysis(self, analysis_data):
        """AI 분석 및 매매 신호 생성"""
        try:
            # 차트 이미지 분석 수행
            chart_analysis = self.capture_and_analyze_chart()

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
                "fear_greed": analysis_data["fear_greed"],
                "news": analysis_data["news"],
                "chart_analysis": chart_analysis
            }


            prompt = """Analyze the cryptocurrency market based on the following data and generate trading signals:
1. Technical Indicators (RSI, MACD, Bollinger Bands, etc.)
2. Order Book Data (Buy/Sell Volume)
3. Fear & Greed Index
4. Recent News Sentiment
5. Visual Chart Analysis Results


Please consider all available data including the visual chart analysis to provide a comprehensive market assessment.


Please respond in the following JSON format:
{
    "decision": "buy/sell/hold",
    "reason": "detailed analysis explanation",
    "risk_level": "low/medium/high",
    "confidence_score": 0-100,
    "market_sentiment": "current market sentiment analysis",
    "news_impact": "analysis of news sentiment impact",
    "chart_analysis": "interpretation of visual patterns and signals"
}"""


            response = self.client.chat.completions.create(
                model="gpt-4",
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
            if decision == "buy":
                if fear_greed_value <= 25:
                    trade_ratio = 0.9995
                elif fear_greed_value <= 40:
                    trade_ratio = 0.7
                else:
                    trade_ratio = 0.5

                if confidence_score > 70:
                    krw = self.upbit.get_balance("KRW")
                    if krw > 5000:
                        order = self.upbit.buy_market_order(self.ticker, krw * trade_ratio)
                        print("\n=== Buy Order Executed ===")
                        print(f"Trade Ratio: {trade_ratio * 100}%")
                        print(json.dumps(order, indent=2))

            elif decision == "sell":
                if fear_greed_value >= 75:
                    trade_ratio = 1.0
                elif fear_greed_value >= 60:
                    trade_ratio = 0.7
                else:
                    trade_ratio = 0.5

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

        current_status = trader.get_current_status()
        orderbook_data = trader.get_orderbook_data()
        ohlcv_data = trader.get_ohlcv_data()
        fear_greed_data = trader.get_fear_greed_index()
        news_data = trader.get_crypto_news()

        if all([current_status, orderbook_data, ohlcv_data, fear_greed_data, news_data]):
            analysis_data = {
                "current_status": current_status,
                "orderbook": orderbook_data,
                "ohlcv": ohlcv_data,
                "fear_greed": fear_greed_data,
                "news": news_data
            }

            ai_result = trader.get_ai_analysis(analysis_data)

            if ai_result:
                print("\n=== AI Analysis Result ===")
                print(json.dumps(ai_result, indent=2))

                trader.execute_trade(
                    ai_result['decision'],
                    ai_result['confidence_score'],
                    fear_greed_data['current']['value']
                )

    except Exception as e:
        print(f"Error in ai_trading: {e}")


if __name__ == "__main__":
    print("Starting Enhanced Bitcoin Trading Bot with Chart Analysis...")
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
