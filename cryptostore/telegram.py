
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    CallbackContext,
)

from cryptofeed.defines import (
    # GOOD_TIL_CANCELED, L2_BOOK, LIMIT, BUY, SELL, TICKER, TRADES, BALANCES, POSITIONS, ORDER_INFO,
    # ASCENDEX, BEQUANT, BITFINEX, BITHUMB, BITMEX, BINANCE, BINANCE_US, BINANCE_FUTURES, BINANCE_DELIVERY, BITFLYER, BITSTAMP, BITTREX, BLOCKCHAIN,
    # BYBIT, COINBASE, DERIBIT, DYDX, EXX, FTX, FTX_US, FMFW, GATEIO, GEMINI, HITBTC, HUOBI, HUOBI_DM, HUOBI_SWAP, KRAKEN, KRAKEN_FUTURES, KUCOIN,
    # OKCOIN, OKEX, PHEMEX, POLONIEX, PROBIT, UPBIT
    BINANCE_FUTURES, BINANCE_DELIVERY
)

LOG = logging.getLogger('cryptostore')

# Stages
FIRST, SECOND, THIRD = range(3)

class TelegramBot:
    def __init__(self, token, chat_id):
       
        if not token:
            raise ValueError('Must specify token')
        if not chat_id:
            raise ValueError('Must specify chat_id') 

        # self.bot = telegram.Bot(token=token)
        self.updater = Updater(token=token)
        self.chat_id = chat_id

    def send_message(self, text):
        self.updater.bot.sendMessage(chat_id=self.chat_id, text=text)

    def stop(self):
        self.updater.start_polling()
        self.updater.dispatcher.stop()
        self.updater.job_queue.stop()
        self.updater.stop()

    def start(self, interval=0, timeout=10, clean=False,  idle=True):
        self.updater.start_polling(poll_interval=interval, timeout=timeout, drop_pending_updates=clean)
        if idle:
            self.updater.idle()

    def add_command(self, cmd, func, run_async=False):
        self.updater.dispatcher.add_handler(CommandHandler(cmd, func, run_async=run_async))

    # def add_command(self, cmd, func, pass_args=False):
    #     self.updater.dispatcher.add_handler(CommandHandler(cmd,func,pass_args))


class AccountBot(TelegramBot):
    def __init__(self, token, chat_id):
        super().__init__(token, chat_id)

        self.exchanges = []
        self.symbols = []
        self.options = []
        # command_handler(exchange, option, update, context, symbol=None)
        self.command_handler = None

    def add_command(self, exchanges: list, symbols: list, options: list, cmd: str, func, run_async=False):
        # assert isinstance(exchanges, list)
        # assert isinstance(options, list)

        self.exchanges = exchanges 
        self.symbols = symbols
        self.options = options
        self.command_handler = func 

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler(cmd, self.account)],
            states={
                FIRST: [
                    CallbackQueryHandler(self.option),
                ],
                SECOND: [
                    CallbackQueryHandler(self.second_conv_end),
                ],
                THIRD: [
                    CallbackQueryHandler(self.third_conv_end),
                ],
            },
            fallbacks=[CommandHandler('account', self.account)],
            run_async = run_async
        )

        # Add ConversationHandler to dispatcher that will be used for handling updates
        self.updater.dispatcher.add_handler(conv_handler)

    def account(self, update: Update, context: CallbackContext) -> int:
        """Send message on `/start`."""
        # Get user that sent /start and log his name
        # user = update.message.from_user
        # logger.info("User %s started the conversation.", user.first_name)
        # Build InlineKeyboard where each button has a displayed text
        # and a string as callback_data
        # The keyboard is a list of button rows, where each row is in turn
        # a list (hence `[[...]]`).
        if len(self.exchanges) > 0:
            # keyboard = [
            #     [
            #         InlineKeyboardButton("BINANCE_FUTURES", callback_data=BINANCE_FUTURES),
            #         # InlineKeyboardButton("BINANCE_DELIVERY", callback_data=str(TWO)),
            #     ]
            # ]
            keyboard = [[InlineKeyboardButton(exchange, callback_data=exchange)] for exchange in self.exchanges]
            reply_markup = InlineKeyboardMarkup(keyboard)
            # Send message with text and appended InlineKeyboard
            update.message.reply_text("Start query account, Choose a exchange", reply_markup=reply_markup)
            return FIRST
        else:
            update.message.reply_text("No exchange options... See you next time!")
            return ConversationHandler.END

        
    def option(self, update: Update, context: CallbackContext) -> int:
        """Parses the CallbackQuery and updates the message text."""
        query = update.callback_query

        # CallbackQueries need to be answered, even if no notification to the user is needed
        # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
        query.answer()

        exchange = query.data

        if len(self.options) > 0:
            keyboard = [[InlineKeyboardButton(option, callback_data=f"{exchange}.{option}")] for option in self.options]
            reply_markup = InlineKeyboardMarkup(keyboard)
            # Send message with text and appended InlineKeyboard
            query.edit_message_text(f"Selected exchange: {exchange}, Choose a option", reply_markup=reply_markup)
            return SECOND

            # keyboard = [
            #     [
            #         InlineKeyboardButton("balances", callback_data=f"{exchange}.balances"),
            #         InlineKeyboardButton("positions", callback_data=f"{exchange}.positions"),
            #     ],
            #     [
            #         InlineKeyboardButton("orders", callback_data=f"{exchange}.orders"),
            #         InlineKeyboardButton("grids", callback_data=f"{exchange}.grids"),
            #     ]
            # ]
        else:
            query.edit_message_text("No exchange options... See you next time!")
            return ConversationHandler.END

    def second_conv_end(self, update: Update, context: CallbackContext) -> int:
        """Returns `ConversationHandler.END`, which tells the
        ConversationHandler that the conversation is over.
        """
        query = update.callback_query
        query.answer()

        cmds = query.data.split(sep='.')
        exchange = cmds[0]
        option = cmds[1]
        # LOG.info(cmds)

        if option == 'orders':
            if len(self.symbols) > 0:
                keyboard = [[InlineKeyboardButton(symbol, callback_data=f"{exchange}.{symbol}.{option}")] for symbol in self.symbols]
                reply_markup = InlineKeyboardMarkup(keyboard)
                # Send message with text and appended InlineKeyboard
                query.edit_message_text(f"Selected exchange: {exchange}, Choose a symbol of orders", reply_markup=reply_markup)
                return THIRD
            else:
                query.edit_message_text("No symbol for orders... See you next time!")
                return ConversationHandler.END 
        elif option == 'grids':
            if len(self.symbols) > 0:
                keyboard = [[InlineKeyboardButton(symbol, callback_data=f"{exchange}.{symbol}.{option}")] for symbol in self.symbols]
                reply_markup = InlineKeyboardMarkup(keyboard)
                # Send message with text and appended InlineKeyboard
                query.edit_message_text(f"Selected exchange: {exchange}, Choose a symbol of grids", reply_markup=reply_markup)
                return THIRD
            else:
                query.edit_message_text("No symbol for grids... See you next time!")
                return ConversationHandler.END 

        self.command_handler(exchange, option, update, context)

        # query.edit_message_text(text="See you next time!")
        return ConversationHandler.END

    def third_conv_end(self, update: Update, context: CallbackContext) -> int:
        """Returns `ConversationHandler.END`, which tells the
        ConversationHandler that the conversation is over.
        """
        query = update.callback_query
        query.answer()

        cmds = query.data.split(sep='.')
        exchange = cmds[0]
        symbol = cmds[1]
        option = cmds[2]
        # LOG.info(cmds)

        self.command_handler(exchange, option, update, context, symbol)

        # query.edit_message_text(text="See you next time!")
        return ConversationHandler.END