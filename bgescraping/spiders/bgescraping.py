from __future__ import division, absolute_import, unicode_literals
from scrapy import Spider, FormRequest, Request
import re
from selenium import webdriver
from time import sleep
import os
import requests


class BgeSpider(Spider):
    name = "bgescraping"
    start_urls = [
        'https://secure.bge.com/Pages/Login.aspx'
    ]
    passed_vals = []

    def __init__(self, username=None, password=None, download_directory=None, *args, **kwargs):
        super(BgeSpider, self).__init__(*args, **kwargs)
        self.user_name = username if username else 'ap@res1.net'
        self.password = password if password else 'paybgenow1!'
        self.download_directory = download_directory if download_directory else 'C:/Users/webguru/Downloads/BGE/'

        if not os.path.exists(self.download_directory):
            os.makedirs(self.download_directory)

        cwd = os.getcwd().replace("\\", "//").replace('spiders', '')
        opt = webdriver.ChromeOptions()
        # opt.add_argument('--headless')
        self.driver = webdriver.Chrome(executable_path='{}/chromedriver.exe'.format(cwd), chrome_options=opt)

        with open('{}/scrapy.log'.format(cwd), 'r') as f:
            self.logs = [i.strip() for i in f.readlines()]
            f.close()

    def login(self):
        while True:
            try:
                user_email = self.driver.find_element_by_xpath(
                    '//div[contains(@class, "exc-form-inner exc-tooltip")]//input[contains(@id, "Username")]')
                user_email.send_keys(self.user_name)
                password = self.driver.find_element_by_xpath(
                    '//div[contains(@class, "exc-form-group-double")]//input[contains(@id,"Password")]'
                )
                password.send_keys(self.password)
                btn_login = self.driver.find_element_by_xpath(
                    '//button[contains(@processing-button, "Signing In...")]'
                )
                btn_login.click()
                break
            except:
                sleep(10)
                continue

        while True:
            try:
                self.driver.find_element_by_xpath('//div[@id="callMeBackContainerApp"]')
                break
            except:
                sleep(100)
                continue

    def parse(self, response):

        opt = webdriver.ChromeOptions()
        self.driver.get(response.url)
        self.login()

        while True:
            try:
                if self.driver.current_url != 'https://secure.bge.com/MyAccount/MyBillUsage/Pages/Secure/AccountHistory.aspx':
                    self.driver.get('https://secure.bge.com/MyAccount/MyBillUsage/Pages/Secure/AccountHistory.aspx')

                account_selected = True
                while account_selected:
                    options = self.driver.find_elements_by_xpath('//select[@id="filter-statement-type"]//option')
                    if options:
                        statement_type = options[1]
                        statement_type.click()

                    search_button = self.driver.find_elements_by_xpath('//button[@id="filter-apply"]')
                    if search_button:
                        search_button[0].click()
                    else:
                        print "There is no search button"

                    account_number = self.driver.find_elements_by_xpath(
                        '//p[contains(text(), "Account")]//span[@class="exc-data-neutral"]'
                    )
                    account_number = account_number[0].text if account_number else None

                    all_pages_crawled = False
                    while not all_pages_crawled:

                        rows = self.driver.find_elements_by_xpath(
                            '//table[@class="table bill-history dataTable no-footer dtr-column collapsed"]//tbody//tr'
                        )

                        for row in rows:
                            bill_date_info = row.find_elements_by_xpath('.//td[@class="sorting_1"]')[0].text.split('/')
                            bill_date = bill_date_info[2] + bill_date_info[0] + bill_date_info[1]

                            pdf_link = row.find_elements_by_xpath('.//td[@class="action-cell"]/a')[0].get_attribute('href')
                            if '{}-{}'.format(account_number, bill_date) not in self.logs:
                                print '--------- downloading ---'
                                yield self.download_page(pdf_link, account_number, bill_date)

                        try:
                            self.driver.find_elements_by_xpath('//li[@class="paginate_button next"]')[0].click()
                        except:
                            all_pages_crawled = True

                    try:
                        self.driver.find_elements_by_xpath(
                            '//a[@class="btn btn-primary" and contains(text(), "Change Account")]')[0].click()
                    except:
                        account_selected = False

            except:
                sleep(2)
                continue

    def download_page(self, pdf_link, account_number=None, bill_date=None):

        raw_pdf = requests.get(pdf_link).content
        file_name = '{}{}_{}.pdf'.format(self.download_directory, account_number, bill_date)

        with open(file_name, 'wb') as f:
            f.write(raw_pdf)
            self.logger.info('{} is downloaded successfully'.format(account_number))
            f.close()
        self.write_logs('{}-{}'.format(account_number, bill_date))
        return {
            'file_name': file_name,
            'file_url': pdf_link,
            'account_number': account_number,
            'bill_date': bill_date
        }

    def date_to_string(self, d):
        d = d.split('/')
        return ''.join([i.zfill(2) for i in d])

    def write_logs(self, bill_id):
        cwd = os.getcwd().replace("\\", "//").replace('spiders', '')
        with open('{}/scrapy.log'.format(cwd), 'a') as f:
            f.write(bill_id + '\n')
            f.close()
        self.logs.append(bill_id)
