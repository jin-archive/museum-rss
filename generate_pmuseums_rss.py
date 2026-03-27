import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime
import pytz
import re
from urllib.parse import urljoin

url = "http://pmuseums.org/bbs/board.php?bo_table=brd_notice"

# 1. 웹페이지 접속 (봇 차단 방지 헤더)
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
}

print("한국사립박물관협회 접속 중...")
response = requests.get(url, headers=headers, timeout=15)
response.raise_for_status()

# 한글 깨짐 방지
response.encoding = 'utf-8' 
soup = BeautifulSoup(response.text, 'html.parser')

# 2. RSS 피드 생성기 초기화
fg = FeedGenerator()
fg.id(url)
fg.title('한국사립박물관협회 공지사항 RSS')
fg.author({'name': '한국사립박물관협회'})
fg.link(href=url, rel='alternate')
fg.description('한국사립박물관협회 공지사항을 제공합니다.')
fg.language('ko')

# 3. 게시글 파싱 (표 형태의 행(tr) 탐색)
rows = soup.select('table tbody tr')
if not rows:
    rows = soup.select('.board-list li')

added_links = set()
items_found = 0

for row in rows:
    title_element = row.find('a')
    if not title_element:
        continue

    title = title_element.get_text(separator=' ', strip=True)
    if not title or len(title) < 2:
        continue

    # 게시판 특성: 진짜 게시글 링크에는 보통 'wr_id=' (글 번호)가 포함되어 있음
    href = title_element.get('href', '')
    if 'wr_id=' not in href:
        continue

    # 상대경로(./board.php?...)를 완벽한 절대경로로 자동 변환
    link = urljoin(url, href)
    
    # '공지'로 상단에 고정된 글이 아래쪽 일반 목록에 중복으로 나오는 것 방지
    if link in added_links:
        continue
    added_links.add(link)

    # 4. 날짜 추출 (2026-03-20 등)
    row_text = row.get_text(separator=' ')
    date_str = ""
    
    date_match = re.search(r'(20\d{2}[-./]\d{2}[-./]\d{2})', row_text)
    time_match = re.search(r'([01]\d|2[0-3]):([0-5]\d)', row_text)
    
    if date_match:
        date_str = date_match.group(1).replace('.', '-').replace('/', '-')
    elif time_match:
        # 오늘 날짜인 경우 시간(09:56)만 표시되는 경우 대응
        date_str = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d')
    else:
        continue # 날짜 정보가 없으면 패스

    # 5. RSS 엔트리 추가 (순서대로 차곡차곡)
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

# 6. XML 파일 저장
xml_filename = 'pmuseums_rss.xml'
fg.rss_file(xml_filename)
print(f"RSS 피드 생성 완료: {xml_filename}")
