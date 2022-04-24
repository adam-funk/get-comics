#!/usr/bin/env python3

import argparse
import json
import re
import smtplib
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
        page_url0, comic_url0, filename_base, message0 = get_go_comics_url(comic, slashed_date0, hyphenated_date0, session0)
    elif site0 == 'dilbert':
        page_url0, comic_url0, filename_base, message0 = get_dilbert_url(comic, hyphenated_date0, session0)
    else:
        if options.verbose:
            print(f'invalid site: {site0}')
        page_url0, comic_url0, filename_base = None, None, None
        message0 = f'invalid site: {site0}'
    if options.verbose:
        print(page_url0, comic_url0, sep='\n')
    if comic_url0:
        return download(comic_url0, session0, page_url0, filename_base)
        # output: buffer, subtype, filename, message
    return None, None, None, message0


def get_go_comics_url(comic, slashed_date0, hyphenated_date0, session0):
    # 'https://www.gocomics.com/adamathome/2020/10/08'
    page_url0 = f'https://www.gocomics.com/{comic}/{slashed_date0}'
    page_html = session0.get(page_url0).html
    try:
        div_comic = page_html.find('div.comic')[0]
        comic_url0 = div_comic.attrs['data-image']
        filename_base = f'{comic}-{hyphenated_date0}'
        message0 = ''
    except IndexError as e:
        comic_url0 = None
        filename_base = None
        message0 = f'{page_url0} {str(e)}'
    return page_url0, comic_url0, filename_base, message0


def get_dilbert_url(comic, hyphenated_date0, session0):
    # https://dilbert.com/strip/2020-12-21
    page_url0 = f'https://dilbert.com/strip/{hyphenated_date0}'
    page_html = session0.get(page_url0).html
    try:
        img_comic = page_html.find('img.img-responsive')[0]
        comic_url0 = img_comic.attrs['src']
        filename_base = f'{comic}-{hyphenated_date0}'
        message0 = ''
    except IndexError as e:
        comic_url0 = None
        filename_base = None
        message0 = f'{page_url0} {str(e)}'
    return page_url0, comic_url0, filename_base, message0


def get_subtype_and_extension(http_headers):
    mimetype = http_headers['Content-Type']
    image_type = mime_split.match(mimetype)
    if image_type:
        subtype0 = image_type.group(1)
        extension = converter.get(subtype0, subtype0)
    else:
        subtype0, extension = 'oops', 'oops'
    return subtype0, extension


def download(url, session0, page_url0, filename_base):
    response = session0.get(url, headers={'Referer': page_url0})
    subtype0, extension = get_subtype_and_extension(response.headers)
    buffer0 = BytesIO()
    buffer0.write(response.content)
    filename0 = f'{filename_base}.{extension}'
    if options.verbose:
        print("Saved", url)
    return buffer0, subtype0, filename0, ''


def send_mail(data0, date_string):
    mail = EmailMessage()
    mail.set_charset('utf-8')
    mail['To'] = ','.join(config['mail_to'])
    mail['From'] = config['mail_from']
    mail['Subject'] = f'Comics {date_string}'

    text = []

    # https://docs.python.org/3/library/email.examples.html
    for buffer0, subtype0, filename0, message0 in data0:
        if filename0:
            buffer0.seek(0)
            img_data = buffer0.read()
            mail.add_attachment(img_data, maintype='image',
                                filename=filename0,
                                subtype=subtype0)
        else:
            text.append(message0)

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

session = requests_html.HTMLSession()
today = date.today()
hyphenated_date = today.strftime('%Y-%m-%d')
slashed_date = today.strftime('%Y/%m/%d')

data = []

for comic_name, site in config['comics']:
    if options.verbose:
        print(comic_name, site)
    buffer, subtype, filename, message = get_comic(site, comic_name, slashed_date,
                                                   hyphenated_date, session)
    data.append((buffer, subtype, filename, message))

send_mail(data, hyphenated_date)
