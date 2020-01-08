from parallel import *
from aip import AipOcr
from screenshot import get_screenshot
import random
from fake_useragent import UserAgent
import traceback
from multiprocessing import Pool, Manager
import nltk
from config import Config
# os.system("adb devices")
def run():
    client = AipOcr(Config.OCR_APP_ID, Config.OCR_API_KEY,Config.OCR_SECRET_KEY)
    try:
        ip_pool = get_ips()
        headers = {'User-Agent': get_header()}
        # 构造代理字典
        proxies = {'http': 'http://{}'.format(ip_pool[random.randint(0, len(ip_pool)-1)])}
    except:
        print(traceback.format_exc())
    else:
        print('*Program ready*')
    qa_info = get_info(client)
    question = qa_info['question']
    option_left = qa_info['answer_left']
    option_right = qa_info['answer_right']
    get_answer_by_browser(qa_info)
    if qa_info['type'] == 'factoid':
        bigrm_left = list(map(''.join, nltk.bigrams(option_left)))
        bigrm_right = list(map(''.join, nltk.bigrams(option_right)))
        print('query: {0}\t({1})'.format(question, qa_info['type']))
        try:
            q = Manager().Queue()
            p = Pool(processes=4)
            for site in Config.SITES:
                p.apply_async(search, args=(q, question, option_left, option_right, bigrm_left, bigrm_right, site, headers, proxies,))
            # print('Waiting for all subprocesses done...')
            p.close()
            p.join()
        except:
            pass
        else:
            print('-'*25)
            b = list(zip(*[q.get() for i in range(len(Config.SITES))]))
            try:
                prob_left, prob_right = list(map(lambda x: x/sum(map(sum, b)), map(sum, b)))
            except:
                print('{}\t\t{}'.format("---", '综合'))
            else:
                if prob_left == prob_right:
                    print('{}\t\t{}'.format("***", '综合'))  # 高低计数相等,此方法失效！
                elif prob_left > prob_right:
                    if '不是' in question or '不属于' in question or '不包' in question or ('未' in question and '未来' not in question):
                        # print('**请注意此题为否定题,选计数最少的**')
                        print('{} {:.2%}\t{}'.format(option_right, prob_left, '综合'))
                    else:
                        print('{} {:.2%}\t{}'.format(option_left, prob_left, '综合'))
                else:
                    if '不是' in question or '不属于' in question or '不包' in question or ('未' in question and '未来' not in question):
                        # print('**请注意此题为否定题,选计数最少的**')
                        print('{} {:.2%}\t{}'.format(option_left, prob_right, '综合'))
                    else:
                        print('{} {:.2%}\t{}'.format(option_right, prob_right, '综合'))
    else:
        print('--- BROWSWER ONLY ---')
# HOW-TO-RUN: shell> run()