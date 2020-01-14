# -*- coding: utf-8 -*-
# Created by Weiyu SHEN

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
from multiprocessing import Pool, Manager
import nltk
from config import Config


def get_file_content(filePath):
    with open(filePath, 'rb') as fp:
        return fp.read()


def get_info(ocr, img=None):

    if img:
        image = get_file_content(img)
        result = ocr.general(image, Config.OCR_OPTIONS)
    else:
        img_path = get_screenshot()
        image = get_file_content(img_path)
        result = ocr.general(image, Config.OCR_OPTIONS)

    answer_left = result['words_result'][-2]['words']
    answer_right = result['words_result'][-1]['words']
    num_and_question = ''.join([i['words']
                                for i in result['words_result'][:-2]])

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

    info = {}
    info['question'] = question
    info['answer_left'] = answer_left
    info['answer_right'] = answer_right

    # 判断题目是factoid还是yesorno
    if '错' in answer_left+answer_right or '不对' in answer_left+answer_right or '正确' in answer_left+answer_right:
        info['type'] = 'yesno'
    else:
        info['type'] = 'factoid'

    get_answer_by_browser(question)
    return info


def get_ips():

    if not Config.IP_POOL:
        targetUrl = Config.IP_PROXY_API
        resp = requests.get(targetUrl)
        ip_pool = json.loads(resp.text)['msg']
        ip_pool = ['{0}:{1}'.format(i['ip'], i['port']) for i in ip_pool]
        return ip_pool
    else:
        return Config.IP_POOL


def get_answer_by_browser(question):
    webbrowser.open(
        'https://www.baidu.com/s?ie=utf-8&f=8&rsv_bp=1&tn=baidu&wd={}&rqlang=cn&rsv_enter=1&rsv_dl=tb&rsv_sug3=41&rsv_sug2=0&rn=20'.format(question))


def search(queue, question, option_left, option_right, bigrm_left, bigrm_right, site, headers, proxies):

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

    try:
        response = requests.get(
            url=url, proxies=proxies, headers=headers, timeout=3)
    except:
        print('{}:  {}'.format('---',site))
        # print(traceback.format_exc())
        return

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
            'div', class_=['text-layout', 'ft', 'str-text-info', 'str_info_div', 'vrTitle'])

    num_left = 0
    num_right = 0
    if Config.BIGRAM:
        candidates = ' '.join([abstra.text for abstra in abstracts])
        for bigram in bigrm_left:
            num_left += candidates.count(bigram)
        for bigram in bigrm_right:
            num_right += candidates.count(bigram)
    else:
        candidates = ' '.join([abstra.text for abstra in abstracts])
        num_left += candidates.count(option_left)
        num_right += candidates.count(option_right)

    if num_left == num_right:
        print('{}\t\t{}'.format("***", site))  # 高低计数相等,此方法失效！

    elif num_left > num_right:
        if '不是' in question or '不属于' in question or '不包' in question or ('未' in question and '未来' not in question):
            # print('**请注意此题为否定题,选计数最少的**')
            print('{}\t\t{}'.format(option_right, site))
        else:
            print('{}\t\t{}'.format(option_left, site))
    else:
        if '不是' in question or '不属于' in question or '不包' in question or ('未' in question and '未来' not in question):
            # print('**请注意此题为否定题,选计数最少的**')
            print('{}\t\t{}'.format(option_left, site))
        else:
            print('{}\t\t{}'.format(option_right, site))
    queue.put((num_left,num_right))
    return

def get_header():
    location = os.getcwd() + '/fake_useragent.json'
    ua = UserAgent(path=location)
    return ua.random


if __name__ == '__main__':

    client = AipOcr(Config.OCR_APP_ID, Config.OCR_API_KEY,
                    Config.OCR_SECRET_KEY)

    os.system("adb devices")
    try:
        ip_pool = get_ips()
        headers = {'User-Agent': get_header()}
        # 构造代理字典
        proxies = {
            'http': 'http://{}'.format(ip_pool[random.randint(0, len(ip_pool)-1)])
        }
    except:
        print(traceback.format_exc())
    else:
        print('*Program ready*')

    qa_info = get_info(client, img='/home/d0main/wyshen/MyProject/PDD-QA-Assistant/img/screenshot_1578496931.png')
    # qa_info=get_info(client)

    question = qa_info['question']
    option_left = qa_info['answer_left']
    option_right = qa_info['answer_right']
    bigrm_left = list(map(''.join, nltk.bigrams(option_left)))
    bigrm_right = list(map(''.join, nltk.bigrams(option_right)))
    print('query: {0}\t({1})'.format(qa_info['question'], qa_info['type']))

    get_answer_by_browser(qa_info)
    try:
        q = Manager().Queue()
        p = Pool(processes=4)
        for site in Config.SITES:
            p.apply_async(search, args=(q, question, option_left, option_right, bigrm_left, bigrm_right, site, headers, proxies,))
        # print('Waiting for all subprocesses done...')
        p.close()
        p.join()
    except:
        print(traceback.format_exc())
