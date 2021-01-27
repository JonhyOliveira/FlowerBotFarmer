from typing import Union, Callable, TypeVar

import requests
import time, datetime
import logging
import parse

log = logging.getLogger(__name__)

__version__ = 'beta 0.1'

_wait_message_parser = parse.Parser("You need to wait another {val} to {}")
_exp_message_parser = parse.Parser("{}**{val}**{}")
_plant_info_message_parser = \
    parse.Parser("**{type}**{}level {level}/{max_level}.{}**{death_timer}**{}**{alive_time}**{}")


class Plant:

    def __init__(self, name: str, plant_type: str, level: int, max_level: int, death_timer: str, alive_time: str):
        self.name = name
        self.type = plant_type
        self.level = level
        self.max_level = max_level
        self.death_timer = _parse_time_message(death_timer)
        self.alive_time = _parse_time_message(alive_time)

    def __repr__(self):
        return f"Plant[name={self.name}, type={self.type}, level={self.level}/{self.max_level}]"


def _parse_time_message(message: str) -> time.struct_time:
    # print("|", message, "|")

    parseFormat = ""

    if "days" in message:
        parseFormat += "{day} days"
    if "hours" in message:
        parseFormat += " {hour} hours"
    if "minutes" in message:
        parseFormat += " {minute} minutes"
    if "seconds" in message:
        parseFormat += " {second} seconds"

    # print("|", parseFormat, "|")

    p = parse.parse(parseFormat, message)

    return datetime.datetime(1990, 1, day=int(p["day"]), hour=int(p["hour"]), minute=int(p["minute"]),
                             second=int(p["second"]))


def _parse_wait_message(message: dict) -> \
        Union[tuple[bool, Union[time.struct_time, time.struct_time]], tuple[bool, None]]:
    """
    Parses the wait message from the bot feedback

    :param message: message to parse
    :return: parsed wait time
    """

    if message.get("embeds"):
        return True, None

    if message.get("content"):  # too soon (get cooldown from bot feedback and wait)
        p = _wait_message_parser.parse(message["content"])
        m: str = p["val"]

        if len(m.split(" ")) > 1:
            t = time.strptime(m, "%Mm %Ss")
        else:
            t = time.strptime(m, "%Ss" if "s" in m else "%Mm")

        return False, t

    log.error(f"Unexpected call on _parse_wait_message, message: {message}")
    return False, None


def _parse_exp_message(message: dict) -> Union[int, None]:
    return int(_exp_message_parser.parse(message["embeds"][0]["description"])["val"])


def _parse_shop_message(message: dict) -> Union[dict, None]:
    fields = message.get("embeds")[0].get("fields")

    s_plants: dict = fields[0]
    s_items: dict = fields[1]

    s_plants: list[str] = s_plants.get("value").split("\n")[:-1]
    s_items: list[str] = s_items.get("value").split("\n")

    shop_items = s_plants.copy()
    shop_items.extend(s_items)

    shop = {}

    for item in shop_items:
        item = item.replace('~', '', -1)
        item = item.replace('`', '', -1)
        item = item.split(" - ")

        shop.update({item[0]: item[1]})

    return shop


def _parse_plants_message(message: dict) -> list[Plant]:

    u_plants: list[dict[str, str]] = message.get("embeds")[0].get("fields")

    _plants = []

    for u_plant in u_plants:
        name = u_plant.get("name")
        info = _plant_info_message_parser.parse(u_plant.get("value"))
        _plants.append(Plant(name, info["type"], info["level"], info["max_level"], info["death_timer"], info["alive_time"]))

    return _plants


class Flower:
    DISCORD_API_VERSION = 8
    ENDPOINT = f"https://discord.com/api/v{DISCORD_API_VERSION}"
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) " \
                 "Chrome/87.0.4280.141 Safari/537.36 "

    def __init__(self, user_token, channel):
        """
        API for interactions with the FlowerBot
        :param user_token: the token of the user interacting with the bot
        :param channel: the channel the bot is on
        """
        self.user_token = user_token
        self.channel = channel

    def water_plant(self, plant_name) -> \
            Union[tuple[bool, Union[time.struct_time, time.struct_time]], tuple[bool, None]]:
        """
        Waters a plant
        :param plant_name: the name of the plant to water
        :return: tuple with first argument indicating if the command was successful, if unsuccessful second argument
        indicates the command remaining cooldown
        """
        return self._issue_command_get_feedback(f"p.water {plant_name}", _parse_wait_message)

    def get_exp(self) -> Union[int, None]:
        """
        :return: the current exp
        """
        return self._issue_command_get_feedback("p.exp", _parse_exp_message)

    def get_shop(self) -> Union[dict[str, int], None]:
        """
        :return: dictionary representing the available plants on the shop and their prices
        """
        return self._issue_command_get_feedback("p.shop", _parse_shop_message)

    def get_plants(self) -> Union[tuple[Plant], None]:
        """
        :return: a list of the user plants
        """
        return self._issue_command_get_feedback("p.plants", _parse_plants_message)

    def _issue_command_get_feedback(self, command: str, feedback_parser: Callable[[dict], None]) -> Union:

        message_id = self._issue_command(command)

        time.sleep(.5)  # wait for bot feedback

        return self._get_feedback(message_id, feedback_parser)

    def _issue_command(self, command: str) -> int:
        """
        Issues a command
        :param command: the command to issue
        :return: the message id related to the issued command
        """

        message_content = {
            "content": f"{command}",
            "tts": False
        }

        # sends water plant message
        send_r = requests.post(f"{self.ENDPOINT}/channels/{self.channel}/messages",
                               headers=self._build_discord_header_data(), json=message_content)

        return send_r.json()["id"]  # command message id

    def _get_feedback(self, message_id: int, feedback_parser: Callable[[dict], None]) -> Union[tuple, dict, None]:

        # get messages after the message (should include bot feedback message)
        get_messages_r = requests.get(f"{self.ENDPOINT}/channels/{self.channel}/messages",
                                      headers=self._build_discord_header_data(), params={"after": message_id})

        messages = get_messages_r.json()

        # iterate through messages
        for message in messages:
            if message["author"]["username"] == "Flower":  # bot feedback message
                return feedback_parser(message)  # pass the message to the feedback parser

        return None

    def _build_discord_header_data(self):
        """
        :return: header data for requests to the discord api
        """
        return {
            "content-type": "application/json",
            "user-agent": self.USER_AGENT,
            "authorization": self.user_token,
            "origin": "discord.com"
        }

