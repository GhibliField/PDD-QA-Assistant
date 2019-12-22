# -*- coding: utf-8 -*-
# Created by Weiyu

from aip import AipOcr
from screenshot import get_screenshot
import os
import re
from zhon.hanzi import punctuation
import string
import urllib.request
import time
import urllib.parse
import requests
import webbrowser
from bs4 import BeautifulSoup as bs
import random
import json
from fake_useragent import UserAgent
import traceback
import telnetlib
import aiohttp
import asyncio
import nltk
from config import Config


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
        self.search_results = []
        if not history:
            os.system("adb devices")
            try:
                headers = {'User-Agent': get_header()}
            except Exception as e:
                print(traceback.format_exc())
            else:
                print('*Program ready*')

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

        # 判断题目是factoid还是yesorno
        if '错' in answer_left+answer_right or '不对' in answer_left+answer_right or '正确' in answer_left+answer_right:
            self.info['type'] = 'yesno'
        else:
            self.info['type'] = 'factoid'
        return self.info

    async def get_answer_by_browser_coro(self, qa_info):
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

    async def search(self, question, site, headers, proxy):
        if site == 'toutiao':
            url = 'http://m.toutiao.com/search/?keyword={}&pd=synthesis&source=input&traffic_source=&original_source=&in_tfs=&in_ogs='.format(
                question)

        elif site == 'wenwen':
            url = "http://wenwen.sogou.com/s/?w=" + \
                urllib.parse.quote(question)+"&ch=ww.header.ssda"
        elif site == 'sogou':
            url = 'http://www.sogou.com/web?query={}&_asf=www.sogou.com&ie=utf8&from=index-nologin&s_from=index'.format(
                urllib.parse.quote(question))

        elif site == '360':
            url = "http://wenda.so.com/search/?q=" + \
                urllib.parse.quote(question)

        else:
            # zhidao
            url = "http://zhidao.baidu.com/search?lm=0&rn=20&pn=0&fr=search&ie=gbk&word=" + \
                urllib.parse.quote(question, encoding='gbk')

        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                async with session.get(url, proxy=proxy) as resp:
                    print("{}\tStatus: {}".format(site, resp.status))
                    page = await resp.text()
            except:
                print(traceback.format_exc())
            # else:
                # print(page)

            soup = bs(page, 'lxml')
            if site == 'wenwen':
                abstracts = soup.find_all(class_=['vrTitle', 'str-text-info'])
            elif site == 'toutiao':
                abstracts = soup.find_all('div', class_=[
                                          'ttfe-flex-item span8 ts-grid', 'ttfe-flex ttfe-flex-dir-column ttfe-article-main'])
            elif site == 'sogou':
                abstracts = soup.find_all(
                    'div', class_=['text-layout', 'ft', 'str-text-info', 'str_info_div', 'vrTitle'])

            elif site == '360':
                abstracts = soup.find_all('div', class_=['qa-i-hd', 'qa-i-bd'])

            else:
                # zhidao
                abstracts = soup.find_all(class_=['dd answer', 'ti'])

            self.search_results.append(abstracts)

    async def output_results(self, question, option_left, option_right):

        await asyncio.sleep(2.5)
        num_left = 0
        num_right = 0
        if self.config.BIGRAM:
            bigrm_left = list(map(''.join, nltk.bigrams(option_left)))
            bigrm_right = list(map(''.join, nltk.bigrams(option_right)))
            for abstracts in self.search_results:
                candidates = ' '.join([abstra.text for abstra in abstracts])
                for bigram in bigrm_left:
                    num_left += candidates.count(bigram)
                for bigram in bigrm_right:
                    num_right += candidates.count(bigram)
        else:
            for abstracts in self.search_results:
                candidates = ' '.join([abstra.text for abstra in abstracts])
                num_left += candidates.count(option_left)
                num_right += candidates.count(option_right)

        if num_left == num_right:
            print("高低计数相等此方法失效！")
        elif num_left > num_right:
            if '不是' in question or '不属于' in question or ('未' in question and '未来' not in question):
                print('**请注意此题为否定题,选计数最少的**')
                print('*'*8+option_right+'*'*8)
            else:
                print('*'*8+option_left+'*'*8)
        else:
            if '不是' in question or '不属于' in question or ('未' in question and '未来' not in question):
                print('**请注意此题为否定题,选计数最少的**')
                print('*'*8+option_left+'*'*8)
            else:
                print('*'*8+option_right+'*'*8)

    def get_answer_by_wordcount_cocurrently(self, qa_info):
        self.search_results = []
        sites = self.config.SITES
        question = qa_info['question']
        option_left = qa_info['answer_left']
        option_right = qa_info['answer_right']

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        if self.config.USE_PROXY:
            try:
                self.ip_pool = self.get_ips()
            except Exception as e:
                print(traceback.format_exc())
            else:
                print('*Proxy Ready*')
                print(self.ip_pool)

        headers = {'User-Agent': get_header()}
        proxy = 'http://{}'.format(
            self.ip_pool[random.randint(0, len(self.ip_pool)-1)])

        tasks = []
        tasks.append(asyncio.ensure_future(self.output_results(
            question, option_left, option_right)))  # time limit
        tasks.extend([asyncio.ensure_future(self.search(
            question, site, headers, proxy)) for site in sites])
        tasks.append(asyncio.ensure_future(
            self.get_answer_by_browser_coro(qa_info)))
        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.wait(tasks))
        loop.close()


if __name__ == '__main__':
    config = Config()
    config.display()
    qa = QA(config)

    qa_info = qa.get_info()
    # qa_info=qa.get_info('img/screenshot_1576399653.png')

    try:
        qa.get_answer_by_wordcount_cocurrently(qa_info)
    except Exception as e:
        print(traceback.format_exc())
    # else:
    #     for abstracts in qa.search_results:
    #         candidates = [abstra.text for abstra in abstracts]
    #         print(' '.join(candidates))
