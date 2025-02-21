import os
from dotenv import load_dotenv
import json
import pyupbit
import pandas as pd
import ta
from datetime import datetime, timedelta


load_dotenv()


class EnhancedCryptoDataCollector:
    def __init__(self, ticker="KRW-BTC"):
        self.ticker = ticker
        self.access = os.getenv('UPBIT_ACCESS_KEY')
        self.secret = os.getenv('UPBIT_SECRET_KEY')
        self.upbit = pyupbit.Upbit(self.access, self.secret)


    def add_technical_indicators(self, df):
        """기술적 분석 지표 추가"""
        # 볼린저 밴드
        indicator_bb = ta.volatility.BollingerBands(close=df['close'])
        df['bb_high'] = indicator_bb.bollinger_hband()
        df['bb_mid'] = indicator_bb.bollinger_mavg()
        df['bb_low'] = indicator_bb.bollinger_lband()

        # RSI
        df['rsi'] = ta.momentum.RSIIndicator(close=df['close']).rsi()

        # MACD
        macd = ta.trend.MACD(close=df['close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_diff'] = macd.macd_diff()

        # 이동평균선
        df['sma_5'] = ta.trend.SMAIndicator(close=df['close'], window=5).sma_indicator()
        df['sma_20'] = ta.trend.SMAIndicator(close=df['close'], window=20).sma_indicator()
        df['sma_60'] = ta.trend.SMAIndicator(close=df['close'], window=60).sma_indicator()
        df['sma_120'] = ta.trend.SMAIndicator(close=df['close'], window=120).sma_indicator()

        # ATR
        df['atr'] = ta.volatility.AverageTrueRange(
            high=df['high'],
            low=df['low'],
            close=df['close']
        ).average_true_range()

        return df


    def get_current_status(self):
        """현재 투자 상태 조회"""
        try:
            krw_balance = float(self.upbit.get_balance("KRW"))
            crypto_balance = float(self.upbit.get_balance(self.ticker))
            avg_buy_price = float(self.upbit.get_avg_buy_price(self.ticker))
            current_price = float(pyupbit.get_current_price(self.ticker))

            print(f"보유 현금: {krw_balance:,.0f} KRW")
            print(f"보유 암호화폐: {crypto_balance:.8f} {self.ticker}")
            print(f"평균 매수가: {avg_buy_price:,.0f} KRW")
            print(f"현재가: {current_price:,.0f} KRW")

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


    def get_ohlcv_data(self):
        """차트 데이터 수집 및 기술적 분석"""
        try:
            # 일봉 데이터 (최근 30일)
            daily_data = pyupbit.get_ohlcv(self.ticker, interval="day", count=30)
            daily_data = self.add_technical_indicators(daily_data)

            # 시간봉 데이터 (최근 24시간)
            hourly_data = pyupbit.get_ohlcv(self.ticker, interval="minute60", count=24)
            hourly_data = self.add_technical_indicators(hourly_data)

            # DataFrame을 dict로 변환 (datetime index 처리)
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


def analyze_market_data():
    try:
        collector = EnhancedCryptoDataCollector("KRW-BTC")

        # 1. 현재 투자 상태 조회
        current_status = collector.get_current_status()
        print("\n=== Current Investment Status ===")
        print(json.dumps(current_status, indent=2))

        # 2. 기술적 분석 데이터 수집
        technical_data = collector.get_ohlcv_data()

        if technical_data and technical_data['daily_data']:
            latest_data = technical_data['daily_data'][-1]
            print("\n=== Latest Technical Analysis ===")
            print(f"Date: {latest_data['date']}")
            print(f"RSI: {latest_data['rsi']:.2f}")
            print(f"MACD: {latest_data['macd']:.2f}")
            print(f"Bollinger Bands: {latest_data['bb_low']:.0f} - {latest_data['bb_mid']:.0f} - {latest_data['bb_high']:.0f}")
            print(f"ATR: {latest_data['atr']:.0f}")

        return technical_data

    except Exception as e:
        print(f"Error in analyze_market_data: {e}")
        return None


if __name__ == "__main__":
    analyze_market_data()
