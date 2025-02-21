from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time
from datetime import datetime


def capture_full_page(url, output_path=None):
    # 크롬 옵션 설정
    chrome_options = Options()
    chrome_options.add_argument('--start-maximized')  # 최대 창 크기
    chrome_options.add_argument('--disable-gpu')  # GPU 가속 비활성화
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')

    # 헤드리스 모드는 차트 조작을 위해 비활성화


    # WebDriver 설정
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 20)  # 최대 20초 대기

    try:
        # 페이지 로드
        driver.get(url)

        # 페이지가 완전히 로드될 때까지 대기
        time.sleep(5)  # 초기 로딩 대기

        # 시간 설정 버튼 클릭
        time_button_xpath = "/html/body/div[1]/div[2]/div[3]/div/section[1]/article[1]/div/span[2]/div/div/div[1]/div[1]/div/cq-menu[1]/span/cq-clickable"
        time_button = wait.until(EC.element_to_be_clickable((By.XPATH, time_button_xpath)))
        time_button.click()

        # 잠시 대기하여 드롭다운 메뉴가 나타나도록 함
        time.sleep(1)

        # 1시간 옵션 클릭
        hour_option_xpath = "/html/body/div[1]/div[2]/div[3]/div/section[1]/article[1]/div/span[2]/div/div/div[1]/div[1]/div/cq-menu[1]/cq-menu-dropdown/cq-item[8]"
        hour_option = wait.until(EC.element_to_be_clickable((By.XPATH, hour_option_xpath)))
        hour_option.click()

        # 차트가 업데이트될 때까지 대기
        time.sleep(3)

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
