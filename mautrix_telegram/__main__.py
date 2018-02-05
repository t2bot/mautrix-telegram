# -*- coding: future_fstrings -*-
# mautrix-telegram - A Matrix-Telegram puppeting bridge
# Copyright (C) 2018 Tulir Asokan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import argparse
import sys
import logging

import sqlalchemy as sql
from sqlalchemy import orm

from mautrix_appservice import AppService

from .base import Base
from .config import Config
from .matrix import MatrixHandler

from .db import init as init_db
from .user import init as init_user
from .portal import init as init_portal
from .puppet import init as init_puppet
from .formatter import init as init_formatter

log = logging.getLogger("mau")
time_formatter = logging.Formatter("[%(asctime)s] [%(levelname)s@%(name)s] %(message)s")
handler = logging.StreamHandler()
handler.setFormatter(time_formatter)
log.addHandler(handler)

parser = argparse.ArgumentParser(
    description="A Matrix-Telegram puppeting bridge.",
    prog="python -m mautrix-telegram")
parser.add_argument("-c", "--config", type=str, default="config.yaml",
                    metavar="<path>", help="the path to your config file")
parser.add_argument("-g", "--generate-registration", action="store_true",
                    help="generate registration and quit")
parser.add_argument("-r", "--registration", type=str, default="registration.yaml",
                    metavar="<path>", help="the path to save the generated registration to")
args = parser.parse_args()

config = Config(args.config, args.registration)
config.load()

if args.generate_registration:
    config.generate_registration()
    config.save()
    print(f"Registration generated and saved to {config.registration_path}")
    sys.exit(0)

if config["appservice.debug"]:
    telethon_log = logging.getLogger("telethon")
    telethon_log.addHandler(handler)
    telethon_log.setLevel(logging.DEBUG)
    log.setLevel(logging.DEBUG)
    log.debug("Debug messages enabled.")

db_engine = sql.create_engine(config.get("appservice.database", "sqlite:///mautrix-telegram.db"))
db_factory = orm.sessionmaker(bind=db_engine)
db_session = orm.scoping.scoped_session(db_factory)
Base.metadata.bind = db_engine
Base.metadata.create_all()

appserv = AppService(config["homeserver.address"], config["homeserver.domain"],
                     config["appservice.as_token"], config["appservice.hs_token"],
                     config["appservice.bot_username"], log=log.getChild("as"))
context = (appserv, db_session, log, config)

with appserv.run(config["appservice.hostname"], config["appservice.port"]) as start:
    init_db(db_session)
    init_formatter(context)
    init_portal(context)
    init_puppet(context)
    init_user(context)
    MatrixHandler(context)
    start()