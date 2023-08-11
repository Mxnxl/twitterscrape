import sys
import os
from datetime import datetime
import requests
from bs4 import BeautifulSoup

ROOT = "https://nitter.net"
RETRIES = 10
HEADERS = {
    "Accept": "*/*",
    "X-User-IP": "1.1.1.1",
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
}

# getting request
def get_request(url):
    for _ in range(RETRIES):
        try:
            res = requests.get(url, headers=HEADERS)
            if res.status_code == 200:
                break
        except requests.exceptions.ConnectionError:
            print("We can't connect to the server")
    return res

def get_webpages(url):
    # get all tweets in case of a very long thread
    res = get_request(url)
    soup = BeautifulSoup(res.content, "lxml")
    fin = soup.find("div", class_="timeline-item thread-last")
    if not fin :
        next_page= soup.find_all("a", class_="more-replies-text")[-1]
        next_page = next_page['href']
        return [soup]+get_webpages(ROOT+next_page)
    return [soup]

class Thread():
    def __init__(self, author, date, pages):
        self.author = author
        self.date = date
        self.text = f'> by {author}  date: {date}\n'
        self.pages = pages
        self.counter = 1
        self.extract_thread()

    def get_first_content(self,tag):
        self.text += "\n---\n"
        for elt in tag:
            if elt.name =="a":
                self.get_link(elt)
            else:
                self.text += elt
        self.text += "\n\n"

    def get_link(self,tag):
        #avoid putting members'name in link
        if tag.next[0] == "@":
            self.text += f'**{tag.text}**'
        else:
            self.text += f'[{tag["href"][0:32]}...]('
            self.text += f'{tag["href"]})\n'

    def get_media(self, path,kind,line, a, b= None):
        url = ROOT + path
        res = get_request(url)
        ext = path.split(a)[-1][0:b]
        name = f'{kind}_{self.counter}.{ext}'
        if res:
            with open(name, "wb") as f:
                f.write(res.content)
            self.text += f'{line.format(name)}\n'
        else:
            self.text += f'Missing : {url}'
        self.counter += 1

    def is_quote(self,tag):
        parents = tag.find_parents( "div", class_="quote-media-container")
        return bool(parents)

    def extract_thread(self):
        for _, page in enumerate(self.pages):
            if _ == 0:
                name = "main-thread"
            else:
                name = "after-tweet thread-line"

            tweets = page.find("div", class_=name)
            tags = tweets.select(
                "div.tweet-content.media-body, a.still-image, video,\
                div.card-content, div.quote-text, div.card-image, div.attachment.video-container")
            for tag in tags:
                # text tags
                if tag['class'][0] =="tweet-content":
                    self.get_first_content(tag)
                if tag['class'][0] =="card-content":
                    self.text += f"**{tag.get_text().strip()}**\n"
                if tag['class'][0] == "quote-text":
                    self.text += "\n>"
                    self.text += tag.text.replace("\n", "\n>")
                    self.text += "\n\n"
                # images & videos
                if tag['class'][0] =="still-image":
                    if self.is_quote(tag):
                        self.text += ">"
                    self.get_media(tag["href"],"image","![image]({})",".")
                if tag['class'][0] == "attachment":
                    if self.is_quote(tag):
                        self.text += ">"
                    self.get_media(tag.img["src"],"image","![image]({})",".",3)
                if tag['class'][0] == "card-image":
                    parent = tag.find_parents("a", class_="card-container")[0]
                    self.get_media(tag.img["src"],"image",f"[![image]({{}})]({parent['href']})","format%3D",3)
                if tag.name == "video":
                    #self.get_media(tag.source["src"],"video","<video src={} controls title=Title></video>",".",3)
                    self.get_media(tag.source["src"],"video","![video]({})",".",3)

        self.text += "\n\n"


def get_thread():
    url = sys.argv[1]
    url = url.replace("https://twitter.com", ROOT)
    pages = get_webpages(url)
    name = pages[0].find("div", class_="tweet-content media-body").text[0:20]
    if os.path.isdir(name):
        print("You already have this tweet")
        quit()
    else :
        os.mkdir(name)
        os.chdir(name)
        author = pages[0].find("a", class_="username").get_text()
        date = pages[0].find("p", class_="tweet-published").text
        date = datetime.strptime(date, "%b %d, %Y · %I:%M %p %Z").strftime("%d-%m-%Y")

        thread = Thread(author, date, pages)
        with open("text.md", "w", encoding="utf-8") as file:
            file.write(thread.text)

get_thread()
