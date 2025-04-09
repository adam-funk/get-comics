#!/usr/bin/env python3

import argparse
import datetime
import json
import re
import subprocess
from datetime import date, timedelta
from email.message import EmailMessage
from io import BytesIO
from typing import Tuple

import requests_html

mime_split = re.compile(r'image/(\w+).*')

converter = {'gif': 'gif',
             'jpeg': 'jpg'
             }

SENDMAIL = ["/usr/sbin/sendmail", "-t", "-oi"]


def add_comic(mail0: EmailMessage, site0: str, comic: str, specified_date, session0: requests_html.HTMLSession):
    hyphenated_date = specified_date.strftime('%Y-%m-%d')
    filename_base = f'{comic}-{hyphenated_date}'
    text_lines = []
    if site0 == 'gocomics':
        page_url0, comic_url0, message = get_go_comics_data(comic, specified_date,
                                                            session0, options.verbose)
    else:
        if options.verbose:
            print(f'invalid site: {site0}')
        page_url0, comic_url0 = '', None
        message = f'invalid site: {site0}'
    if options.verbose:
        print(page_url0, comic_url0, sep='\n')
    if comic_url0:
        buffer, subtype, filename = download(comic_url0, session0, page_url0, filename_base)
        # output: buffer, subtype, filename
        add_image(mail0, buffer, filename, subtype)
    if page_url0:
        text_lines.append(page_url0)
    if message:
        text_lines.append(message)
    add_text(mail0, '\n'.join(text_lines))
    return


def get_go_comics_data(comic: str, specified_date: datetime.date,
                       session0: requests_html.HTMLSession, verbose: bool) -> Tuple[str, str, str]:
    # https://www.gocomics.com/adamathome/2020/10/08
    slashed_date = specified_date.strftime('%Y/%m/%d')
    page_url0 = f'https://www.gocomics.com/{comic}/{slashed_date}'
    page_html = session0.get(page_url0).html
    try:
        img = page_html.find('section')[1].find('img')[0]
        if verbose:
            print(img)
        comic_url0 = img.attrs['src']
        if verbose:
            print(comic_url0)
        message = ''
    except (AttributeError, IndexError):
        comic_url0 = None
        message = 'not found!'
    return page_url0, comic_url0, message


def get_kingdom_data(comic, hyphenated_date: str,
                     session0: requests_html.HTMLSession) -> Tuple[str, str, str]:
    # https://comicskingdom.com/hagar-the-horrible/2022-04-24
    page_url0 = f'https://comicskingdom.com/{comic}/{hyphenated_date}'
    page_html = session0.get(page_url0).html
    try:
        img_element = page_html.find('img#theComicImage')[0]
        comic_url0 = img_element.attrs['src']
        message0 = ''
    except IndexError as e:
        comic_url0 = None
        message0 = f'{page_url0} {str(e)}'
    return page_url0, comic_url0, message0


def get_subtype_and_extension(http_headers):
    mimetype = http_headers['Content-Type']
    image_type = mime_split.match(mimetype)
    if image_type:
        subtype0 = image_type.group(1)
        extension = converter.get(subtype0, subtype0)
    else:
        subtype0, extension = 'oops', 'oops'
    return subtype0, extension


def download(url: str, session0: requests_html.BaseSession, page_url0: str, filename_base: str) \
        -> Tuple[BytesIO, str, str]:
    response = session0.get(url, headers={'Referer': page_url0})
    subtype0, extension = get_subtype_and_extension(response.headers)
    buffer0 = BytesIO()
    buffer0.write(response.content)
    filename0 = f'{filename_base}.{extension}'
    if options.verbose:
        print("Stored", url)
    return buffer0, subtype0, filename0


def create_mail(specified_date: datetime.date, config0: dict) -> EmailMessage:
    mail0 = EmailMessage()
    mail0.set_charset('utf-8')
    mail0['To'] = ','.join(config0['mail_to'])
    mail0['From'] = config0['mail_from']
    date_string = specified_date.strftime('%Y-%m-%d')
    mail0['Subject'] = f'Comics {date_string}'
    return mail0


def add_image(mail0: EmailMessage, buffer0: BytesIO, filename0: str, subtype0: str):
    buffer0.seek(0)
    img_data = buffer0.read()
    mail0.add_attachment(img_data, maintype='image',
                         filename=filename0,
                         subtype=subtype0)
    return


def add_text(mail0: EmailMessage, text: str):
    mail0.add_attachment(text.encode('utf-8'),
                         maintype='text', subtype='plain',
                         disposition='inline')
    return


def send_mail(mail0: EmailMessage):
    subprocess.run(SENDMAIL, input=mail0.as_bytes())
    return


oparser = argparse.ArgumentParser(description="Comic fetcher",
                                  formatter_class=argparse.ArgumentDefaultsHelpFormatter)

oparser.add_argument('-c', dest='config_file',
                     required=True,
                     metavar='JSON',
                     help='config file')

oparser.add_argument('-b', dest='back_days',
                     default=0,
                     type=int,
                     metavar='N',
                     help='fetch from N days before today')

oparser.add_argument("-v", dest="verbose",
                     default=False,
                     action='store_true',
                     help="verbose")

options = oparser.parse_args()

with open(options.config_file, 'r') as f:
    config = json.load(f)

session = requests_html.HTMLSession()
fetch_date = date.today() - timedelta(days=options.back_days)

mail = create_mail(fetch_date, config)

for comic_name, site in config['comics']:
    if options.verbose:
        print(comic_name, site)
    add_comic(mail, site, comic_name, fetch_date, session)

send_mail(mail)
