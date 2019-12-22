# -*- coding: utf-8 -*-
# Created by Weiyu SHEN


class Config(object):

    USE_PROXY = True
    IP_POOL = []
    # if IP_POOL　is empty, using api below to get proxies
    IP_PROXY_API = '***'

    # for screen adaption
    END = 'app'  # wechat: when you're using the mini program in wechat

    OCR_APP_ID = '***'
    OCR_API_KEY = '***'
    OCR_SECRET_KEY = '***'
    OCR_OPTIONS = {}
    OCR_OPTIONS["recognize_granularity"] = "big"
    OCR_OPTIONS["language_type"] = "CHN_ENG"
    OCR_OPTIONS["vertexes_location"] = "true"
    OCR_OPTIONS["probability"] = "true"

    METHOD = 'wordcount'  # wordcount, pagecount, browser
    SITE = 'toutiao'  # sogou, wenwen, 360, zhidao, toutiao
    SITES = ['toutiao', 'wenwen', '360', 'sogou']
    BIGRAM = True # to use 2-gram to match options or not

    # TODO
    HISTORY = False  # search KB or not

    def display(self):
        """Display Configuration values."""
        print("\nConfigurations:")
        for a in dir(self):
            if not a.startswith("__") and not callable(getattr(self, a)):
                print("{:30} {}".format(a, getattr(self, a)))
        print("\n")
