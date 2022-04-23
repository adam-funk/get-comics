#!/usr/bin/env python3

import argparse
import imghdr
import json
import os
import re
import smtplib
import tempfile
from datetime import date
from email.message import EmailMessage
from io import BytesIO

import requests_html

mime_split = re.compile(r'image/(\w+).*')

converter = {'gif': 'gif',
             'jpeg': 'jpg'
             }


def get_comic(site0, comic, slashed_date0, hyphenated_date0, session0):
    if site0 == 'gocomics':
        return get_go_comics_url(comic, slashed_date0, hyphenated_date0, session0)
    if site0 == 'dilbert':
        return get_dilbert_url(comic, hyphenated_date0, session0)
    if options.verbose:
        print('invalid site:', site0)
    return None, None, None


def get_go_comics_url(comic, slashed_date0, hyphenated_date0, session0):
    # 'https://www.gocomics.com/adamathome/2020/10/08'
    page_url0 = f'https://www.gocomics.com/{comic}/{slashed_date0}'
    page_html = session0.get(page_url0).html
    try:
        div_comic = page_html.find('div.comic')[0]
        comic_url0 = div_comic.attrs['data-image']
        filename0 = 'gocomics-%s-%s' % (comic, hyphenated_date0)
    except IndexError as e:
        comic_url0 = None
        filename0 = None
    return page_url0, comic_url0, filename0


def get_dilbert_url(comic, hyphenated_date0, session0):
    # https://dilbert.com/strip/2020-12-21
    page_url0 = f'https://dilbert.com/strip/{hyphenated_date0}'
    page_html = session0.get(page_url0).html
    try:
        img_comic = page_html.find('img.img-responsive')[0]
        comic_url0 = img_comic.attrs['src']
        filename0 = 'dilbert-%s-%s' % (comic, hyphenated_date0)
    except IndexError as e:
        comic_url0 = None
        filename0 = None
    return page_url0, comic_url0, filename0


def filename_extension(http_headers):
    try:
        mimetype = http_headers['Content-Type']
        image_type = mime_split.match(mimetype)
        if image_type:
            image_str = image_type.group(1)
            result = converter.get(image_str, image_str)
        else:
            result = 'oops'
    except KeyError:
        result = 'dat'
    return result


# https://stackoverflow.com/questions/7243750/download-file-from-web-in-python-3
def download(url, session0, page_url0, options0):
    # TODO determine mime type of binary
    #      and set filename extension appropriately
    # TODO remove site from filename
    response = session0.get(url, headers={'Referer': page_url0})
    subtype = filename_extension(response.headers)
    buffer0 = BytesIO()
    buffer0.write(response.content)
    if options0.verbose:
        print("Saved", url)
    return buffer0, subtype


def send_mail(data0, date_string):
    mail = EmailMessage()
    mail.set_charset('utf-8')
    mail['To'] = ','.join(config['mail_to'])
    mail['From'] = config['mail_from']
    mail['Subject'] = f'Comics {date_string}'

    text = []

    # https://docs.python.org/3/library/email.examples.html
    for filename0, buffer0, subtype0 in data0:
        buffer0.seek(0)
        img_data = buffer0.read()
        mail.add_attachment(img_data, maintype='image',
                            filename=filename0,
                            subtype=imghdr.what(None, img_data))

    mail.add_attachment('\n'.join(text).encode('utf-8'),
                        maintype='text', subtype='plain',
                        disposition='inline')

    with smtplib.SMTP('localhost') as s:
        s.send_message(mail)
    return
    

oparser = argparse.ArgumentParser(description="Comic fetcher",
                                  formatter_class=argparse.ArgumentDefaultsHelpFormatter)

oparser.add_argument('-c', dest='config_file',
                     required=True,
                     metavar='JSON',
                     help='config file')

oparser.add_argument("-v", dest="verbose",
                     default=False,
                     action='store_true',
                     help="verbose")

options = oparser.parse_args()

with open(options.config_file, 'r') as f:
    config = json.load(f)

# TODO option for date

user_agent = requests_html.user_agent()
headers = {'user-agent': user_agent}
if options.verbose:
    print('request headers:', headers)
# TODO use this

session = requests_html.HTMLSession()
today = date.today()
hyphenated_date = today.strftime('%Y-%m-%d')
slashed_date = today.strftime('%Y/%m/%d')
dir_prefix = 'comics--%s--' % hyphenated_date
out_dir = tempfile.mkdtemp(prefix=dir_prefix)

data = []

for comic_name, site in config['comics']:
    if options.verbose:
        print(comic_name, site)
    page_url, comic_url, filename = get_comic(site, comic_name, slashed_date,
                                              hyphenated_date, session)
    if options.verbose:
        print(page_url, comic_url, sep='\n')
    if comic_url:
        buffer, subtype = download(comic_url, session, page_url, options)
        data.append((filename, buffer, subtype))
    else:
        data.append(('error', None, None))

send_mail(data, hyphenated_date)
