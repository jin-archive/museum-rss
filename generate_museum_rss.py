import time
import re
import hashlib
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime
import pytz
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

url = "https://museum.or.kr/news/"
base_url = "https://museum.or.kr"

print("크롬 브라우저를 시작합니다...")
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--window-size=1920,1080')
chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

print("웹페이지에 접속하여 자바스크립트 렌더링을 기다립니다...")
driver.get(url)
time.sleep(8) # 충분한 로딩 시간 부여

html = driver.page_source
soup = BeautifulSoup(html, 'html.parser')
driver.quit()

fg = FeedGenerator()
fg.id(url)
fg.title('한국박물관협회 공지사항 RSS')
fg.author({'name': '한국박물관협회'})
fg.link(href=url, rel='alternate')
fg.description('한국박물관협회 소식 및 공지사항을 제공합니다.')
fg.language('ko')

links = soup.find_all('a')
added_links = set()
items_found = 0

for a in links:
    href = a.get('href', '')
    title = a.get_text(separator=' ', strip=True)
    
    # 의미 없는 링크나 메뉴 필터링
    if not href or len(title) < 5:
        continue
    
    junk_words = ['기관소개', '입회안내', '회원관', '국제활동', '자료실', '개인정보처리방침', '이용약관']
    if any(junk in title for junk in junk_words):
        continue

    # 1. 좁은 범위 내에서 날짜 찾기
    date_str = ""
    row_container = a.find_parent(['tr', 'li'])
    
    if not row_container:
        curr = a.parent
        for _ in range(4):
            if not curr or curr.name in ['body', 'html']:
                break
            # 텍스트가 300자 미만인 블록 안에서 날짜 찾기
            if len(curr.get_text(strip=True)) < 300:
                if re.search(r'20\d{2}[-./]\d{2}[-./]\d{2}|([01]\d|2[0-3]):([0-5]\d)', curr.get_text()):
                    row_container = curr
                    break
            curr = curr.parent

    if row_container:
        row_text = row_container.get_text(separator=' ')
        date_match = re.search(r'(20\d{2}[-./]\d{2}[-./]\d{2})', row_text)
        time_match = re.search(r'([01]\d|2[0-3]):([0-5]\d)', row_text)
        
        if date_match:
            date_str = date_match.group(1).replace('.', '-').replace('/', '-')
        elif time_match:
            # 시간만 표기된 경우 오늘 날짜로 처리
            date_str = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d')

    if not date_str:
        continue

    # 2. 제목 정제
    title = re.sub(r'^(공지사항|New)\s*', '', title, flags=re.IGNORECASE).strip()

    # 3. 고유 링크 생성
    if href.startswith('/'):
        link = base_url + href
    elif href.startswith('http'):
        link = href
    elif 'javascript' in href or href == '#' or not href:
        onclick = a.get('onclick') or ''
        nums = re.findall(r"\d+", onclick)
        link = f"{url}?id={nums[0]}" if nums else f"{url}#{hashlib.md5(title.encode()).hexdigest()[:8]}"
    else:
        # 상대경로일 경우
        link = f"{url.rstrip('/')}/{href}"

    if link in added_links:
        continue
    added_links.add(link)

    # 4. RSS 항목 추가
    fe = fg.add_entry(order='append')
    fe.id(link)
    fe.title(title)
    fe.link(href=link)
    
    if date_str:
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            kst = pytz.timezone('Asia/Seoul')
            dt = kst.localize(dt)
            fe.pubDate(dt)
        except ValueError:
            pass
            
    items_found += 1

print(f"탐색 완료: 총 {items_found}개의 공지사항을 찾았습니다.")
fg.rss_file('museum_rss.xml')
