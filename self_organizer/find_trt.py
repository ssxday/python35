# -*- coding:utf-8 -*-
"""
Licensed Materials - Property of SSX
Copyright statement and purpose...
-----------------------------------------------------
File Name:
Author:
Version:
Description:分三个步骤
1、page -> post
2、post -> download
3、download -> torrent暂时存放在文件中

"""
import requests
from html.parser import HTMLParser
from os.path import join
from bs4 import BeautifulSoup
from random import choice
import re


class Config:
    """所需的常量及设置"""
    URL_ROOT = r'http://km.1024ky.trade/pw'
    KEY_WORDS = [
        'blacked'
    ]
    USER_AGENTS = [
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
        'Mozilla/5.0 (Windows; U; Windows NT 5.1; it; rv:1.8.1.11) Gecko/20071127 Firefox/2.0.0.11',
        'Opera/9.25 (Windows NT 5.1; U; en)',
        'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727)',
        'Mozilla/5.0 (compatible; Konqueror/3.5; Linux) KHTML/3.5.5 (like Gecko) (Kubuntu)',
        'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.0.12) Gecko/20070731 Ubuntu/dapper-security Firefox/1.5.0.12',
        'Lynx/2.8.5rel.1 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/1.2.9',
        "Mozilla/5.0 (X11; Linux i686) AppleWebKit/535.7 (KHTML, like Gecko) Ubuntu/11.04 Chromium/16.0.912.77 \
        Chrome/16.0.912.77 Safari/535.7",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:50.0) Gecko/20100101 Firefox/50.0"
        "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:10.0) Gecko/20100101 Firefox/10.0 ",
    ]
    HEADERS = {
        'User-Agent': choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml,application/force-download/;q=0.9,*/*;q=0.8',
        'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded'
    }


class TaskTeam:
    """通用队列类"""

    def __init__(self):
        self.tasks = []  # 没有上限

    def add_task(self, task):
        self.tasks.append(task)

    def take_task(self):
        if self.tasks:
            return self.tasks.pop(0)
        else:
            raise EOFError

    def __call__(self, *args, **kwargs):
        return self.tasks


class Page2PostParser(HTMLParser):
    def __init__(self):
        super(Page2PostParser, self).__init__()
        self.__tasks = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a' and len(attrs) == 2:
            query = dict(attrs)
            if query.get('href', '').startswith(r'htm_data'):
                self.__tasks.append(query.get('href'))  # 只负责添加

    def __call__(self, *args, **kwargs):
        return self.__tasks


class Page2Post(TaskTeam, Config):
    """本类的实例"""

    def __init__(self, start_page=5):
        super(Page2Post, self).__init__()
        self.start_page = start_page
        self.parser = Page2PostParser()
        self.list_post()

    def list_post(self):
        query_string = r'thread.php?fid=3&page={page}'.format(page=self.start_page)
        url = join(self.URL_ROOT, query_string)
        # print(url)
        page = requests.get(url)
        page.encoding = 'utf-8'
        data = page.text
        self.parser.feed(data)  # 把当前页的所有帖子地址加入到task队列
        # 把task队列搬到当前对象的__task，已继承队列属性
        self.tasks.extend(self.parser())


class Post2Download(TaskTeam, Config):
    """"""

    def __init__(self, query):
        """query从Page2Post的队列中取"""
        super(Post2Download, self).__init__()
        text = self.pull_request(query)
        # 分析帖子text
        self.scan_post(text)

    def pull_request(self, query):
        """发起请求，得到帖子内容并返回内容"""
        url = join(self.URL_ROOT, query)
        # print('正在处理帖子{}'.format(url))
        page = requests.get(url, headers=self.HEADERS)
        page.encoding = 'utf-8'  # 设置编码
        text = page.text
        return text

    def scan_post(self, source_code):
        """从post定位到download页面"""
        soup = BeautifulSoup(source_code, 'lxml')
        # 定位到主体div
        the_div = soup.find('div', attrs={'class': "tpc_content", 'id': "read_tpc"})
        for sub_str_elem in the_div.strings:
            if self.washing(sub_str_elem, *self.KEY_WORDS):
                for sibling in sub_str_elem.next_siblings:
                    if sibling.name == 'a' and sibling['href'] == sibling.string:
                        if sibling.string not in self.tasks:
                            landing_url = str(sibling.string)  # 下载着陆页的url
                            title = str(sub_str_elem)  # 去掉乱码
                            print(title, landing_url)
                            self.add_task((title, landing_url))
                        break

    @staticmethod
    def name_trim(txt):
        """已解决乱码问题，本方法并没有在使用
        """
        reg = re.compile(r'[a-zA-Z0-9]+')
        cleaned = reg.findall(txt)
        return '-'.join(cleaned)

    @staticmethod
    def washing(sands, *golds):
        """
        从sands中检查gold是否存在,强制转换sands为字符串，不区分大小写。
        :param sands:expecting 字符串
        :param golds:目标
        :return:gold只要出现任何一个，返回True，否则返回False
        """
        for g in golds:
            if str(g).lower() in sands.lower():
                return True
        return False


page2post = Page2Post(1)
while page2post():
    query = page2post.take_task()
    post2download = Post2Download(query)  # 成功


# 以下为试验区
class Downloader(Config):
    def download(self):
        """进入download页面拿到目标地址然后下载资源到本地"""
        url = 'http://www2.j32048downhostup9s.info/freeone/down.php'
        data = {
            'type': 'torrent',
            'name': 'OJGSOWr',
            'id': 'OJGSOWr'
        }
        resp = requests.post(url, data=data, headers=self.HEADERS)
        print(1,resp.status_code)
        content = resp.content
        print(2,resp.status_code)
        with open('/users/aug/desktop/testhaha.torrent','wb') as f:
            f.write(content)

# d = Downloader()  # 并不成功
# d.download()
