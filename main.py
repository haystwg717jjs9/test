import argparse
import json
import logging
import logging.handlers as handlers
import random
import sys
from pathlib import Path

from src import (Browser, DailySet, Discord, Login, MorePromotions, PunchCards,
                 Redeem, Searches)
from src.constants import VERSION
from src.loggingColoredFormatter import ColoredFormatter

POINTS_COUNTER = 0


def main():
    setupLogging()
    Discord.check_json()
    loadedAccounts = setupAccounts()
    for currentAccount in loadedAccounts:
        try:
            executeBot(currentAccount)
        except Exception as e:
            logging.error(f"{e.__class__.__name__}: {e}")


def setupLogging():
    format = "%(asctime)s [%(levelname)s] %(message)s"
    terminalHandler = logging.StreamHandler(sys.stdout)
    terminalHandler.setFormatter(ColoredFormatter(format))

    (Path(__file__).resolve().parent / "logs").mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format=format,
        handlers=[
            handlers.TimedRotatingFileHandler(
                "logs/activity.log",
                when="midnight",
                interval=1,
                backupCount=2,
                encoding="utf-8",
            ),
            terminalHandler,
        ],
    )


def argumentParser():
    parser = argparse.ArgumentParser(description="Microsoft Rewards Farmer")
    parser.add_argument(
        "-v", "--visible", action="store_true", help="Optional: Visible browser"
    )
    parser.add_argument(
        "-l", "--lang", type=str, default=None, help="Optional: Language (ex: en)"
    )
    parser.add_argument(
        "-g", "--geo", type=str, default=None, help="Optional: Geolocation (ex: US)"
    )
    parser.add_argument(
        "-wh", "--webhook", action="store_true", help="Optional: send a discord webhook message with the summary"
    )
    parser.add_argument(
        "-s", "--shuffle", action="store_true", help="Optional: shuffle the order in which accounts will be farmed on"
    )
    parser.add_argument(
        "-r", "--redeem", action="store_true", help="Optional: auto redeem rewards based on the goal set in the microsoft account"
    )
    parser.add_argument(
        "-p",
        "--proxy",
        type=str,
        default=None,
        help="Optional: Global Proxy (ex: http://user:pass@host:port)",
    )
    return parser.parse_args()


def bannerDisplay():
    farmerBanner = """
    ███╗   ███╗███████╗    ███████╗ █████╗ ██████╗ ███╗   ███╗███████╗██████╗
    ████╗ ████║██╔════╝    ██╔════╝██╔══██╗██╔══██╗████╗ ████║██╔════╝██╔══██╗
    ██╔████╔██║███████╗    █████╗  ███████║██████╔╝██╔████╔██║█████╗  ██████╔╝
    ██║╚██╔╝██║╚════██║    ██╔══╝  ██╔══██║██╔══██╗██║╚██╔╝██║██╔══╝  ██╔══██╗
    ██║ ╚═╝ ██║███████║    ██║     ██║  ██║██║  ██║██║ ╚═╝ ██║███████╗██║  ██║
    ╚═╝     ╚═╝╚══════╝    ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝"""
    logging.error(farmerBanner)
    logging.warning(
        f"        by Charles Bel (@charlesbel)               version {VERSION}\n"
    )


def setupAccounts() -> dict:
    accountPath = Path(__file__).resolve().parent / "accounts.json"
    if not accountPath.exists():
        accountPath.write_text(
            json.dumps(
                [{"username": "Your Email", "password": "Your Password"}], indent=4
            ),
            encoding="utf-8",
        )
        noAccountsNotice = """
    [ACCOUNT] Accounts credential file "accounts.json" not found.
    [ACCOUNT] A new file has been created, please edit with your credentials and save.
    """
        logging.warning(noAccountsNotice)
        exit()
    loadedAccounts = json.loads(accountPath.read_text(encoding="utf-8"))

    args = argumentParser()

    if args.shuffle:  
        random.shuffle(loadedAccounts)

    return loadedAccounts


def executeBot(currentAccount):
    logging.info(
        f'********************{ currentAccount.get("username", "") }********************'
    )
    with Browser(
        mobile=False, account=currentAccount, args=argumentParser()
    ) as desktopBrowser:
        accountPointsCounter = Login(desktopBrowser).login()
        startingPoints = accountPointsCounter
        logging.debug(
            f"[POINTS] You have {desktopBrowser.utils.formatNumber(accountPointsCounter)} points on your account !"
        )
        DailySet(desktopBrowser).completeDailySet()
        PunchCards(desktopBrowser).completePunchCards()
        MorePromotions(desktopBrowser).completeMorePromotions()
        (
            remainingSearches,
            remainingSearchesM,
        ) = desktopBrowser.utils.getRemainingSearches()
        if remainingSearches != 0:
            accountPointsCounter = Searches(desktopBrowser).bingSearches(
                remainingSearches
            )

        if remainingSearchesM != 0:
            desktopBrowser.closeBrowser()
            with Browser(
                mobile=True, account=currentAccount, args=argumentParser()
            ) as mobileBrowser:
                accountPointsCounter = Login(mobileBrowser).login()
                accountPointsCounter = Searches(mobileBrowser).bingSearches(
                    remainingSearchesM
                )

        logging.debug(
            f"[POINTS] You have earned {desktopBrowser.utils.formatNumber(accountPointsCounter - startingPoints)} points today !"
        )
        logging.debug(
            f"[POINTS] You are now at {desktopBrowser.utils.formatNumber(accountPointsCounter)} points !\n"
        )
          
        args = argumentParser()
            
        if args.webhook:
            Discord.send_to_webhook(f'`{currentAccount.get("username", "")}` has farmed {accountPointsCounter - startingPoints} points today. Total points: {accountPointsCounter}')
            
        if args.redeem:
            Redeem.auto_redeem(desktopBrowser, currentAccount.get("username", ""), accountPointsCounter, args.webhook)


if __name__ == "__main__":
    main()
