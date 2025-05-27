import time
import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import chromedriver_autoinstaller
from bs4 import BeautifulSoup
from datetime import datetime
from tqdm import tqdm

def make_search_url(query, period='1y'):
    nso_period = f'so%3Ar%2Cp%3A{period}'
    base_url = (
        "https://search.naver.com/search.naver?sm=tab_hty.top&ssc=tab.cafe.all"
        "&query={query}"
        "&oquery={oquery}"
        "&tqi=jvnOBsqpts0ssM%2FjKtGssssstOR-204345"
        "&ackey=ibdmdmt6"
        f"&nso={nso_period}"
        "&cafe_where=articleg"
        "&stnm=rel"
    )
    query_enc = query.replace(' ', '+')
    return base_url.format(query=query_enc, oquery=query_enc)

def get_driver():
    chromedriver_autoinstaller.install()
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=options)
    return driver

def scroll_down(driver, min_li_count=100, sleep_sec=1):
    last_count = 0
    while True:
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        li_list = soup.select('div.api_subject_bx ul.lst_view li.bx._bx')
        if len(li_list) >= min_li_count:
            break
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
        time.sleep(sleep_sec)
        if len(li_list) == last_count:
            break
        last_count = len(li_list)
    return driver.page_source

def parse_li(li):
    try:
        title_tag = li.select_one('div.detail_box div.title_area a.title_link')
        title = title_tag.get_text(strip=True) if title_tag else ''
        link = title_tag['href'] if title_tag else ''
        summary_tag = li.select_one('div.detail_box div.dsc_area a.dsc_link')
        summary = summary_tag.get_text(strip=True) if summary_tag else ''
        user_tag = li.select_one('div.user_box_inner a.name')
        user = user_tag.get_text(strip=True) if user_tag else ''
        date_tag = li.select_one('div.user_box_inner span.sub')
        date = date_tag.get_text(strip=True) if date_tag else ''
        return {
            'title': title,
            'link': link,
            'summary': summary,
            'user': user,
            'date': date
        }
    except Exception as e:
        return {'title': '', 'link': '', 'summary': '', 'user': '', 'date': ''}

def crawl_cafe(query, min_li_count=100, period='1y'):
    save_dir = "crawled_csv"
    os.makedirs(save_dir, exist_ok=True)
    now = datetime.now().strftime('%Y%m%d_%H%M%S')
    query_str = query.replace(' ', '').replace('+', '')
    output_csv = os.path.join(save_dir, f"cafe_{query_str}_{period}_{now}.csv")

    url = make_search_url(query, period)
    driver = get_driver()
    driver.get(url)
    time.sleep(2)
    page_source = scroll_down(driver, min_li_count)
    soup = BeautifulSoup(page_source, 'html.parser')
    li_list = soup.select('div.api_subject_bx ul.lst_view li.bx._bx')

    data = []
    print(f"총 {min_li_count}개 중...")
    for i, li in enumerate(tqdm(li_list[:min_li_count], desc='진행률', ncols=80)):
        data.append(parse_li(li))
        time.sleep(0.01)

    df = pd.DataFrame(data)
    df.to_csv(output_csv, index=False)
    driver.quit()
    print(f"{len(df)}개 데이터 저장 완료: {output_csv}")

if __name__ == "__main__":
    query = "+대구 +치과 +추천"
    period = '1y'
    crawl_cafe(query, min_li_count=1000, period=period)
