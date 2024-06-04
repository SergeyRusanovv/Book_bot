import os
from dataclasses import dataclass
from dotenv import load_dotenv


load_dotenv()
TOKEN = os.environ.get("TOKEN")
ADMIN_IDS = os.environ.get("ADMIN_IDS")


@dataclass
class TgBot:
    token: str
    admin_ids: int


@dataclass
class Config:
    tg_bot: TgBot


def load_config() -> Config:
    return Config(
        tg_bot=TgBot(
            token=TOKEN,
            admin_ids=int(ADMIN_IDS)
        )
    )
