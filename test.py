from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from datetime import datetime


def capture_full_page(url, output_path=None):
    # 크롬 옵션 설정
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # 헤드리스 모드
    chrome_options.add_argument('--start-maximized')  # 최대 창 크기
    chrome_options.add_argument('--disable-gpu')  # GPU 가속 비활성화
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')


    # WebDriver 설정
    driver = webdriver.Chrome(options=chrome_options)

    try:
        # 페이지 로드
        driver.get(url)

        # 페이지가 완전히 로드될 때까지 대기
        time.sleep(5)  # 동적 콘텐츠 로딩을 위한 대기

        # 전체 페이지 높이 구하기
        total_height = driver.execute_script("return document.body.scrollHeight")

        # 브라우저 창 크기 설정
        driver.set_window_size(1920, total_height)

        # 현재 시간을 파일명에 포함
        if output_path is None:
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"screenshot_{current_time}.png"

        # 스크린샷 캡처
        driver.save_screenshot(output_path)
        print(f"Screenshot saved as: {output_path}")

    except Exception as e:
        print(f"Error occurred: {str(e)}")

    finally:
        driver.quit()


# 사용 예시
url = "https://upbit.com/exchange?code=CRIX.UPBIT.KRW-BTC"
capture_full_page(url)
