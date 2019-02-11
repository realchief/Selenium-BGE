from __future__ import division, absolute_import, unicode_literals
from scrapy import Spider, FormRequest, Request
import re
from selenium import webdriver
from time import sleep
import os
import urllib
import requests
import ssl
import csv
from selenium.webdriver.common.keys import Keys


class BgeSpider(Spider):
    name = "bgescraping"
    start_urls = [
        'https://secure.bge.com/Pages/Login.aspx'
    ]
    passed_vals = []

    def __init__(self, username=None, password=None, download_directory=None, *args, **kwargs):
        super(BgeSpider, self).__init__(*args, **kwargs)

        with open('BGE-account_number.csv', 'rb') as csvfile:
            reader = csv.reader(csvfile)
            self.password_list = []
            self.username_list = []
            self.account_number_list = []
            for row_index, row in enumerate(reader):
                if row_index != 0:
                    self.username_list.append(row[0])
                    self.password_list.append(row[1])
                    self.account_number_list.append(row[2])

        self.user_index = 0

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

    def login(self, user_index=None):
        while True:
            try:
                user_email = self.driver.find_element_by_xpath(
                    '//div[contains(@class, "exc-form-inner exc-tooltip")]//input[contains(@id, "Username")]')
                user_name = self.username_list[user_index]
                password = self.password_list[user_index]

                user_email.send_keys(user_name)
                user_password = self.driver.find_element_by_xpath(
                    '//div[contains(@class, "exc-form-group-double")]//input[contains(@id,"Password")]'
                )
                user_password.send_keys(password)
                btn_login = self.driver.find_element_by_xpath(
                    '//button[contains(@processing-button, "Signing In...")]'
                )
                btn_login.click()
                break
            except:
                sleep(10)
                continue

    def parse(self, response):

        all_users_option = True
        user_index = 0
        while all_users_option:

            try:

                no_thanks_button = self.driver.find_elements_by_xpath('//a[@title="No, thanks"]')
                if no_thanks_button:
                    no_thanks_button[0].click()

                if user_index == 0:
                    self.driver.get('https://secure.bge.com/pages/login.aspx')
                    self.login(user_index)

                if user_index > 0 and self.username_list[user_index-1] != self.username_list[user_index]:
                    self.driver.find_element_by_xpath(
                        '//button[contains(@title, "Sign Out")]'
                    ).click()
                    self.driver.get('https://secure.bge.com/pages/login.aspx')
                    self.login(user_index)

                sleep(5)

                if self.driver.current_url == 'https://secure.bge.com/Pages/Login.aspx?technicalError=true':
                    print "Login failed. Invalid username and password"
                    user_index = user_index + 1
                    if user_index > len(self.username_list) - 1:
                        all_users_option = False
                if self.driver.current_url == 'https://secure.bge.com/pages/login.aspx?TARGET=%2fPages%2fChangeAccount.aspx':
                    print "Login failed. Invalid username and password"
                    user_index = user_index + 1
                    if user_index > len(self.username_list) - 1:
                        all_users_option = False

                try:
                    if self.driver.current_url != 'https://secure.bge.com/Pages/ChangeAccount.aspx':
                        self.driver.get('https://secure.bge.com/Pages/ChangeAccount.aspx')

                    sleep(5)
                    account_number_search_input = self.driver.find_element_by_xpath(
                        '//div[contains(@id, "changeAccountDT_filter")]//input[contains(@type, "search")]')
                    sleep(5)
                    account_number = self.account_number_list[user_index]
                    account_number_search_input.send_keys(account_number)
                    sleep(5)
                    account_rows = self.driver.find_elements_by_xpath('//table[@id="changeAccountDT"]//tbody//tr')

                    account_rows[0].find_elements_by_xpath(
                        './/td[@class="action-cell ng-scope"]//button')[0].click()
                    sleep(5)

                    if self.driver.current_url != 'https://secure.bge.com/MyAccount/MyBillUsage/Pages/Secure/AccountHistory.aspx':
                        self.driver.get('https://secure.bge.com/MyAccount/MyBillUsage/Pages/Secure/AccountHistory.aspx')

                    sleep(5)

                    options = self.driver.find_elements_by_xpath('//select[@id="filter-statement-type"]//option')
                    if options:
                        statement_type = options[1]
                        statement_type.click()

                    sleep(5)
                    search_button = self.driver.find_elements_by_xpath('//button[@id="filter-apply"]')
                    if search_button:
                        search_button[0].click()
                    else:
                        print "There is no search button"

                    sleep(5)
                    no_thanks_button = self.driver.find_elements_by_xpath('//a[@title="No, thanks"]')
                    if no_thanks_button:
                        no_thanks_button[0].click()

                    all_pages_crawled = False
                    while not all_pages_crawled:
                        rows = self.driver.find_elements_by_xpath(
                            '//table[@class="table bill-history dataTable no-footer dtr-column collapsed"]//tbody//tr'
                        )
                        cookies = self.driver.get_cookies()
                        for row in rows:

                            no_thanks_button = self.driver.find_elements_by_xpath('//a[@title="No, thanks"]')
                            if no_thanks_button:
                                no_thanks_button[0].click()

                            bill_date_info = row.find_elements_by_xpath('.//td[@class="sorting_1"]')[0].text.split('/')
                            if "No data available in table" not in bill_date_info[0]:
                                bill_date = bill_date_info[2] + bill_date_info[0] + bill_date_info[1]
                                pdf_link = row.find_elements_by_xpath('.//td[@class="action-cell"]/a')[0].get_attribute('href')
                                if '{}-{}'.format(account_number, bill_date) not in self.logs:
                                    print '--------- downloading ---'
                                    yield self.download_page(pdf_link, account_number, bill_date, cookies)
                                    sleep(5)
                            else:
                                no_thanks_button = self.driver.find_elements_by_xpath('//a[@title="No, thanks"]')
                                if no_thanks_button:
                                    no_thanks_button[0].click()

                                user_index = user_index + 1
                                if user_index > len(self.username_list) - 1:
                                    all_users_option = False
                        try:
                            self.driver.find_elements_by_xpath('//li[@class="paginate_button next"]')[0].click()
                        except:
                            all_pages_crawled = True

                    change_account_btn = self.driver.find_elements_by_xpath(
                            '//a[@class="btn btn-primary" and contains(text(), "Change Account")]')
                    if change_account_btn:
                        change_account_btn[0].click()
                    else:
                        self.driver.get('https://secure.pepco.com/Pages/ChangeAccount.aspx')
                    sleep(3)
                except:
                    continue
                    sleep(2)

                print('===========All files of your account have been downloaded================')
                user_index = user_index + 1
                if user_index > len(self.username_list) - 1:
                    all_users_option = False

            except:
                sleep(2)
                continue

        print('===========All files of all users have been downloaded================')
        # self.driver.close()

    def download_page(self, pdf_link, account_number=None, bill_date=None, cookies=None):

        s = requests.Session()
        for cookie in cookies:
            s.cookies.set(cookie['name'], cookie['value'])

        raw_pdf = s.get(pdf_link).content
        file_name = '{}pdf_{}_{}.pdf'.format(self.download_directory, account_number, bill_date)

        with open(file_name, 'wb') as f:
            f.write(raw_pdf)
            sleep(10)
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
