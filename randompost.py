from newspaper import Config, Article
import requests
from bs4 import BeautifulSoup
import html
import lxml
import random

headers = {'Accept-Language': "en-US,en;q=0.9",
           'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"}

URL = "https://gadgets360.com/mobiles/news"

response = requests.get(url=URL, headers=headers)

yc_webpage = html.unescape(response.text)

soup = BeautifulSoup(yc_webpage, "lxml")

all_news_links = soup.select('div.caption_box>a')

news_urls = []

for new_link in all_news_links:
    news_url = new_link.find_next(name='a')
    news_url = news_url.get_attribute_list('href')[0]
    if news_url != 'https://gadgets360.com/mobiles':
        news_urls.append(news_url)


def random_post_process():
    config = Config()
    config.keep_article_html = True

    article_id = random.randint(0, 20)
    try:
        article = Article(url=news_urls[article_id], config=config)
    except IndexError:
        article = Article(url=news_urls[0], config=config)

    article.download()

    article.parse()

    # random_post_content = article.text
    random_post_content = article.article_html

    random_post_subtitle = article.text[0:200]+'...'
    random_post_title = article.title

    random_post_img = article.top_img

    return random_post_title, random_post_subtitle, random_post_img, random_post_content
