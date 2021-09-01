#!/usr/bin/python3.8

import logging
import os
from datetime import datetime
from time import sleep

import telebot
from telebot.types import Message

import db


TELEGRAM_API_TOKEN = os.getenv("TELEGRAM_API_TOKEN")


logger = logging.getLogger('TeleBot')
logger.setLevel(logging.ERROR)


ADD_SENDER_COMMAND = '/Отчёт_Титан_Отослать'
ADD_SUBSCRIBER_COMMAND = '/Отчёт_Титан_Принять'

DELETE_SENDER_COMMAND = '/Не_Отчёт_Титан_Отослать'
DELETE_SUBSCRIBER_COMMAND = '/Не_Отчёт_Титан_Принять'


class Bot():
    _bot = None

    def __init__(self, token: str):
        self._bot = telebot.TeleBot(token = token, threaded = False)

        # Use custom handler adding instead of decorators.
        self._bot.add_message_handler({
            # Read TeleBot.message_handler docstring for details.
            'function': self.get_message,
            'filters': {
                # content_types: ['audio', 'photo', 'voice', 'video',
                #     'document', 'text', 'location', 'contact', 'sticker']
                'content_types': ['audio', 'photo', 'voice', 'video',
                                  'document', 'text', 'location', 'contact',
                                  'sticker'],
                # commands=['start', 'help']
                'commands': None,
                # regexp='someregexp'
                'regexp': None,
                # if func returns True, the message will be passed to
                # the 'function'
                'func': lambda message: True,
            }
        })

    def get_message(self, message: Message):
        raise NotImplementedError()

    def get_updates(self):
        updates = self._bot.get_updates(
            offset = (self._bot.last_update_id + 1),
            timeout = 1,
            long_polling_timeout = 1
        )

        self._bot.process_new_updates(updates)

class ResenderBot(Bot):
    __subscribers = None
    __senders = None

    def __init__(self, token: str):
        self.__subscribers = set()
        self.__senders = set()
        self.__get_subscribers()
        self.__get_senders()

        super().__init__(token)

    def __add_subscriber(self, message: Message) -> str:
        subscriber_id = str(message.from_user.id)
        if subscriber_id in self.__subscribers:
            return "Вы уже подписаны на рассылку!"

        self.__subscribers.add(subscriber_id)
        db.insert_subscriber(
            id = subscriber_id,
            init_datetime = datetime.utcnow())

        logger.info("Inserted the following subscriber: {}".format(subscriber_id))

        return "Вы были подписал на рассылку! :)"

    def __delete_subscriber(self, message:Message) -> str:
        subscriber_id = str(message.from_user.id)
        if subscriber_id not in self.__subscribers:
            return "Ты уже не подписан на рассылку!"

        self.__subscribers.remove(subscriber_id)
        db.delete_subscriber(id = subscriber_id)

        logger.info("Deleted the following subscriber: {}".format(subscriber_id))

        return "Вы больше не подписаны на рассылку! :)"

    def __get_subscribers(self):
        results = db.fetch_subscribers()
        for result in results:
            self.__subscribers.add(result[0])

        logger.info("Fetched the following subscribers: {}".format(self.__subscribers))

    def __add_sender(self, message: Message):
        sender_id = str(message.from_user.id)
        if sender_id in self.__senders:
            return "Вы уже запомнены. Шлите мне сообщения для пересылки!"

        self.__senders.add(sender_id)
        db.insert_sender(
            id = sender_id,
            init_datetime = datetime.utcnow())

        logger.info("Inserted the following sender: {}".format(sender_id))

        return "Вы запомнены. Шлите мне сообщения для пересылки! :)"

    def __delete_sender(self, message:Message) -> str:
        sender_id = str(message.from_user.id)
        if sender_id not in self.__senders:
            return "Вы уже забыты. Теперь сообщения для пересылки ингорируются!"

        self.__senders.remove(sender_id)
        db.delete_sender(id = sender_id)

        logger.info("Deleted the following sender: {}".format(sender_id))

        return "Вы были забыты. Теперь сообщения для пересылки ингорируются! :)"

    def __get_senders(self):
        results = db.fetch_senders()
        for result in results:
            self.__senders.add(result[0])

        logger.info("Fetched the following subscribers: {}".format(self.__senders))

    def get_message(self, message: Message):
        db.insert_message(message)

        message_text = message.text

        command_map = {
            ADD_SUBSCRIBER_COMMAND: self.__add_subscriber,
            ADD_SENDER_COMMAND: self.__add_sender,
            DELETE_SUBSCRIBER_COMMAND: self.__delete_subscriber,
            DELETE_SENDER_COMMAND: self.__delete_sender,
        }

        command_handler = command_map.get(message_text, None)
        if command_handler is not None:
            reply_text = command_handler(message)
            self._bot.reply_to(message, reply_text)
            return

        user_id = str(message.from_user.id)
        reply_text = 'Мне нечего сказать об этом!'
        if user_id in self.__senders:
            reply_text = self.__process_message_from_sender(message)

        self._bot.reply_to(message, reply_text)

    def __process_message_from_sender(self, message: Message):
        self.__resend_message(message)
        return 'Сообщение передано. Спасибо :)'

    def __resend_message(self, message: Message):
        """Forwards message from the receiver bot to the subscribers.

        Parameters:
            :message (telebot.types.Message): amessage that shall be passed.

        """
        for subscriber_id in self.__subscribers:
            logger.info("Processing the following subscriber: {}".format(
                subscriber_id))

            try:
                self._bot.forward_message(
                    chat_id = subscriber_id,
                    from_chat_id = message.from_user.id,
                    message_id = message.message_id)
            except telebot.apihelper.ApiException:
                pass


resender = ResenderBot(token = TELEGRAM_API_TOKEN)


while True:
    resender.get_updates()
    sleep(1)
