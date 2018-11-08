#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crawler for novels from [LNMTL](https://lnmtl.com).
"""
import json
import logging
import re
from concurrent import futures

from bs4 import BeautifulSoup

from .app.crawler import Crawler
from .app.crawler_app import CrawlerApp

logger = logging.getLogger('LNMTL')

home_url = 'https://lnmtl.com'
login_url = 'https://lnmtl.com/auth/login'
logout_url = 'https://lnmtl.com/auth/logout'


class LNTMLCrawler(Crawler):
    @property
    def supports_login(self):
        return True
    # end def

    def login(self, email, password):
        '''login to LNMTL'''
        # Get the login page
        logger.info('Visiting %s', login_url)
        response = self.get_response(login_url)
        soup = BeautifulSoup(response.text, 'lxml')
        token = soup.select_one('form input[name="_token"]')['value']
        # Send post request to login
        logger.info('Logging in...')
        response = self.submit_form(
            login_url,
            _token=token,
            email=email,
            password=password,
        )
        # Check if logged in successfully
        soup = BeautifulSoup(response.text, 'lxml')
        if soup.select_one('a[href="%s"]' % logout_url):
            logger.warning('Logged in')
        else:
            body = soup.select_one('body').text
            logger.debug('-' * 80)
            logger.debug('\n\n'.join([
                x for x in body.split('\n\n')
                if len(x.strip()) > 0
            ]))
            logger.debug('-' * 80)
            logger.error('Failed to login')
        # end if
    # end def

    def logout(self):
        '''logout as a good citizen'''
        logger.debug('Logging out...')
        response = self.get_response(logout_url)
        soup = BeautifulSoup(response.text, 'lxml')
        if soup.select_one('a[href="%s"]' % logout_url):
            logger.error('Failed to logout.')
        else:
            logger.warning('Logged out.')
        # end if
    # end def

    def read_novel_info(self, url):
        '''get list of chapters'''
        logger.info('Visiting %s', url)
        response = self.get_response(url)
        soup = BeautifulSoup(response.text, 'lxml')

        title = soup.select_one('.novel .media .novel-name').text
        self.novel_title = title.rsplit(' ', 1)[0]
        logger.debug('Novel title = %s', self.novel_title)

        self.novel_cover = soup.find('img', {'title': self.novel_title})['src']
        logger.info('Novel cover = %s', self.novel_cover)

        self.parse_volume_list(soup)
        logger.debug(self.volumes)

        logger.info('%d volumes found.', len(self.volumes))
    # end def

    def parse_volume_list(self, soup):
        self.volumes = []
        for script in soup.find_all('script'):
            text = script.text.strip()
            if not text.startswith('window.lnmtl'):
                continue
            # end if
            i, j = text.find('lnmtl.volumes = '), text.find(';lnmtl.route')
            if i <= 0 and j <= i:
                continue
            # end if
            i += len('lnmtl.volumes =')

            volumes = json.loads(text[i:j].strip())
            for i, vol in enumerate(volumes):
                title = re.sub(r'[^\u0000-\u00FF]', '', vol['title'])
                title = re.sub(r'\(\)', '', title).strip()
                if not (title and re.match(r'volume \d+', title.lower())):
                    name = title
                    title = 'Volume %d' % (i + 1)
                    title += (' - ' + name) if name else ''
                # end if
                self.volumes.append({
                    'id': vol['id'],
                    'title': title,
                })
            # end for
            break
        # end for
    # end def

    def download_chapter_list(self):
        self.chapters = []
        page_url = '%s/chapter?page=1' % home_url
        future_to_url = {
            self.executor.submit(
                self.download_chapter_list_of_volume,
                index,
                page_url
            ): index
            for index in range(len(self.volumes))
        }
        for future in futures.as_completed(future_to_url):
            futures.wait(future.result())
        # end for
        self.chapters = sorted(self.chapters, key=lambda x: x['id'])
        logger.debug(self.chapters)
        logger.info('%d chapters found', len(self.chapters))
    # end def

    def download_chapter_list_of_volume(self, vol_index, page_url):
        vol_id = self.volumes[vol_index]['id']
        url = '%s&volumeId=%s' % (page_url, vol_id)
        logger.info('Visiting %s', url)
        result = self.get_response(url).json()
        page_url = result['next_page_url']
        for chapter in result['data']:
            title = 'Chapter #%s - %s' % (chapter['position'], chapter['title'])
            self.chapters.append({
                'title': title,
                'url': chapter['site_url'],
                'id': int(chapter['position']),
                'volume': self.volumes[vol_index]['title'],
            })
        # end for
        if result['current_page'] == 1:
            return {
                self.executor.submit(
                    self.download_chapter_list_of_volume,
                    vol_index,
                    '%s/chapter?page=%s' % (home_url, page + 1)
                ): '%s-%s' % (vol_id, page)
                for page in range(1, result['last_page'])
            }
        # end if
        return {}
    # end def

    def download_chapter_body(self, chapter):
        logger.info('Downloading %s', chapter['url'])
        response = self.get_response(chapter['url'])
        soup = BeautifulSoup(response.text, 'lxml')
        body = soup.select('.chapter-body .translated')
        body = [self.format_text(x.text) for x in body if x]
        body = '\n'.join(['<p>%s</p>' % (x) for x in body if len(x)])
        return body.strip()
    # end def

    def format_text(self, text):
        '''formats the text and remove bad characters'''
        text = text.replace(u'\u00ad', '')
        text = re.sub(r'\u201e[, ]*', '&ldquo;', text)
        text = re.sub(r'\u201d[, ]*', '&rdquo;', text)
        text = re.sub(r'[ ]*,[ ]+', ', ', text)
        return text.strip()
    # end def
# end class


class LNMTLCrawlerApp(CrawlerApp):
    crawler = LNTMLCrawler()
# end class


if __name__ == '__main__':
    LNMTLCrawlerApp().start()
# end if
