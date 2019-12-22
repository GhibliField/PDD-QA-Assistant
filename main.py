# -*- coding: utf-8 -*-
# Created by Weiyu

from aip import AipOcr
from screenshot import get_screenshot
import os
import re
from zhon.hanzi import punctuation
import string
import time
import urllib.parse
import requests
import webbrowser
from bs4 import BeautifulSoup as bs
import random
import json
from fake_useragent import UserAgent
import traceback
from config import Config
import nltk


def get_header():
    location = os.getcwd() + '/fake_useragent.json'
    ua = UserAgent(path=location)
    return ua.random


class QA(object):
    def __init__(self, config, history=False):
        self.client = AipOcr(
            config.OCR_APP_ID, config.OCR_API_KEY, config.OCR_SECRET_KEY)
        self.options = config.OCR_OPTIONS
        self.config = config
        if not history:
            os.system("adb devices")
            try:
                headers = {'User-Agent': get_header()}
            except Exception as e:
                print(traceback.format_exc())
            else:
                print('*Program ready*')
        self.search_result = []

    def get_file_content(self, filePath):
        with open(filePath, 'rb') as fp:
            return fp.read()

    def get_info(self, *args):
        if args:
            image = self.get_file_content(args[0])
            self.result = self.client.general(image, self.options)
        else:
            img_path = get_screenshot()
            image = self.get_file_content(img_path)
            self.result = self.client.general(image, self.options)

        answer_left = self.result['words_result'][-2]['words']
        answer_right = self.result['words_result'][-1]['words']
        num_and_question = ''.join([i['words']
                                    for i in self.result['words_result'][:-2]])

        punctuations = string.punctuation+punctuation
        num_and_question = re.sub(
            "[{}]+".format(punctuations), " ", num_and_question).strip()
        pattern = r'[0-9]{1,2}'
        res = re.match(pattern, num_and_question, flags=0)
        if res != None:
            num = res.group()
            question = num_and_question[len(str(num)):]
        else:
            question = num_and_question

        self.info = {}
        self.info['question'] = question
        self.info['answer_left'] = answer_left
        self.info['answer_right'] = answer_right

        # factoid or yesorno
        if '错' in answer_left+answer_right or '不对' in answer_left+answer_right or '正确' in answer_left+answer_right:
            self.info['type'] = 'yesno'
        else:
            self.info['type'] = 'factoid'
        return self.info

    def get_answer_by_wordcount(self, qa_info, site='toutiao'):

        if self.config.USE_PROXY:
            try:
                self.ip_pool = self.get_ips()
            except Exception as e:
                print(traceback.format_exc())
            else:
                print('*Proxy Ready*')

        question = qa_info['question']
        option_left = qa_info['answer_left']
        option_right = qa_info['answer_right']
        headers = {'User-Agent': get_header()}

        if site == 'zhidao':
            url = "https://zhidao.baidu.com/search?lm=0&rn=20&pn=0&fr=search&ie=gbk&word=" + \
                urllib.parse.quote(question, encoding='gbk')
        elif site == 'wenwen':
            url = "http://wenwen.sogou.com/s/?w=" + \
                urllib.parse.quote(question)+"&ch=ww.header.ssda"
        elif site == 'sogou':
            url = 'https://www.sogou.comsearch_resultssearch/?q=' + urllib.parse.quote(question)         
        elif site == 'toutiao':
            url = 'https://m.toutiao.com/search/?keyword={}&pd=synthesis&source=input&traffic_source=&original_source=&in_tfs=&in_ogs='.format(
                question)
        else:
            # url = 'https://www.baidu.com/s?wd=' + question + '&pn=0'
            print('SiteNotSupported')
            print('Use Default site: toutiao.com')
            url = 'https://m.toutiao.com/search/?keyword={}&pd=synthesis&source=input&traffic_source=&original_source=&in_tfs=&in_ogs='.format(
                question)

        try:
            if self.config.USE_PROXY:
                # 构造代理字典
                proxies = {
                    'http': 'http://{}'.format(self.ip_pool[random.randint(0, len(self.ip_pool)-1)])
                }
                response = requests.get(
                    url=url, proxies=proxies, headers=headers, timeout=2)
            else:
                response = requests.get(url=url, headers=headers, timeout=2)

        except requests.exceptions.ConnectTimeout as e:
            print('TimeoutError')
            self.get_answer_by_browser(qa_info)

        if site == 'zhidao':
            page = response.content.decode(
                'gbk').encode('utf-8').decode('utf-8')
            soup = bs(page, 'lxml')
            abstracts = soup.find_all(class_=['dd answer', 'ti'])

        elif site == '360':
            page = response.content.decode('utf-8')
            soup = bs(page, 'lxml')
            abstracts = soup.find_all('div', class_=['qa-i-hd', 'qa-i-bd'])

        elif site == 'toutiao':
            page = response.content.decode('utf-8')
            soup = bs(page, 'lxml')
            abstracts = soup.find_all('div', class_=[
                                      'ttfe-flex-item span8 ts-grid', 'ttfe-flex ttfe-flex-dir-column ttfe-article-main'])

        elif site == 'wenwen':
            page = response.content.decode('utf-8')
            soup = bs(page, 'lxml')
            abstracts = soup.find_all(class_=['vrTitle', 'str-text-info'])

        elif site == 'sogou':
            page = response.content.decode('utf-8')
            soup = bs(page, 'lxml')
            abstracts = soup.find_all(
                'div', class_=['text-layout', 'ft', 'str-text-info', 'str_info_div'])
        # CAUTION: prone to being blocked by baidu vertification
        # elif site == 'baidu':
        #     response.raise_for_status()
        #     response.encoding = response.apparent_encoding
        #     html = response.text
        #     soup = bs(html, 'html.parser')
        #     abstracts = soup.find_all('div', class_=['c-abstract','c-span18 c-span-last'])

        num_left = 0
        num_right = 0
        candidates = ' '.join([abstra.text for abstra in abstracts])
        if self.config.BIGRAM:
            bigrm_left = list(map(''.join, nltk.bigrams(option_left)))
            bigrm_right = list(map(''.join, nltk.bigrams(option_right)))
            for bigram in bigrm_left:
                num_left += candidates.count(bigram)
            for bigram in bigrm_right:
                num_right += candidates.count(bigram)
        else:
            num_left += candidates.count(option_left)
            num_right += candidates.count(option_right)

        if num_left == num_right:
            print("高低计数相等此方法失效！")
            self.get_answer_by_browser(qa_info)
        elif num_left > num_right:
            if '不是' in question or '不属于' in question or ('未' in question and '未来' not in question):
                print('**请注意此题为否定题,选计数最少的**')
                return option_right
            else:
                return option_left
        else:
            if '不是' in question or '不属于' in question or ('未' in question and '未来' not in question):
                print('**请注意此题为否定题,选计数最少的**')
                return option_left
            else:
                return option_right

    def get_answer_by_pagecount(self, qa_info):
        try:
            self.ip_pool = self.get_ips()
        except Exception as e:
            print(traceback.format_exc())
        else:
            print('*Proxy Ready*')

        question = qa_info['question']
        option_left = qa_info['answer_left']
        option_right = qa_info['answer_right']

        cnts = []
        headers = {'User-Agent': get_header()}
        pattern = r'[0-9,]{1,}'

        keywords = ['{} {}'.format(question, option_left), '{} {}'.format(
            question, option_right)]

        for wd in keywords:
            url = 'https://www.sogou.com/web?query={}&_asf=www.sogou.com&ie=utf8&from=index-nologin&s_from=index'.format(
                urllib.parse.quote(wd))
            response = requests.get(url, headers=headers, timeout=2)
            page = response.content.decode('utf-8')
            soup = bs(page, 'lxml')
            s = soup.find('p', class_='num-tips').get_text()
            page_cnt = re.search(pattern, s).group().replace(',', '')
            cnts.append(page_cnt)

        cnts = list(map(int, cnts))

        num_left = cnts[0]
        num_right = cnts[1]

        if num_left == num_right:
            print("高低计数相等此方法失效！")
            self.get_answer_by_browser(qa_info)
        elif num_left > num_right:
            if '不是' in question or '不属于' in question or ('未' in question and '未来' not in question):
                print('**请注意此题为否定题,选计数最少的**')
                return option_left
        else:
            if '不是' in question or '不属于' in question or ('未' in question and '未来' not in question):
                print('**请注意此题为否定题,选计数最少的**')
                return option_left
            else:
                return option_right

    def get_answer_by_browser(self, qa_info):
        webbrowser.open(
            'https://www.baidu.com/s?ie=utf-8&f=8&rsv_bp=1&tn=baidu&wd={}&rqlang=cn&rsv_enter=1&rsv_dl=tb&rsv_sug3=41&rsv_sug2=0&rn=20'.format(qa_info['question']))

    def get_ips(self):

        if not self.config.IP_POOL:
            targetUrl = Config.IP_PROXY_API
            resp = requests.get(targetUrl)
            ip_pool = json.loads(resp.text)['msg']
            ip_pool = ['{0}:{1}'.format(i['ip'], i['port']) for i in ip_pool]
            return ip_pool
        else:
            return self.config.IP_POOL


if __name__ == '__main__':
    config = Config()
    config.display()
    qa = QA(config)

    qa_info = qa.get_info()
    # qa_info = qa.get_info('img/screenshot_1576144846.png')
    print('query: {0}\t({1})'.format(qa_info['question'], qa_info['type']))
    if qa_info['type'] == 'yesno' or config.METHOD == 'browser':
        qa.get_answer_by_browser(qa_info)
    else:
        if config.METHOD == 'pagecount':  # factoid only
            print(qa.get_answer_by_pagecount(qa_info))
        elif config.METHOD == 'wordcount':  # factoid only
            print(qa.get_answer_by_wordcount(qa_info, site=config.SITE))
        else:
            print('Method not existed')
