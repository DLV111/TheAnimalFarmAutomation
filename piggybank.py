from calendar import weekday
from web3 import Web3
import os
import logging
import sys
import time
import calendar
from datetime import datetime, date
from pushover import Client
from utils import eth2wei, prettyPrint, wei2eth, read_json_file, to_checksum, getLocalTime, addNewConfigOption
import traceback
import argparse
import configparser


PIGGYBANK_CONTRACT_ADDR = "0x1514c766127378ea9653f9f4428fe25f3fd256c3"

PIGGYBANK_ABI_FILE = "./abis/piggybank.json"
VERSION = '0.3'

class PiggyBank:
    def __init__(self, txn_timeout=120, gas_price=5, rpc_host="https://bsc-dataseed.binance.org:443",rounding=3, **kwargs):

        self.config_args = self.argparser()
        self.config_file = self.config_args['config_file']
        self.config = self.readInConfig()
        self.validateConfig()

        logging.info('"%s" Selected for processing' % self.wallet_friendly_name)
        self.rounding = rounding
        self.txn_timeout = txn_timeout
        self.gas_price = gas_price
        self.rpc_host = rpc_host

        # Init the pushover client if defined
        self.PushOverClientInit()

        # Initialize web3, and load the smart contract objects.
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_host))
        self.account = self.w3.eth.account.privateKeyToAccount(self.private_key)
        self.address = self.account.address
        self.w3.eth.default_account = self.address
        self.piggy_contract = self.w3.eth.contract(
            to_checksum(PIGGYBANK_CONTRACT_ADDR),
            abi=read_json_file(PIGGYBANK_ABI_FILE))

        self.piggybankCount = self.piggy_contract.functions.myPiggyBankCount(self.address).call()
        logging.info("You have %s piggy banks" % self.piggybankCount)

    def updatePiggyConfigFile(self,pbinfo):
        _parser = configparser.ConfigParser()
        anyUpdates = False
        config_file = self.config_args['config_file']
        if os.path.exists(config_file):
            _parser.read(config_file)
        for key,item in pbinfo.items():
            section = "piggybank_" + str(key)
            if not _parser.has_section(section):
                anyUpdates = True
                day = 0
                week = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
                while day < 6:
                    if day == 0:
                        _parser = addNewConfigOption(_parser, section, week[day], 'compound  # Options are compound or claim - if unknown will compound')
                    else:
                        _parser = addNewConfigOption(_parser, section, week[day], 'compound')
                    day += 1
        if anyUpdates:
            writemsg = "There has been a new piggy bank added to the config. Please review and update. Default action is to compound each day"
            self.writeConfigFile(_parser,writemsg=writemsg,dontexit=True)

    def calculateTruffleSell(self,truffles):
        print (self.piggy_contract.functions.calculateTruffleSell(truffles).call())
        print (wei2eth(self.piggy_contract.functions.calculateTruffleSell(truffles).call()))

    def getMyTruffles(self,ID):
        return self.piggy_contract.functions.getMyTruffles(ID).call()

    def myPiggyBankDetails(self):
        pbinfo = self.piggyBankInfo()
        self.my_piggybank = {} # This is an internal dict which contains all the info I need
        for pb in pbinfo:
            _ID = pb[0]
            _nextFeeding = pb[4] + 86400
            _timeToNextFeeding = _nextFeeding - int(time.time())
            currentTruffles = self.getMyTruffles(_ID)
            # self.calculateTruffleSell(currentTruffles)
            self.my_piggybank.update({
                _ID: {
                    "raw": pb,
                    "ID": _ID,
                    "isStakeOn": pb[1],
                    "hatcheryPiglets": pb[2],
                    "claimedTruffles": pb[3],
                    "lastFeeding": pb[4],
                    "lastCompounded": pb[5],
                    "trufflesUsed": pb[6],
                    "trufflesSold": pb[7],
                    "isMaxPayOut": pb[8],
                    "nextFeeding": _nextFeeding,
                    "timeToNextFeeding": _timeToNextFeeding,
                    "currentTruffles": currentTruffles,
                }
            })
        return (self.my_piggybank)

    def getActionForToday(self,ID):
        curr_date = date.today()
        day = str(calendar.day_name[curr_date.weekday()]).lower()
        config = self.readInConfig()
        try:
            return config['piggybank_' + str(ID)][day]
        except:
            return ('compound')

    def feedOrSleepOrClaim(self,pbinfo):
        logging.info("Working out if I feed or claim or sleep...")
        _farmerSleepTime = 86400 # Max of 1 day, but will be reduced as soon as this is run
        _nextFeedTime = ""
        for key,item in pbinfo.items():
            actionForToday = self.getActionForToday(key)
            #print ("key: %s - action: %s " % (key,actionForToday))
            nextFeed = (pbinfo[key]['timeToNextFeeding'])
            if nextFeed <=0:
                if actionForToday == "claim":
                    _msg = "Claiming the pigs - piggy bank number: %s - truffles: %s" % (key,self.my_piggybank[key]['currentTruffles'])
                    logging.info (_msg)
                    self.feedOrClaim(key,action=actionForToday)
                else:
                    _msg = "Feeding the pigs - piggy bank number: %s" % key
                    logging.info(_msg)
                    self.feedOrClaim(key)
            else:
                if nextFeed < _farmerSleepTime:
                    _farmerSleepTime = nextFeed
                    _nextFeedTime = pbinfo[key]['nextFeeding']

        logging.info("I will sleep for %s - Next feeding is at %s" % (_farmerSleepTime, getLocalTime(_nextFeedTime)))
        return(_farmerSleepTime)

    def feedOrClaim(self,ID,action='compound'):
        max_tries = self.max_tries
        retry_sleep = self.max_tries_delay
        default_sleep_between_actions=30  # This ensures enough time for the network to settle and provide accurate results.
        remaining_retries = max_tries
        txn_receipt = None
        if action == 'claim':
            tx = self.piggy_contract.functions.sellTruffles(ID).buildTransaction(
                {"gasPrice": eth2wei(self.gas_price, "gwei"),
                "from": self.address,
                "gas": 571431,
                "nonce": self.w3.eth.getTransactionCount(self.address)
            })
        else:
            tx = self.piggy_contract.functions.feedPiglets(ID).buildTransaction(
                {"gasPrice": eth2wei(self.gas_price, "gwei"),
                "from": self.address,
                "gas": 173344,
                "nonce": self.w3.eth.getTransactionCount(self.address)
            })

        if self.perform_piggybank_actions.lower() == "true":
            for _ in range(max_tries):
                try:
                    remaining_retries+=-1
                    tx = self.piggy_contract.functions.feedPiglets(ID).buildTransaction(
                        {"gasPrice": eth2wei(self.gas_price, "gwei"),
                        "from": self.address,
                        "gas": 173344,
                        "nonce": self.w3.eth.getTransactionCount(self.address)
                    })
                    #print(tx)
                    signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
                    txn = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                    txn_receipt = self.w3.eth.waitForTransactionReceipt(txn)
                    if txn_receipt and "status" in txn_receipt and txn_receipt["status"] == 1:
                        #logging.info("Transaction Successful: %s" % (self.w3.toHex(txn)))
                        #time.sleep(default_sleep_between_actions)
                        # self.getDripBalance()
                        if action == 'claim':
                            _msg = ("Successfully claimed %s truffles from the piggy bank %s - tx: https://bscscan.com/tx/%s" % (self.my_piggybank[ID]['currentTruffles'],ID,self.w3.toHex(txn)))
                        else:
                            _msg = ("Successfully fed the piggy bank %s - tx: https://bscscan.com/tx/%s" % (ID,self.w3.toHex(txn)))
                        logging.info(_msg)
                        self.sendMessage("Fed the piglets", _msg)
                        break
                    else:
                        logging.info(txn_receipt)
                        _msg = "Piglet feeding failed. %s retries remaining (%s seconds apart). Transaction status '%s' - tx https://bscscan.com/tx/%s" % (remaining_retries,retry_sleep,txn_receipt["status"],self.w3.toHex(txn))
                        logging.info(_msg)
                        #time.sleep(default_sleep_between_actions)
                        self.sendMessage("Failed piglet feeding",_msg)
                        logging.debug(txn_receipt)
                        if remaining_retries != 0:
                            time.sleep(retry_sleep)
                except:
                    logging.info(traceback.format_exc())
                    time.sleep(default_sleep_between_actions)
        else:
            logging.info("Compounding is set to False, only outputting some messages")
            #logging.info("Updated Drip balance is: %s (Increase %s)" % (self.DripBalance,self.getDripBalanceIncrease()))
            #self.sendMessage("Compounding Complete","Updated Balance %s (Increase %s) - tx %s" % (self.DripBalance,self.getDripBalanceIncrease(),'test:aaaabbbbccccdddd'))

    def piggyBankInfo(self):
        _piggyBankInfo = []
        for x in range(self.piggybankCount):
            _piggyBankInfo.append (self.piggy_contract.functions.piggyBankInfo(self.address,x).call())
        return (_piggyBankInfo)


    def validateConfig(self):
        if self.private_key == "":
            logging.info("private_key is not set")
            sys.exit(1)
        if self.wallet_friendly_name == "":
            logging.info("wallet_friendly_name is not set")
            sys.exit(1)
        if self.perform_piggybank_actions == "":
            logging.info("perform_piggybank_actions is not set")
            sys.exit(1)
        if self.max_tries == "":
            logging.info("max_tries is not set")
            sys.exit(1)
        if self.max_tries_delay == "":
            logging.info("max_tries_delay is not set")
            sys.exit(1)
        if self.min_bnb_balance == 'False':
            self.min_bnb_balance = False
        else:
            self.min_bnb_balance = float(self.min_bnb_balance)
        if self.pushover_api_key == 'False':
            self.pushover_api_key = False
        if self.pushover_user_key == 'False':
            self.pushover_user_key = False

    def readInConfig(self):
        config_file = self.config_file
        if self.config_args['new_config'] == True:
            self.createDefaultConfig(config_file)
        else: 
            try:
                config = configparser.ConfigParser({'min_bnb_balance': False, 'pushover_api_key': False, 'pushover_user_key': False}, inline_comment_prefixes="#")
                config.read(config_file)
                # [default]
                self.private_key = config['default']['private_key']
                self.wallet_friendly_name = config['default']['wallet_friendly_name']
                self.pushover_api_key = config['default']['pushover_api_key']
                self.pushover_user_key = config['default']['pushover_user_key']
                # [piggybank]
                self.perform_piggybank_actions = config['piggybank']['perform_piggybank_actions']
                self.max_tries = int(config['piggybank']['max_tries'])
                self.max_tries_delay = int(config['piggybank']['max_tries_delay'])
                self.min_bnb_balance = config['piggybank']['min_bnb_balance']
                return config
            except:
                logging.info('There was an error opening the config file %s' % config_file)
                logging.info('If this config file does not exist yet, run with -n to create')
                print(traceback.format_exc())
                sys.exit(2)

    def createDefaultConfig(self, config_file):
        _parser = configparser.ConfigParser()
        if os.path.exists(config_file):
            _parser.read(config_file)
        
        # defaults
        _parser = addNewConfigOption(_parser, 'default', 'private_key', '  # Mandatory - gives write access to your wallet KEEP THIS SECRET!!')
        _parser = addNewConfigOption(_parser, 'default', 'wallet_friendly_name', 'Test Wallet  # Mandatory - Friendly name to display in output')
        _parser = addNewConfigOption(_parser, 'default', 'pushover_api_key', 'False  # Optional - If you have an account on https://pushover.net/ you can set this up to send notfications to your phone.')
        _parser = addNewConfigOption(_parser, 'default', 'pushover_user_key', 'False  # Optional - If you have an account on https://pushover.net/ you can set this up to send notfications to your phone.')
        # piggybank
        _parser = addNewConfigOption(_parser, 'piggybank', 'perform_piggybank_actions', 'False  # Set to true to actually perform compounding')
        _parser = addNewConfigOption(_parser, 'piggybank', 'max_tries', '2  # Number of retries on a transaction failure - will cost gas each time. 2 means try once more if there is a failure.')
        _parser = addNewConfigOption(_parser, 'piggybank', 'max_tries_delay', '30  # Seconds between retries on a transaction failure. Wait this long before trying again.')
        _parser = addNewConfigOption(_parser, 'piggybank', 'min_bnb_balance', '0.02  # Optional -  Min BNB Balance to have in your wallet to allow compounding action')
        
        self.writeConfigFile(_parser)

    def writeConfigFile(self,parser,dontexit=False,writemsg=False):
        config_file = self.config_args['config_file']
        try:
            with open(config_file, "w") as f:
                parser.write(f)
                if writemsg:
                    logging.info(writemsg)
                else:
                    logging.info("Template file created &/or updated at '%s'. Please review" % config_file)
                if dontexit == False:
                    sys.exit(0)
        except IOError:
            logging.info('Unable to write template file')
            sys.exit(5)


    def argparser(self):
        import textwrap
        description = textwrap.dedent('''
            Piggy Bank Compounding

            You can use this script to compound your piggy bank's every 24h
            See the readme at https://github.com/DLV111/TheAnimalFarmAutomations for more details.
            If you like this please consider buying me a beer/coffee
        ''')
        parser = argparse.ArgumentParser(description=description,
                                        formatter_class=argparse.RawTextHelpFormatter)
        parser.add_argument("-n", "--new-config", action="store_true", help="Create a new config file at the location specified - If file exists no action is taken")
        parser.add_argument("config_file", help="Path to the config file")
        args = parser.parse_args()
        return(vars(args))

    def getAvailableClaims(self):
        self.claimsAvailable = round(wei2eth(self.piggy_contract.functions.claimsAvailable(self.address).call()),self.rounding)

    def getBNBbalance(self):
        self.BNBbalance = self.w3.eth.getBalance(self.address)
        self.BNBbalance = round(wei2eth(self.BNBbalance),self.rounding)

    def checkAvailableBNBBalance(self):
        logging.info('BNB Balance is %s' % round(self.BNBbalance,self.rounding))
        if self.min_bnb_balance:  # Do we have a min balance defined?
            if self.BNBbalance < self.min_bnb_balance:
                msg = 'Your current BNB balance(%s) is below min required (%s) for %s' % (self.BNBbalance, self.min_bnb_balance, self.wallet_friendly_name)
                logging.info(msg)
                self.sendMessage('BNB Balance issue',msg)
                sys.exit()

    def sendMessage(self, title_txt, body):
        if self.pushover_api_key and self.pushover_user_key:
            title_txt = ("%s: %s" % (self.wallet_friendly_name,title_txt) )
            logging.info("PushOver Notification\n\rTitle: %s\n\rBody: %s" % (title_txt,body))
            self.client.send_message(body, title=title_txt)

    def PushOverClientInit(self):
        if self.pushover_api_key and self.pushover_user_key:
            self.client = Client(self.pushover_user_key, api_token=self.pushover_api_key)

def main():
    # Setup logger.
    log_format = '%(asctime)s: %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_format, stream=sys.stdout)
    logging.info('Feeding pigs automation v%s Started!' % VERSION)
    logging.info('----------------')

    piggybank = PiggyBank()

    while True:
        pbinfo = piggybank.myPiggyBankDetails()
        # Loop through all the returned piggy banks to either sleep or compound
        # prettyPrint(pbinfo)
        piggybank.updatePiggyConfigFile(pbinfo)
        sleep_time = piggybank.feedOrSleepOrClaim(pbinfo)

        # sys.exit(2)
        time.sleep(sleep_time)

if __name__ == "__main__":
   main()
