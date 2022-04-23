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

import requests_html

mime_split = re.compile(r'image/(\w+).*')
converter = {'gif': 'gif',
             'jpeg': 'jpg'
             }


def get_comics_url(site0, comic, slashed_date0, hyphenated_date0, session0, headers0):
    if site0 == 'gocomics':
        return get_go_comics_url(comic, slashed_date0, hyphenated_date0, session0)
    if site0 == 'dilbert':
        return get_dilbert_url(comic, hyphenated_date0, session0)
    if options.verbose:
        print('invalid site:', site0)
    return None, None, None


def get_go_comics_url(comic, slashed_date0, hyphenated_date0, session0):
    # 'https://www.gocomics.com/adamathome/2020/10/08'
    page_url = 'https://www.gocomics.com/%s/%s' % (comic, slashed_date0)
    page_html = session0.get(page_url).html
    try:
        div_comic = page_html.find('div.comic')[0]
        comic_url = div_comic.attrs['data-image']
        filename = 'gocomics-%s-%s' % (comic, hyphenated_date0)
    except IndexError as e:
        comic_url = None
        filename = None
    return page_url, comic_url, filename


def get_dilbert_url(comic, hyphenated_date0, session0):
    # https://dilbert.com/strip/2020-12-21
    page_url = 'https://dilbert.com/strip/%s' % hyphenated_date0
    page_html = session0.get(page_url).html
    try:
        img_comic = page_html.find('img.img-responsive')[0]
        comic_url = img_comic.attrs['src']
        filename = 'dilbert-%s-%s' % (comic, hyphenated_date0)
    except IndexError as e:
        comic_url = None
        filename = None
    return page_url, comic_url, filename


def filename_extension(http_headers):
    try:
        mimetype = http_headers['Content-Type']
        image_type = mime_split.match(mimetype)
        if image_type:
            image_str = image_type.group(1)
            result = converter.get(image_str, image_str)
    except KeyError:
        result = 'dat'
    return result


# https://stackoverflow.com/questions/7243750/download-file-from-web-in-python-3
def download(url, file_path, session, headers, options):
    # TODO use BytesIO instead of tmp files
    #      but use filenames too to make attachments savable
    # TODO determine mime type of binary
    #      and set filename extension appropriately
    # TODO remove site from filename
    # open in binary mode
    response = session.get(url)
    full_path = file_path + '.' + filename_extension(response.headers)
    with open(full_path, "wb") as f:
        # get request
        # write to file
        f.write(response.content)
        if options.verbose:
            print("Saved", full_path)
    return full_path


def send_mail(links_files, date_string):
    mail = EmailMessage()
    mail.set_charset('utf-8')
    mail['To'] = ','.join(config['mail_to'])
    mail['From'] = config['mail_from']
    mail['Subject'] = f'Comics {date_string}'

    text = []
    delenda = []
    for k, v in links_files.items():
        if v:
            text.append(k)    # page URL
            text.append(v[0]) # comic URL
        else:
            text.append(k)
            text.append('%s IndexError' % k)
            delenda.append(k)
        text.append('')   # blank line

    for k in delenda:
        del links_files[k]

    # https://docs.python.org/3/library/email.examples.html
    for comic_url, file_path in links_files.values():
        if file_path:
            with open(file_path, 'rb') as fp:
                img_data = fp.read()
            mail.add_attachment(img_data, maintype='image',
                                filename=os.path.basename(file_path),
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

# TODO fix email to and from
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

links_files = dict()

for comic_name, site in config['comics']:
    if options.verbose:
        print(comic_name, site)
    page_url, comic_url, filename = get_comics_url(site, comic_name, slashed_date,
                                                   hyphenated_date, session, headers)
    if options.verbose:
        print(page_url, comic_url, sep='\n')
    if comic_url:
        file_path = os.path.join(out_dir, filename)
        full_path = download(comic_url, file_path, session, headers, options)
        links_files[page_url] = (comic_url, full_path)
    else:
        links_files[page_url] = None

send_mail(links_files, hyphenated_date)
