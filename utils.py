import re
from web3 import Web3
from decimal import Decimal
import logging
import traceback
import requests
import time
import datetime

def wei2eth(wei, unit="ether"):
    return Web3.fromWei(wei, unit)

def eth2wei(eth, unit="ether"):
    return Web3.toWei(eth, unit)

def to_checksum(address):
    return Web3.toChecksumAddress(address)

def read_json_file(filepath):
    try:
        with open(filepath) as fp:
            results = fp.read()
    except:
        logging.info('Error reading json file.')
        results = None
    return results

def decimal_round(decimal_number, decimal_places):
    return decimal_number.quantize(Decimal(10) ** -decimal_places)

def decimal_fix_places(decimal_number, decimals):
    if decimals is not None:
        return decimal_number / (10 ** decimals)
    else:
        raise Exception("decimal_fix_places(): Must supply a fixed amount of decimal places to fix number to.")

def is_percent_down(previous_amount, current_amount, percent_down):
    if previous_amount - current_amount > Decimal(previous_amount) * (Decimal(percent_down) / Decimal(100)):
        return True
    else:
        return False

def is_percent_up(previous_amount, current_amount, percent_up):
    if current_amount - previous_amount > Decimal(previous_amount) * (Decimal(percent_up) / Decimal(100)):
        return True
    else:
        return False

def pancakeswap_api_get_price(token_address, max_tries=1, type="tokens"):
    # response example: {"updated_at":1644451690368,"data":{"name":"USD Coin","symbol":"USDC","price":"0.999362623429255457703972330882","price_BNB":"0.002364980172183089994929542565945"}}
    for _ in range(max_tries):
        try:
            response = requests.get('https://api.pancakeswap.info/api/v2/%s/%s' % (type,token_address))
            return response.json()
        except:
            logging.info(traceback.format_exc())
    return None

def binance_api_get_price(symbol, max_tries=1):
    # example symbol, BNBBUSD
    for _ in range(max_tries):
        try:
            response = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=%s' % symbol)
            return response.json()
        except:
            logging.info(traceback.format_exc())
    return None

def getLocalTime(timeInEpoch):
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timeInEpoch))

def checkOptionExists(config,section,option):
    _regexp="[;#\s]*" + option
    for o in config.options(section):
        if re.match(_regexp,o):
            return True

def checkSectionExists(config,section):
    if config.has_section(section):
        return True
    else:
        return False

def addNewConfigOption(config,section,option,value):
    if not checkSectionExists(config, section):
        config.add_section(section)
    if not checkOptionExists(config, section, option):
        config.set(section, option, value)
    return config

def prettyPrint(data):
    import pprint
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(data)

def time_until_end_of_day(dt=None):
    if dt is None:
        dt = datetime.datetime.now()
    return ((24 - dt.hour - 1) * 60 * 60) + ((60 - dt.minute - 1) * 60) + (60 - dt.second)