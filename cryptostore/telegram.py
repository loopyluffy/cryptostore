
import telegram
from telegram.ext import Updater, CommandHandler

class TelegramBot:
    def __init__(self, token, chat_id):
       
        if not token:
            raise ValueError('Must specify token')
        if not chat_id:
            raise ValueError('Must specify chat_id') 

        # self.bot = telegram.Bot(token=token)
        self.updater = Updater(token=token)
        self.chat_id = chat_id

    def sendMessage(self, text):
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