#!/usr/bin/python3.7

import logging
import os
from datetime import datetime
from time import sleep

import telebot
from telebot.types import Message

import db
import localz


TELEGRAM_API_TOKEN = os.getenv("TELEGRAM_API_TOKEN")


logger = logging.getLogger('TeleBot')
logger.setLevel(logging.ERROR)


ADD_SENDER_COMMAND = localz.ADD_SENDER_COMMAND
ADD_SUBSCRIBER_COMMAND = localz.ADD_SUBSCRIBER_COMMAND
DELETE_SENDER_COMMAND = localz.DELETE_SENDER_COMMAND
DELETE_SUBSCRIBER_COMMAND = localz.DELETE_SUBSCRIBER_COMMAND
GET_SUBSCRIBERS_COMMAND = localz.GET_SUBSCRIBERS_COMMAND
GET_SENDERS_COMMAND = localz.GET_SENDERS_COMMAND


class Bot():
    #: telebot.TeleBot: instance of the bot API.
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
        self.__subscribers = dict()
        self.__senders = dict()
        self.__get_subscribers()
        self.__get_senders()

        super().__init__(token)

    def __add_subscriber(self, message: Message) -> str:
        user_info = message.from_user
        subscriber_id = str(user_info.id)
        if subscriber_id in self.__subscribers:
            return localz.MSG_YOU_ARE_ALREADY_SUBSCRIBER

        self.__subscribers[subscriber_id] = {
            "id": user_info.id,
            "first_name": user_info.first_name,
            "last_name": user_info.last_name,
            "username": user_info.username,
        }

        db.insert_subscriber(
            message = message,
            init_datetime = datetime.utcnow())

        logger.info("Inserted the following subscriber: {}".format(subscriber_id))

        return localz.MSG_YOU_HAVE_BEEN_SUBSCRIBED

    def __delete_subscriber(self, message:Message) -> str:
        subscriber_id = str(message.from_user.id)
        if subscriber_id not in self.__subscribers:
            return localz.MSG_YOU_ARE_ALREADY_NOT_SUBSCRIBER

        self.__subscribers.pop(subscriber_id)
        db.delete_subscriber(id = subscriber_id)

        logger.info("Deleted the following subscriber: {}".format(subscriber_id))

        return localz.MSG_YOU_HAVE_BEEN_UNSUBSCRIBED

    def __get_subscribers(self):
        results = db.fetch_subscribers()
        for result in results:
            id, first_name, last_name, username = result
            self.__subscribers[id] = {
                "id": id,
                "first_name": first_name,
                "last_name": last_name,
                "username": username,
            }

        logger.info("Fetched the following subscribers: {}".format(self.__subscribers))

    def __add_sender(self, message: Message):
        user_info = message.from_user
        sender_id = str(user_info.id)
        if sender_id in self.__senders:
            return localz.MSG_YOU_ARE_ALREADY_SENDER

        self.__senders[sender_id] = {
            "id": user_info.id,
            "first_name": user_info.first_name,
            "last_name": user_info.last_name,
            "username": user_info.username,
        }

        db.insert_sender(
            message = message,
            init_datetime = datetime.utcnow())

        logger.info("Inserted the following sender: {}".format(sender_id))

        return localz.MSG_YOU_HAVE_BEEN_MARKED_AS_SENDER

    def __delete_sender(self, message:Message) -> str:
        sender_id = str(message.from_user.id)
        if sender_id not in self.__senders:
            return localz.MSG_YOU_ARE_ALREADY_NOT_SENDER

        self.__senders.pop(sender_id)
        db.delete_sender(id = sender_id)

        logger.info("Deleted the following sender: {}".format(sender_id))

        return localz.MSG_YOU_HAVE_BEEN_UNMARKED_AS_SENDER

    def __get_senders(self):
        results = db.fetch_senders()
        for result in results:
            id, first_name, last_name, username = result
            self.__senders[id] = {
                "id": id,
                "first_name": first_name,
                "last_name": last_name,
                "username": username,
            }

        logger.info("Fetched the following senders: {}".format(self.__senders))

    def get_message(self, message: Message):
        db.insert_message(message)

        message_text = message.text

        command_map = {
            ADD_SUBSCRIBER_COMMAND: self.__add_subscriber,
            ADD_SENDER_COMMAND: self.__add_sender,
            DELETE_SUBSCRIBER_COMMAND: self.__delete_subscriber,
            DELETE_SENDER_COMMAND: self.__delete_sender,
            GET_SUBSCRIBERS_COMMAND: self.__get_subscribers_command,
            GET_SENDERS_COMMAND: self.__get_senders_command,
        }

        command_handler = command_map.get(message_text, None)
        if command_handler is not None:
            reply_text = command_handler(message)
            self._bot.reply_to(message, reply_text)
            return

        user_id = str(message.from_user.id)
        reply_text = localz.MSG_IGNORE
        if user_id in self.__senders:
            reply_text = self.__process_message_from_sender(message)

        self._bot.reply_to(message, reply_text)

    def __process_message_from_sender(self, message: Message):
        self.__resend_message(message)
        return localz.MSG_FORWARDED

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

    def __get_subscribers_command(self, message: Message):
        cmd_sender_info = message.from_user
        if str(cmd_sender_info.id) not in self.__subscribers:
            return localz.MSG_IGNORE

        results = []
        number = 1
        for user_info in self.__subscribers.values():
            formed_data = '{}. {} {}'.format(
                number,
                user_info['first_name'],
                user_info['last_name'])

            if user_info['username']:
                formed_data += ' (@{})'.format(user_info['username'])

            results.append(formed_data)
            number += 1

        if not results:
            return 'There is no active subscribers'

        return '\n'.join(results)

    def __get_senders_command(self, message: Message):
        cmd_sender_info = message.from_user
        if str(cmd_sender_info.id) not in self.__subscribers:
            return localz.MSG_IGNORE

        results = []
        number = 1
        for user_info in self.__senders.values():
            formed_data = '{}. {} {}'.format(
                number,
                user_info['first_name'],
                user_info['last_name'])

            if user_info['username']:
                formed_data += ' (@{})'.format(user_info['username'])

            results.append(formed_data)
            number += 1

        if not results:
            return 'There is no active senders'

        return '\n'.join(results)


resender = ResenderBot(token = TELEGRAM_API_TOKEN)


while True:
    try:
        resender.get_updates()
    except Exception:
        pass

    sleep(1)
