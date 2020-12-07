from typing import Optional, Type

from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper
from maubot import Plugin, MessageEvent
from maubot.handlers import command

import requests
import json

class Config(BaseProxyConfig):
    def do_update(self, helper: ConfigUpdateHelper) -> None:
        helper.copy("apiKey")
        helper.copy("stocktrigger")
        helper.copy("cryptotrigger")

class TickerBot(Plugin):
    async def start(self) -> None:
        await super().start()
        self.config.load_and_update()

    @classmethod
    def get_config_class(cls) -> Type[BaseProxyConfig]:
        return Config

    @command.new(name=lambda self: self.config["stocktrigger"],
            help="Look up information about a stock by its ticker symbol")
    @command.argument("ticker", pass_raw=True, required=True)
    async def handler(self, evt: MessageEvent, ticker: str) -> None:
        await evt.mark_read()

        tickerUpper = ticker.upper()
        url = "https://apidojo-yahoo-finance-v1.p.rapidapi.com/market/v2/get-quotes"
        querystring = {"symbols":tickerUpper}
        headers = {
            'x-rapidapi-key': self.config["apiKey"],
            'x-rapidapi-host': "apidojo-yahoo-finance-v1.p.rapidapi.com"
            }
        
        try:
            response = requests.request("GET", url, headers=headers, params=querystring)
        except Exception as e:
            await evt.respond(f"request failed: {e.message}")
            return None
        try:
            jsonresponse = response.json()['quoteResponse']['result'][0]
            openDifference = f"{jsonresponse['regularMarketPrice'] - jsonresponse['regularMarketOpen']:.2f}"
            openPercentDiff = f"{(float(openDifference) / jsonresponse['regularMarketOpen'] * 100):.2f}%"
        except Exception as e:
            await evt.respond("No results, double check that you've chosen a real ticker symbol")
            self.log.exception(e)
            return None
        
        if float(openDifference) < 0:
            color = "red"
            arrow = "\U000025BC"
        else:
            color = "green"
            arrow = "\U000025B2"

        prettyMessage = "<br />".join(
                [
                    f"<b>Current data for <a href=\"https://finance.yahoo.com/quote/{tickerUpper}\">\
                            {jsonresponse['longName']}</a> ({tickerUpper}):</b>" ,
                    f"",
                    f"<b>Price:</b> <font color=\"{color}\">${str(jsonresponse['regularMarketPrice'])}, \
                            {arrow}{openPercentDiff}</font> from market open @ ${str(jsonresponse['regularMarketOpen'])}",
                    f"<b>52 Week High:</b> ${str(jsonresponse['fiftyTwoWeekHigh'])}",
                    f"<b>52 Week Low:</b> ${str(jsonresponse['fiftyTwoWeekLow'])}"
                ]
            )
        
        await evt.respond(prettyMessage, allow_html=True)
