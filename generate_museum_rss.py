import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime
import pytz
import re

url = "https://museum.or.kr/news/"
base_url = "https://museum.or.kr"

# 1. 웹페이지 접속 (봇 차단 방지 헤더)
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
}

print("한국박물관협회 접속 중...")
response = requests.get(url, headers=headers, timeout=15)
response.raise_for_status()

# 사이트 인코딩이 utf-8이 아닐 수 있으므로 확인 (필요시 'euc-kr' 등으로 변경)
response.encoding = 'utf-8' 
soup = BeautifulSoup(response.text, 'html.parser')

# 2. RSS 피드 생성기 초기화
fg = FeedGenerator()
fg.id(url)
fg.title('한국박물관협회 공지사항 RSS')
fg.author({'name': '한국박물관협회'})
fg.link(href=url, rel='alternate')
fg.description('한국박물관협회 소식 및 공지사항을 제공합니다.')
fg.language('ko')

# 3. 게시글 파싱
# 보통 <table> 내의 <tr> 또는 <ul class="board_list"> 내의 <li> 형태입니다.
# 두 가지 가능성을 모두 열어두고 탐색합니다.
rows = soup.select('table tbody tr')
if not rows:
    rows = soup.select('.board-list li, .list_wrap > div, .board_wrap tbody tr')

items_found = 0

for row in rows:
    title_element = row.find('a')
    if not title_element:
        continue

    # 제목 정제
    title = title_element.get_text(separator=' ', strip=True)
    
    # "New" 아이콘 텍스트 제거 등 정제 (이미지 대체 텍스트가 딸려올 수 있음)
    title = re.sub(r'^(공지사항|New)\s*', '', title, flags=re.IGNORECASE).strip()

    # 링크 추출
    href = title_element.get('href', '')
    if href.startswith('/'):
        link = base_url + href
    elif href.startswith('http'):
        link = href
    else:
        # 상대경로(예: view.php?id=123)일 경우
        link = f"{url.rstrip('/')}/{href}"

    # 날짜 추출
    date_str = ""
    # 전체 row 텍스트에서 날짜 형식(2026.03.20) 또는 시간 형식(09:56) 찾기
    row_text = row.get_text(separator=' ')
    
    date_match = re.search(r'20\d{2}[-./]\d{2}[-./]\d{2}', row_text)
    time_match = re.search(r'([01]\d|2[0-3]):([0-5]\d)', row_text)
    
    if date_match:
        # 2026.03.20 형식
        date_str = date_match.group().replace('.', '-').replace('/', '-')
    elif time_match:
        # 오늘 날짜인 경우 시간(09:56)만 표시되는 경우가 있음
        # 이 경우 스크립트 실행 당일의 날짜를 부여
        date_str = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d')
    else:
        # 날짜를 전혀 찾지 못하면 패스
        continue

    # 4. RSS 엔트리 추가 (order='append'로 읽어온 순서대로 추가)
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

print(f"탐색 완료: 총 {items_found}개의 게시글을 찾았습니다.")

# 5. XML 파일 저장
xml_filename = 'museum_rss.xml'
fg.rss_file(xml_filename)
print(f"RSS 피드 생성 완료: {xml_filename}")
