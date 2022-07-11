# TheAnimalFarmAutomation

## Disclaimer

This is automation that I have written for my own personal use. If you choose to use this, then I take no responsibility for errors etc.

Also never share your ``PRIVATE KEY``. This code has been designed so the private key information does NOT, nor should it sit in the same directory with this automation.

Any information below is my personal view and is not financial advice. Always do your own research and only invest money you can afford to lose.

## Introduction

This is to automate the daily compounding or claiming of the piggy bank for the website https://animalfarm.app/piggy-bank

I spent many hours working on this and making it user friendly, if you appreciate my work and it has saved you some time please consider a donation - See end of this readme.

If you do run into problems please raise an issuse against this repo, and if you want to chat to me please reach out on telegram https://t.me/Zobah111 and I will reply when I can.

## Prerequisites

* Somewhere to run this automation - while you can run it manually and it will compound stuff if missed in the last 24 hours, it is much better to run it all the time. Invest in a raspberry Pi 4, or some cloud compute.
* Docker - Here is a comprehensive guide to set it up, and a direct link to setting up your computer. If you get the "hello world" demo working, then this automation will run fine.
   * https://docker-curriculum.com/#setting-up-your-computer
* docker-compose - while not 100% required if you have knowlege around running docker manually - running it under docker-compose will make it much easier for you if you are a beginner (eg use the file I've created)
   * https://docs.docker.com/compose/install/

## Running for the first time

When you run this program for the very first time you need to create the config file. The below is all for a Linux OS, if you are running in windows you may need to update the paths.

If you already use my drip automation located here https://github.com/DLV111/DripCompound then you can use the same config file, just make sure you back it up first before running for the first time.

This will create the template file in /tmp/my_config.ini - As mentioned if you already use the drip wallet, it should just add in the piggybank sections

Note: You will only modify paths to the left of the ``:`` like /tmp, $PWD (which is a short cut to my current directory in linux). Everything to the right is inside the container so don't change!

Make sure this is run inside the folder where piggybank.py is.

``` bash
$ docker run --rm -ti -v /tmp/:/config/ -v "$PWD":/usr/src/myapp dlv111/crypto-web3:latest python piggybank.py -n /config/my_config.ini
2022-07-07 11:33:48,231: Feeding pigs automation v0.7 Started!
2022-07-07 11:33:48,231: ----------------
2022-07-07 11:33:48,233: Template file created &/or updated at '/config/my_config.ini'. Please review

```

``` ini

$ cat /tmp/my_config.ini
[default]
private_key =   # Mandatory - gives write access to your wallet KEEP THIS SECRET!!
wallet_friendly_name = Test Wallet  # Mandatory - Friendly name to display in output
pushover_api_key = False  # Optional - If you have an account on https://pushover.net/ you can set this up to send notfications to your phone.
pushover_user_key = False  # Optional - If you have an account on https://pushover.net/ you can set this up to send notfications to your phone.

[piggybank]
perform_piggybank_actions = False  # Set to true to actually perform compounding
max_tries = 2  # Number of retries on a transaction failure - will cost gas each time. 2 means try once more if there is a failure.
max_tries_delay = 30  # Seconds between retries on a transaction failure. Wait this long before trying again.
min_bnb_balance = 0.02  # Optional -  Min BNB Balance to have in your wallet to allow compounding action
```

## Running the piggybank automation

After you have done your configuration, you can now run the automation. If running from docker review the file ``docker-compose.piggybank.yml`` my recommendation is to copy this file outside of the git repo, and update the volumes to point to the required files. If you wish to build the docker files locally then uncomment the relevant section. 

The /etc/localtime bit ensure all the dates/times presented to you are in your timezone as the container by default will run in UTC. If you see dates/times that look weird check the timezones and see if they make more sense by converting that date/time from UTC -> your local time.

When you are ready, run this. If you omit the ``-d``, you will see all your output on the screen. The -d stands for daemon mode, eg run in the background.

``` bash
$ docker-compose -f docker-compose.piggybank.yml up -d
Creating network "theanimalfarmautomation_default" with the default driver
Creating af_piggybank ... done
```

As soon as it runs, it will further populate the configuration file with every piggybank it sees, and you can then update it as required.

Any combination is possible, default is all compounds.

---
**_NOTE:_** The action of the each piggybank ``[piggybank_x]`` is read just before each action, so there is no need to restart the program on updating the config file.

---

``` ini
[piggybank_0]
sunday = compound  # Options are compound, claim or skip - if unknown will compound
monday = skip
tuesday = claim
wednesday = skip
thursday = compound
friday = skip
saturday = compound
```

## Monitoring the usage

If you don't know normal docker commands your friend is..

``` bash
docker ps # to get container names
docker logs -f af_piggybank --tail=30
docker restart af_piggybank # If you need to restart the container for some reason, generally only required on a code update or modificiation of the common sections (eg [default], [piggybank]). Restart is not required on change of action.
```

## Donations/Referrals

1. If you'd like to donate some $$ please do so to this address (BNB/BUSD) please! ``0xfdb5550aa2145573cf878e6e90e061c611d170b8``
2. If you are considering signing up to drip/animal farm jump into our telegram channel https://t.me/flowriders and mention that https://t.me/Zobah111 sent you. The team has some great sign up bonuses and is a helpful and friendly group.
3. [Credefi](https://credefi.finance/) is an upcoming lending group which performs lending for real-economy projects. They provide returns between 10% and 40% on stable coins (you choose your risk). If you are looking for a place to diversify your stable coin investments and decide to use this platform, please use my referral link [https://platform.credefi.finance/l/5rnhyju](https://platform.credefi.finance/l/5rnhyju)