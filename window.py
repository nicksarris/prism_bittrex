__author__ = 'Nick Sarris (ngs5st)'

import os
import sys

import datetime
import operator
import dateutil.parser
from datetime import timedelta

from PySide.QtCore import *
from PySide.QtGui import *
import Resources.main_gui
from Resources.bittrex_api import *

import xml.dom.minidom as m
import xml.etree.ElementTree as ET

class print_stream(QObject):

    def write(self, text):
        self.textWritten.emit(str(text))
    def flush(self):
        pass

def resource_path(relative):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(relative)

class MainWindow(QMainWindow, Resources.main_gui.Ui_Prism_v2):

    def __init__(self, parent=None):

        super(MainWindow, self).__init__(parent)
        self.setupUi(self)

        self.buildNumber = '1'
        self.versionNumber = '1.0.0'
        self.counter = 0

        self.initial_verification()
        self.update_table(first=True)
        self.settings_display(first=True)

        self.console_1 = QTextEdit()
        self.bot_log.addWidget(self.console_1, 1, 0, 1, 1)
        self.console_1.setReadOnly(True)
        sys.stdout = print_stream()
        self.connect(sys.stdout, SIGNAL('textWritten(QString)'), self.print)

        # Set-Up Button Functionality
        self.connect(self.start_button, SIGNAL("clicked()"), self.buy_coins)
        self.connect(self.stop_button, SIGNAL("clicked()"), self.end_process)
        self.connect(self.sell_button, SIGNAL("clicked()"), self.sell_everything)
        self.connect(self.add_blacklist, SIGNAL("clicked()"), self.save_blacklist)
        self.connect(self.save_exchange, SIGNAL("clicked()"), self.verify_api)

    class CoinThread(QThread):

        def __init__(self, coins, key, secret, blacklist):

            super().__init__()
            self.btc = coins
            self.api = bittrex(key, secret)
            self.blacklist = blacklist

        def __del__(self):
            try:
                self.quit()
            except:
                pass

        def select_coins(self):

            coin_list = []
            blacklisted_coins = []
            coins = self.api.getmarketsummaries()

            for val in self.blacklist:
                list.append(blacklisted_coins, val.split('-')[1])

            for coin in coins:
                volume = coin['BaseVolume']
                base = coin['MarketName'].split('-')[0]
                name = coin['MarketName'].split('-')[1]

                if volume > 100:
                    if base == 'BTC':
                        if name not in (['BTC', 'BTG', 'USDT']
                                + blacklisted_coins):
                            if name not in coin_list:
                                list.append(coin_list, 'BTC-' + name)

            return coin_list

        def get_points(self, coin_list):

            final_data = []
            for pair in coin_list:

                bitcoin_buy_2 = 0
                bitcoin_sell_2 = 0
                bitcoin_sell_5 = 0
                bitcoin_sell_10 = 0

                final_rate_2 = None
                final_rate_5 = None
                final_rate_10 = None

                sell_counter_2 = 0
                buy_book = self.api.getorderbook(pair, 'buy')
                sell_book = self.api.getorderbook(pair, 'sell')
                initial_rate = self.api.getticker(pair)['Last']

                for sell in sell_book:

                    if bitcoin_sell_2 <= 2:
                        bitcoin_sell_2 += float(sell['Quantity'] * sell['Rate'])
                        final_rate_2 = sell['Rate']
                        sell_counter_2 += 1
                    if bitcoin_sell_5 <= 5:
                        bitcoin_sell_5 += float(sell['Quantity'] * sell['Rate'])
                        final_rate_5 = sell['Rate']
                    if bitcoin_sell_10 <= 10:
                        bitcoin_sell_10 += float(sell['Quantity'] * sell['Rate'])
                        final_rate_10 = sell['Rate']

                ratio_change_2 = final_rate_2 / initial_rate
                ratio_change_5 = final_rate_5 / initial_rate
                ratio_change_10 = final_rate_10 / initial_rate

                buy_counter = 0
                for buy in buy_book[:sell_counter_2]:

                    if buy_counter <= sell_counter_2:
                        bitcoin_buy_2 += float(buy['Quantity'] * buy['Rate'])
                    buy_counter += 1

                ratio_market = bitcoin_buy_2 / bitcoin_sell_2
                list.append(final_data, [pair, ratio_market,
                    ratio_change_2, ratio_change_5, ratio_change_10])

            return final_data

        def get_final(self, final_data):

            max_2 = 0
            max_5 = 0
            max_10 = 0

            coin_list = []
            blacklisted_coins = []
            revised_final = []
            coins = self.api.getbalances()

            for coin in coins:
                if coin['Currency'] not in (['BTC', 'BTG', 'USDT']
                        + blacklisted_coins):
                    if coin['Balance'] != 0.0:
                        list.append(coin_list, 'BTC-' + coin['Currency'])

            for data in final_data:

                if data[2] > max_2: max_2 = data[2]
                if data[3] > max_5: max_5 = data[3]
                if data[4] > max_10: max_10 = data[4]

            for data in final_data:
                ratio_2 = (data[2] / max_2) * 100
                ratio_5 = (data[3] / max_5) * 100
                ratio_10 = (data[4] / max_10) * 100
                ratio = ((ratio_2 + ratio_5 + ratio_10) / 3)

                if ratio > 87:
                    if data[1] > 1:
                        if data[0] not in coin_list:
                            list.append(revised_final,
                                [data[0], data[4], ratio])

            revised_final = sorted(revised_final,
                key=operator.itemgetter(1), reverse=True)

            return revised_final[:5]

        def buy_coins(self, revised_final):

            coin_list = []
            blacklisted_coins = []
            coins = self.api.getbalances()

            for val in self.blacklist:
                list.append(blacklisted_coins, val.split('-')[1])

            for coin in coins:
                if coin['Currency'] not in (['BTC', 'BTG', 'USDT']
                        + blacklisted_coins):
                    if coin['Balance'] != 0.0:
                        list.append(coin_list, 'BTC-' + coin['Currency'])

            position_btc = float(self.btc)
            if position_btc <= .05:
                num_positions = 8
            else:
                num_positions = 15

            bought_list = []
            for val in revised_final:
                if val[0] not in coin_list:
                    if (len(coin_list) + len(bought_list)) < int(num_positions):
                        list.append(bought_list, val[0])
                        time.sleep(1)
                    else:
                        print("{}: Not Enough Positions".format(val[0]))
                else:
                    print("{}: Already Bought".format(val[0]))
            self.buy_market(bought_list, coin_list, position_btc, num_positions)

        def buy_market(self, bought_list, coin_list, final_btc, num_positions):

            for coin in bought_list:

                current_price = self.api.getticker(coin)['Last']
                current_ask = self.api.getticker(coin)['Ask']

                if ((current_ask - current_price) /
                        (current_ask)) * 50 < 3:

                    price_change = 0
                    current_bought = 0
                    price_list = []

                    order_book = self.api.getorderbook(coin, 'sell')[:10]
                    for value in order_book:
                        list.append(price_list, [value['Rate'] *
                                                 value['Quantity'], value['Rate']])
                    for value in price_list:
                        if float(current_bought) <= final_btc:
                            price_change = value[1]
                            current_bought += value[0]
                        else:
                            continue

                    initial_price = price_list[0][1]
                    price_ratio = price_change / initial_price
                    if price_ratio <= 1.01:
                        if len(coin_list) < int(num_positions):
                            print("{}: Currently Placing a Buy Order".format(coin))
                            self.api.buylimit(market=coin,
                                              quantity=(0.99 * final_btc / price_change),
                                              rate=round(price_change, 8))
                            time.sleep(2)
                            self.api.selllimit(market=coin,
                                               quantity=(0.99 * final_btc / price_change),
                                               rate=round(price_change * (1 + (int(10) / 100)), 8))

        def buy_phase(self):

            data = self.select_coins()
            data = self.get_points(data)
            final = self.get_final(data)

            data_markets = []
            for val in final:
                if val[0] not in data_markets:
                    list.append(data_markets, val[0])
            data_string = ", ".join(data_markets)
            print("Currently Looking at Markets: {}".format(data_string))

            print('')
            self.buy_coins(final)
            print('')

            coin_list = []
            coins = self.api.getbalances()
            for coin in coins:
                if coin['Currency'] not in ['USDT', 'BTC', 'BTG']:
                    if coin['Balance'] != 0.0:
                        if coin['Currency'] not in coin_list:
                            list.append(coin_list, coin['Currency'])

            for coin in coin_list:
                current_price = self.api.getticker('BTC-' + coin)['Last']
                current_profit = 100 * (current_price / self.api.getorderhistory(
                    'BTC-' + coin)[0]['PricePerUnit'])
                print("{} | Relation to Buy-In: {}%".format(coin, round(current_profit, 2)))
            print('')

            print("Currently Waiting for Next Buy Phase")
            time.sleep(600)

        def run(self):

            print("\nInitializing the Prism Platform... \n\n"
            "Use this software at your own risk. You are responsible for "
            "your own investments. Past performance is not necessarily "
            "indicative of future results. The authors and all affiliates "
            "are not accountable for any losses incurred during your "
            "trading. \n")

            while True:

                try:
                    self.buy_phase()
                except:
                    self.print("Error. Disconnected from API. Retrying. \n")

    def print(self, text):

        if (text != ''):
            out = text
            self.console_1.moveCursor(QTextCursor.End)
            self.console_1.insertPlainText(out)

    def buy_coins(self):

        if self.counter < 1:
            self.counter += 1

            blacklisted_coins = []
            data_1 = ET.parse(resource_path(
                os.path.join('Data', 'verification.xml')))
            data_2 = ET.parse(resource_path(
                os.path.join('Data', 'blacklist.xml')))

            verification = data_1.getroot()
            blacklist = data_2.getroot()

            for i in blacklist:
                list.append(blacklisted_coins, 'BTC-' + i[0].text)

            self.thread_1 = self.CoinThread(
                verification[0][0].text, verification[0][1].text,
                verification[0][2].text, blacklisted_coins)
            self.thread_1.start()

        else:
            self.print("Error. Prism Already Running. \n")

    def end_process(self):

        if self.counter == 0:
            self.print('Error. No Current Process to Stop. \n')
        else:
            self.counter -= 1
            try:
                self.thread_1.terminate()
                self.print('Success! Terminating the Current Script. \n')
            except:
                self.print("Error. Some Settings are Currently Missing. \n")

    def delete_blacklist(self, who):

        treeUser = ET.parse(resource_path(
            os.path.join('Data', 'blacklist.xml')))
        rootUser = treeUser.getroot()
        rootUser.remove(rootUser[who])
        treeUser.write(resource_path(
            os.path.join('Data', 'blacklist.xml')))

        self.blacklist_table.removeRow(who)
        self.update_table()

    def initial_verification(self):

        settings = ET.parse(resource_path(
            os.path.join('Data', 'verification.xml'))).getroot()

        try:
            settings_list = []
            list.append(settings_list, [
                settings[0][0].text, settings[0][1].text, settings[0][2].text])

            self.settings_key_2.setText(settings_list[0][0])
            self.settings_key.setText(settings_list[0][1])
            self.settings_secret.setText(settings_list[0][2])
            self.verification.setText(settings_list[0][1])

        except:
            pass

    def update_table(self, first=None):

        treeUser = ET.parse(resource_path(
            os.path.join('Data', 'blacklist.xml')))
        rootUser = treeUser.getroot()
        users = len(rootUser.findall('configuration'))

        self.blacklist_table.clearContents()
        self.blacklist_table.horizontalHeader().setResizeMode(
            QHeaderView.ResizeToContents)

        x = 0
        while x < users:
            if first == True:
                rowPos = self.blacklist_table.rowCount()
                self.blacklist_table.insertRow(rowPos)

            coin = QTableWidgetItem(rootUser[x][0].text)
            exchange = QTableWidgetItem('Bittrex')

            self.blacklist_table.setItem(x, 0, coin)
            self.blacklist_table.setItem(x, 1, exchange)

            self.delete = QPushButton()
            self.connect(self.delete, SIGNAL("clicked()"), lambda who=x: self.delete_blacklist(who))
            self.blacklist_table.setCellWidget(x, 2, self.delete)
            x += 1

    def verify_api(self):

        if self.settings_key.text() == '' or \
           self.settings_secret.text() == '':

            msg = QMessageBox()
            msg.setWindowIcon(self.style().standardIcon(QStyle.SP_MessageBoxWarning))
            msg.setWindowTitle("Error")
            msg.setText("Please Fill in all Fields!")
            msg.exec_()

        else:

            key_to_check = self.settings_key.text()
            secret_to_check = self.settings_secret.text()
            api = bittrex(key_to_check, secret_to_check)

            test_1 = api.getbalances()
            test_2 = api.getticker('BTC-NXS')
            test_3 = api.getorderhistory('BTC-OMG')

            if test_1 != "APIKEY_INVALID" and \
               test_3 != "APIKEY_INVALID" and \
               test_2 != "INVALID_MARKET":

                doc = m.parse(resource_path(
                    os.path.join('Data', 'verification.xml')))
                root = doc.getElementsByTagName("data").item(0)
                conf = doc.createElement('configuration')

                num = doc.createElement('num')
                num_value = doc.createTextNode(self.settings_key_2.text())
                num.appendChild(num_value)

                key = doc.createElement('key')
                key_value = doc.createTextNode(self.settings_key.text())
                key.appendChild(key_value)

                secret = doc.createElement('secret')
                secret_value = doc.createTextNode(self.settings_secret.text())
                secret.appendChild(secret_value)

                conf.appendChild(num)
                conf.appendChild(key)
                conf.appendChild(secret)
                root.appendChild(conf)

                doc.writexml(open(resource_path(
                    os.path.join('Data', 'verification.xml')), "w"))
                treeUser = ET.parse(resource_path(
                    os.path.join('Data', 'verification.xml')))
                rootUser = treeUser.getroot()
                users = len(rootUser.findall('configuration'))

                if users > 1:
                    rootUser.remove(rootUser[0])
                    treeUser.write(resource_path(
                        os.path.join('Data', 'verification.xml')))

                self.settings_key_2.setAlignment(Qt.AlignLeft)
                self.settings_key.setAlignment(Qt.AlignLeft)
                self.settings_secret.setAlignment(Qt.AlignLeft)
                self.verification.setText(self.settings_key.text())

            else:
                self.verification.setText("FAILED")

    def save_blacklist(self):

        if self.coin_blacklist.text() == '':

            msg = QMessageBox()
            msg.setWindowIcon(self.style().standardIcon(QStyle.SP_MessageBoxWarning))
            msg.setWindowTitle("Error")
            msg.setText("Please Fill in all Fields!")
            msg.exec_()

        else:

            blacklisted_coins = []
            blacklist = ET.parse(resource_path(
                os.path.join('Data', 'blacklist.xml'))).getroot()

            try:
                for i in blacklist:
                    list.append(blacklisted_coins, i[0].text)
            except:
                pass

            if self.coin_blacklist.text() in blacklisted_coins:
                pass

            else:

                doc = m.parse(resource_path(
                    os.path.join('Data', 'blacklist.xml')))
                root = doc.getElementsByTagName("data").item(0)
                conf = doc.createElement('configuration')

                coin = doc.createElement('coin')
                coin_value = doc.createTextNode(self.coin_blacklist.text())
                coin.appendChild(coin_value)

                conf.appendChild(coin)
                root.appendChild(conf)

                doc.writexml(open(resource_path(
                    os.path.join('Data', 'blacklist.xml')), "w"))

                self.coin_blacklist.setAlignment(Qt.AlignLeft)
                self.coin_blacklist.clear()

                rowPos = self.blacklist_table.rowCount()
                self.blacklist_table.insertRow(rowPos)
                self.update_table()

    def settings_display(self, first=True):

        x = 0
        while (x < 1):
            self.select_exchange.addItem(
                "Bittrex")
            x += 1

    def sell_everything(self):

        if self.counter == 0:

            blacklisted_coins = []
            data_1 = ET.parse(resource_path(
                os.path.join('Data', 'verification.xml')))
            data_2 = ET.parse(resource_path(
                os.path.join('Data', 'blacklist.xml')))

            verification = data_1.getroot()
            blacklist = data_2.getroot()
            api = bittrex(verification[0][1].text,
                          verification[0][2].text)

            for i in blacklist:
                list.append(blacklisted_coins, 'BTC-' + i[0].text)

            try:
                coins = api.getbalances()
                for coin in coins:
                    if coin['Currency'] not in ['USDT', 'BTC', 'BTG']:
                        if coin['Balance'] != 0.0:
                            coin_to_search = coin['Currency']
                            uuid = (api.getopenorders('BTC-' + coin_to_search)[0]['OrderUuid'])
                            api.cancel(uuid)
                            prices = api.getticker('BTC-' + coin_to_search)
                            api.selllimit(market='BTC-' + coin_to_search,
                                          quantity=coin['Balance'],
                                          rate=round(prices['Last'] * 0.8, 8))
            except:
                coins = api.getbalances()
                for coin in coins:
                    if coin['Currency'] not in ['USDT', 'BTC', 'BTG']:
                        if coin['Balance'] != 0.0:
                            coin_to_search = coin['Currency']
                            prices = api.getticker('BTC-' + coin_to_search)
                            api.selllimit(market='BTC-' + coin_to_search,
                                          quantity=coin['Balance'],
                                          rate=round(prices['Last'] * 0.8, 8))

        else:
            self.counter -= 1
            self.print('Success! Selling and Ending Scripts. \n')

            blacklisted_coins = []
            data_1 = ET.parse(resource_path(
                os.path.join('Data', 'verification.xml')))
            data_2 = ET.parse(resource_path(
                os.path.join('Data', 'blacklist.xml')))

            verification = data_1.getroot()
            blacklist = data_2.getroot()
            api = bittrex(verification[0][0].text,
                          verification[0][1].text)

            for i in blacklist:
                list.append(blacklisted_coins, 'BTC-' + i[0].text)

            try:
                coins = api.getbalances()
                for coin in coins:
                    if coin['Currency'] not in ['USDT', 'BTC', 'BTG']:
                        if coin['Balance'] != 0.0:
                            coin_to_search = coin['Currency']
                            uuid = (api.getopenorders('BTC-' + coin_to_search)[0]['OrderUuid'])
                            api.cancel(uuid)
                            prices = api.getticker('BTC-' + coin_to_search)
                            api.selllimit(market='BTC-' + coin_to_search,
                                               quantity=coin['Balance'],
                                               rate=round(prices['Last'] * 0.8, 8))
            except:
                coins = api.getbalances()
                for coin in coins:
                    if coin['Currency'] not in ['USDT', 'BTC', 'BTG']:
                        if coin['Balance'] != 0.0:
                            coin_to_search = coin['Currency']
                            prices = api.getticker('BTC-' + coin_to_search)
                            api.selllimit(market='BTC-' + coin_to_search,
                                               quantity=coin['Balance'],
                                               rate=round(prices['Last'] * 0.8, 8))
