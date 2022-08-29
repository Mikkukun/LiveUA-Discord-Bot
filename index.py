import time
import json
import base64
import requests
import traceback
import wand.image

from selenium import webdriver
from utils import timef, db_news
from colorama import Fore, Style
from colorthief import ColorThief
from bs4 import BeautifulSoup, element
from selenium.webdriver.chrome.options import Options

chrome_options = Options()
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')

db = db_news.Database()
db.create_tables()


def traceback_maker(err):
    """ Make a traceback from the error """
    _traceback = ''.join(traceback.format_tb(err.__traceback__))
    error = '{1}{0}: {2}'.format(type(err).__name__, _traceback, err)
    return error


def decode(html_data):
    title_class = html_data.find("div", {"class": "title"})
    encrypted_data = title_class.find("a", class_="__cf_email__")
    data = bytes.fromhex(encrypted_data['data-cfemail'])
    decoded_data = bytes(byte ^ data[0] for byte in data[1:]).decode('utf-8')
    title_class.find("a").decompose()
    return decoded_data + title_class.text


class Data:
    def __init__(self, html_data):
        self.html = html_data
        self.title = html_data.find("div", {"class": "title"}).text if not \
            html_data.find("a", class_="__cf_email__") else decode(html_data)
        self.id = html_data.attrs.get("data-id", None)
        self.link = html_data.attrs.get("data-link", None)
        self.source = ((fetch(self.link)).find("a", {"class": "source-link"}))['href']
        self.location = (html_data.find('a')).text
        self.type = (fetch(self.link).find('span', class_='marker bgma'))['data-src']
        self.vid = ((html_data.find("blockquote", {"class": "twitter-video"})).find('a'))['href'] if \
            html_data.find("blockquote", {"class": "twitter-video"}) else None
        self.twitimg = html_data['data-twitpic']
        self.date = html_data.find('span', class_='date_add').text


def read_json(key: str = None, default=None):
    """ Read the config.json file, also define default key for keys """
    with open("./config.json", "r") as f:
        data = json.load(f)
    if key:
        return data.get(key, default)
    return data


def fetch(url):
    headers = {"user_agent": read_json("user_agent")}
    html_text = requests.get(url, headers=headers).text
    soup = BeautifulSoup(html_text, 'lxml')
    return soup


def pretty_print(symbol: str, text: str):
    """ Use colorama to print text in pretty colours """
    data = {
        "+": Fore.GREEN, "-": Fore.RED,
        "!": Fore.YELLOW, "?": Fore.CYAN,
    }

    colour = data.get(symbol, Fore.WHITE)
    print(f"{colour}[{symbol}]{Style.RESET_ALL} {text}")


def news_type(link):
    driver = webdriver.Chrome(options=chrome_options)
    try:
        driver.set_page_load_timeout(8)
        driver.get(link)
    except:
        pass

    source = driver.page_source
    soup = BeautifulSoup(source, 'lxml')
    svg_xml_url = (soup.find('img'))['src']

    encoded = svg_xml_url.replace("data:image/svg+xml;base64,", "")
    decoded = base64.b64decode(encoded)

    with wand.image.Image(blob=decoded,
                          format="svg",
                          resolution=512,
                          background=wand.image.Color('transparent')) as image:
        wand.image.Image.compression_quality = 0
        png_image = image.make_blob("png32")

    with open("utils/type.png", "wb") as fh:
        fh.write(png_image)

    return ColorThief("utils/type.png").get_color(quality=1)


def news_twitimg(link):
    if "photo" in link:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(link)
        time.sleep(3)
        source = driver.page_source
        driver.quit()
        twitter_soup = BeautifulSoup(source, 'lxml')
        isolate = twitter_soup.find_all('div', class_='r-1p0dtai r-1pi2tsx r-1d2f490 r-u8s1d r-ipm5af r-13qz1uu')
        results = []
        for div in isolate:
            img = div.find('img', {'alt': 'Image'})
            if img is not None:
                img = img['src']
                results.append(img)
        return results[-1]
    else:
        return


def news_date(date):
    offset_amount = int(''.join(filter(str.isdigit, date)))

    if 'second' in date:
        date_add = (timef.time_index() - timef.time_offset(offset_amount))
    elif 'minute' in date:
        offset_amount = offset_amount * 60
        date_add = (timef.time_index() - timef.time_offset(offset_amount))
    elif 'hour' in date:
        offset_amount = offset_amount * 3600
        date_add = (timef.time_index() - timef.time_offset(offset_amount))
    else:
        offset_amount = offset_amount * 86400
        date_add = (timef.time_index() - timef.time_offset(offset_amount))
    return date_add


def main():
    try:
        pretty_print("?", timef.time_cst() + 'Checking for new articles')
        pretty_print("+", timef.time_cst() + "Fetching all articles and parsing HTML...")

        html = fetch("https://liveuamap.com/")
        feedler = html.find("div", {"id": "feedler"})

        try:
            latest_feed = sorted(
                [g for g in feedler if isinstance(g, element.Tag)],
                key=lambda g: g.attrs.get("data-time", 0), reverse=True)

            for entry in reversed(range(read_json("article_fetch_limit"))):
                news = Data(latest_feed[entry])
                print("Check")
                data = db.fetchrow("SELECT * FROM articles WHERE post_id=?", (news.id,))

                if not data:
                    pretty_print("+", timef.time_cst() + "New article found, checking article...")
                    db.execute(
                        "INSERT INTO articles (post_id, text, link, location, category) VALUES (?, ?, ?, ?, ?)",
                        (news.id, news.title, news.link, news.location, news.type)
                    )

                    return news.title, news.link, news.location, news.source, news_type(news.link), (
                           news_twitimg(news.twitimg)), news.vid, news_date(news.date)
                else:
                    continue
        except TypeError:
            pretty_print("!", "Failed to get feeder, probably 500 error, trying again...")

    except Exception as e:
        pretty_print("!", traceback_maker(e))
