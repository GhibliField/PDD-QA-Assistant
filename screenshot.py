# -*- coding: utf-8 -*-
# Created by Weiyu

"""
fetch screenshot from a device
"""

import os
import time
import sys
from PIL import Image
from config import Config


# Define a class to raise Line errors
class ConfigError(Exception):   #继承自基类Exception
    def __init__(self,ErrorInfo):
        self.errorinfo=ErrorInfo
    def __str__(self):
        return self.errorinfo


def get_screenshot():

    if Config().END == 'app':
        region_q=(150,200,950,340) # app
        region_a=(150,1680,950,1800) # app
        new_img = Image.new('RGB', (950-150,340-200+1800-1680)) # app
    elif Config().END == 'wechat':
        region_q = (105,255,978,411) # mini program
        region_a = (105,1680,978,1800) # mini program
        new_img = Image.new('RGB', (978-105,411-255+1800-1680)) # mini program
    else:
        try:
            raise ConfigError("Wrong param. for END in configuration")
        except ConfigError as e:
            print(e)
            sys.exit(0)

    timestamp = str(int(time.time()))
    os.system("adb shell /system/bin/screencap -p /sdcard/screenshot.png")
    os.system(
        "adb pull /sdcard/screenshot.png ./img/screenshot_{}.png".format(timestamp))

    # cover the unecessary part
    origin = Image.open('./img/screenshot_{}.png'.format(timestamp))
    # crop the necessary parts and combine them
    cropped_q = origin.crop(region_q)   
    cropped_a = origin.crop(region_a)    
    new_img.paste(cropped_q,(0,0))

    if Config().END == 'app':
        new_img.paste(cropped_a,(0,340-200)) # app
    else:
        new_img.paste(cropped_a,(0,411-255)) # mini program    
    
    new_path='./img/screenshot_{}.jpg'.format(timestamp)
    new_img.save(new_path)

    return new_path


if __name__ == '__main__':
    get_screenshot()
