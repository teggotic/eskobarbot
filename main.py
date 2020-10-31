import os
import sys
import asyncio
import json
import random

import twitchio


import databases
import orm
import sqlalchemy

# import edgedb
from time import time
from math import ceil

from os.path import join, dirname
from twitchio.ext import commands
from dotenv import load_dotenv

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

database = databases.Database("sqlite:///db.sqlite")
metadata = sqlalchemy.MetaData()


class User(orm.Model):
    __tablename__ = "notes"
    __database__ = database
    __metadata__ = metadata

    id = orm.Integer(primary_key=True)
    iq = orm.Integer()
    name = orm.String(max_length=255)


# Create the database
engine = sqlalchemy.create_engine(str(database.url))
metadata.create_all(engine)

bot_commands = (
    '!icq',
    '!клоун',
    '!команды',
    '!зайка',
    '!зайчик',
    '!солнышко',
    '!тяночка',
    '!ежик',
    '!лох',
    '!пес',
    '!дурачок',
    '!рублик',
    '!рыбка',
    '!эзериал',
)

BLOCKED_SYMBOLS = set('⠭◐⢉⠄⡾▌⠸⡄▐⡀⠑⣾⠲⠙⠁⣈⠾⢚⠿⣸⠹⠇⠘⡹⠴⠀⡻⠷⣉⣌⣮⣴⡇⡈⢹⣿⠋▒█⠈⠃⣰░⡆⡏'
                      '⠉⣜▀⡿⣭⢦⡴⣹⢿⣦⠻⠔⡟⠠⣶⠏⣀⣤⣏⢰⡞⣗⣠⢻⣥⠦⠤⣼⢀▄⣽⢴⢄⢂⠛⣷⠟⢠⢤⣩⣆⣄⠂⣧⡉⢸⣁⣇')

BAN_BOTS_SYMBOLS = set('𝙇𝕀𝘮𝙩𝕞𝕣𝘗𝘦𝙝𝙋𝕘𝙗𝕓𝕙𝘅𝐨𝕤𝐰𝐚𝘤𝐦𝘐𝘁𝗝𝙜𝕩𝙤𝗯𝐞𝙣𝗼𝘓𝗩𝗵𝙃𝕁𝐭𝗟𝗰𝘩𝙄𝐤ℍ𝕋𝟬𝕔ℙ𝘰𝘣𝘯𝙨𝙑𝗛'
                       '𝗣𝘢𝟔𝗴𝕜𝕂𝕠𝙧𝘬𝟘𝙢𝗿𝐥𝗧𝘝𝘆𝐠𝘸𝙠𝘏𝗺𝕟𝙅𝟓𝟑𝐇𝘳𝟎𝕍𝐬𝘄𝘵𝘺'
                       '𝙆𝘹𝟒𝕃𝘀𝟏𝙬𝟐𝗞𝘛𝗸𝙮𝘑𝘒𝕨𝗜𝕥𝘨𝕪𝗻𝘴𝙏𝙭𝚐𝚒𝚕𝚛𝚜𝟺𝟻𝟼')

COOLDOWN = 10

COMMADS_COOLDOWN = 60

ROULETTE_TIMEOUT = 60 * 4
ROULETTE_REQUEST_COOLDOWN = 20 * 1
ROULETTE_ACCEPT_COOLDOWN = 60 * 1

QUESTION_COOLDOWN = 10

REPLY_COOLDOWN = 30

PASTA_COOLDOWN = 30

CHAT_MESSAGES_TIMEOUT = 20

project_id, session_id, language_code = 'teggotbot', 'me', 'ru'


class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            irc_token=os.environ['TMI_TOKEN'],
            api_token=os.environ.get('API_TOKEN'),
            client_id=os.environ['CLIENT_ID'],
            nick=os.environ['BOT_NICK'],
            prefix=os.environ['BOT_PREFIX'],
            initial_channels=[os.environ['CHANNEL']],
        )

        self.roulette_requests = {}

        self.last_command_time = 0
        self.last_roulette_request_time = 0
        self.last_roulette_accept_time = 0
        self.last_reply_time = 0
        self.last_commands_command_time = 0
        self.last_question_command = 0

        self.last_pasta_message = 0

        self.REPLY_COOLDOWN = REPLY_COOLDOWN

        self.CHAT_MESSAGES = {}

    def run(self):
        loop = self.loop or asyncio.get_event_loop()

        loop.run_until_complete(self._ws._connect())

        try:
            loop.run_until_complete(self._ws._listen())
        except KeyboardInterrupt:
            pass
        finally:
            self._ws.teardown()

    async def event_ready(self):
        print(f'Starting | {self.nick}')
        await self.pubsub_subscribe(os.environ['OAUTH_TOKEN'],
                                    'channel-points-channel-v1.140883424')
        print(f'Ready | {self.nick}')

    def _get_context(self, channel, author):
        return twitchio.Context(message=twitchio.Message(),
                                channel=channel,
                                user=author)

    async def event_raw_pubsub(self, data):
        try:
            if data['type'] == 'MESSAGE':
                print(data)
                message = json.loads(data['data']['message'])
                if message['type'] == 'reward-redeemed':
                    redemption = message['data']['redemption']
                    user_name = redemption['user']['login'].lower()

                    reward = redemption['reward']

                    if reward['title'] == '10iq':
                        user = await self.get_or_create_user(user_name)
                        await user.update(iq=user.iq + 10)
                    elif reward['title'] == 'Забанить кого-то на 10мин.':

                        user_input = redemption['user_input'].strip()
                        if user_input[0] == '@':
                            user_input = user_input[1:]

                        author = (await self.get_users(user_name))[0]

                        ctx = self._get_context(
                            self.get_channel(self.initial_channels[0]), author)

                        await ctx.timeout(user_input, 600, 'за очки')

        except json.decoder.JSONDecodeError:
            pass

    async def event_message(self, message):
        print(message.author.name, message.content)
        good = await self.moderate_message(message)

        if good:
            if message.content.startswith(bot_commands):
                await self.handle_commands(message)

            else:
                await self.try_reply(message)

    async def try_reply(self, message: twitchio.Message):
        # if len(message.content) > 30:
        message_set = set(message.content.strip().split())
        if len(message_set) == 1:
            if time() - self.last_reply_time > REPLY_COOLDOWN:
                if message.content.strip().lower() == 'грайм':
                    await message.channel.send('ГРИМЕЧКИ peepoPog')

                    return
                if 'PogChamp' in message_set:
                    await message.channel.send(' '.join(
                        'PogChamp' for x in range(random.randint(3, 5))))

                    self.last_reply_time = time()

                    return

                if 'Pog' in message_set:
                    await message.channel.send(' '.join(
                        'Pog' for x in range(random.randint(3, 5))))

                    self.last_reply_time = time()

                    return

    async def append_banned_text(msg):
        with open('t.txt', 'a') as f:
            f.write(msg + '\n')

    async def moderate_message(self, message: twitchio.Message):
        # TODO ADD VIPS CHECK
        message_set = set(message.content)
        if len(message_set.intersection(BLOCKED_SYMBOLS)):
            await message.channel.timeout(message.author.name,
                                          reason='Спам картинок')
            return False

        if len(message_set.intersection(BAN_BOTS_SYMBOLS)) and \
                len(message.content.split(' ')) > 2:
            await message.channel.ban(message.author.name, reason='БОТ')

            asyncio.create_task(self.append_banned_text(message.content))

            return False

        if message.author.name.lower() == 'grimeochki':
            if '[' in message.content or ']' in message.content:
                await message.channel.timeout(message.author.name, 60,
                                              'grimeochki скобка')
                return False

        return True

    @commands.command(name='принять')
    async def accept_roulette_command(self, ctx: twitchio.Context):
        author_name = ctx.author.name
        words = ctx.message.content.strip().lower().split(' ')[1:]
        if len(words) == 1:
            requestor_name = words[0]

            if requestor_name[0] == '@':
                requestor_name = requestor_name[1:]

            if self.roulette_requests.get(
                    requestor_name.lower()) == author_name.lower():
                if time(
                ) - self.last_roulette_accept_time < ROULETTE_ACCEPT_COOLDOWN:
                    time_left = max(
                        0, ROULETTE_ACCEPT_COOLDOWN -
                        ceil(time() - self.last_roulette_accept_time))
                    await ctx.send(f'кд еще {time_left} сек')
                else:
                    self.last_roulette_accept_time = time()

                del self.roulette_requests[requestor_name]

                await self.start_roulette_fight(ctx, requestor_name,
                                                author_name)

    async def start_roulette_fight(self, ctx, requestor_name, author_name):
        count = random.randint(1, 6)
        round = 1

        msg = f'@{author_name} принимает вызов {requestor_name}. '
        while True:
            killed_req = random.randint(1, 7) <= count
            killed_acc = random.randint(1, 7) <= count

            msg = (f'Уже {round}й круг. {self.nick} Заряжает по {count}'
                   f' {self.pluralize(count)} в револьверы. Игроки'
                   f' крутят барабан, нажимают на курок')

            if killed_acc or killed_req:
                kills = killed_acc + killed_req
                msg += (
                    f', происходит {kills} {self.pluralize(kills, "выстрел")}')

                if kills == 2:
                    msg += ' и оба умерли'
                else:
                    if killed_acc:
                        msg += f' и умер {author_name}, победает' \
                                f' {requestor_name}'
                    if killed_req:
                        msg += f' и умер {requestor_name}, побеждает' \
                                f' {author_name}'

                await ctx.send(msg)

                if killed_acc:
                    await ctx.timeout(author_name, 60, 'застрелен')
                if killed_req:
                    await ctx.timeout(requestor_name, 60, 'застрелен')

                return

            msg += ' и никто не умер. '

            round += 1

    def pluralize(self, count, word='патрон'):
        if count == 1:
            return word
        elif 2 <= count <= 4:
            return word + 'a'
        else:
            return word + 'ов'

    @commands.command(name='клоун')
    async def clown_command(self, ctx: twitchio.Context):
        if time() - self.last_command_time > COOLDOWN:
            self.last_command_time = time()

            await ctx.send('@kevsen_o')

    @commands.command(name='солнышко')
    async def solnishko_command(self, ctx: twitchio.Context):
        if time() - self.last_command_time > COOLDOWN:
            self.last_command_time = time()

            await ctx.send('@ojiubeptbuct')

    @commands.command(name='эзериал')
    async def etherial_command(self, ctx: twitchio.Context):
        if time() - self.last_command_time > COOLDOWN:
            self.last_command_time = time()

            await ctx.send(
                f'@{ctx.author.name}, Эзериал стоит как второй даго'
                'н, но наносит больше урона и позволяет очень легко кайтить'
                ' врагов')

    @commands.command(name='ежик')
    async def yozhik_command(self, ctx: twitchio.Context):
        if time() - self.last_command_time > COOLDOWN:
            self.last_command_time = time()

            await ctx.send('@y0zzz1k')

    @commands.command(name='зайка')
    async def zayka_command(self, ctx: twitchio.Context):
        if time() - self.last_command_time > COOLDOWN:
            self.last_command_time = time()

            await ctx.send('@neitro_O')

    @commands.command(name='рублик')
    async def rublik_command(self, ctx: twitchio.Context):
        if time() - self.last_command_time > COOLDOWN:
            self.last_command_time = time()

            await ctx.send('@rubilinks')

    @commands.command(name='дурачок')
    async def durachek_command(self, ctx: twitchio.Context):
        if time() - self.last_command_time > COOLDOWN:
            self.last_command_time = time()

            await ctx.send('@exTECHu')

    @commands.command(name='тяночка')
    async def tyanochka_command(self, ctx: twitchio.Context):
        if time() - self.last_command_time > COOLDOWN:
            self.last_command_time = time()

            await ctx.send('@s1ndere11a')

    @commands.command(name='зайчик')
    async def zaychik_command(self, ctx: twitchio.Context):
        if time() - self.last_command_time > COOLDOWN:
            self.last_command_time = time()

            await ctx.send('@Ellenwoodd')

    @commands.command(name='пес')
    async def pes_command(self, ctx: twitchio.Context):
        if time() - self.last_command_time > COOLDOWN:
            self.last_command_time = time()

            await ctx.send('@Ellenwoodd')

    @commands.command(name='рыбка')
    async def ribka_command(self, ctx: twitchio.Context):
        if time() - self.last_command_time > COOLDOWN:
            self.last_command_time = time()

            await ctx.send('@ribka_moya')

    @commands.command(name='команды')
    async def commands_command(self, ctx: twitchio.Context):
        if time() - self.last_commands_command_time > COMMADS_COOLDOWN:
            self.last_commands_command_time = time()

            await ctx.send('Команды бота: ' + ', '.join(sorted(bot_commands)))

    @commands.command(name='рулетка')
    async def roulette_command(self, ctx: twitchio.Context):
        author_name = ctx.author.name
        count = random.randint(1, 6)
        words = ctx.message.content.strip().lower().split(' ')[1:]
        if len(words) == 1:
            try:
                count = int(words[0])
                if not (1 <= count <= 6):
                    return
            except ValueError:
                user_name = words[0]

                if user_name[0] == '@':
                    user_name = user_name[1:]

                if user_name.lower() == author_name.lower():
                    return

                if user_name.lower() == 'eskobartv':
                    return

                user = await self.find_user(user_name.lower())

                if user is None:
                    chatters = await self.get_chatters('eskobartv')
                    all_chatters = chatters.all
                    if user_name.lower() in all_chatters:
                        user = await self.create_user(user_name)

                if user:
                    request = self.roulette_requests.get(author_name.lower())

                    is_cd = (time() - self.last_roulette_request_time
                             ) < ROULETTE_REQUEST_COOLDOWN

                    if request is None and not is_cd:
                        self.last_command_time = time()
                        self.last_roulette_request_time = time()
                        msg = (f'@{author_name} приглашает {user_name}'
                               f' сыграть в рулетку. напиши'
                               f' "!принять {author_name}"')

                        self.roulette_requests[author_name.lower()] = user_name

                        await ctx.send(msg)

                        await asyncio.sleep(ROULETTE_TIMEOUT)

                        req = self.roulette_requests.get(author_name.lower())

                        if req is not None:
                            del self.roulette_requests[author_name.lower()]
                    else:
                        if is_cd:
                            time_left = max(
                                0, ROULETTE_REQUEST_COOLDOWN -
                                ceil(time() - self.last_roulette_request_time))
                            await ctx.send(f'кд еще {time_left} сек')

                return

        if time() - self.last_command_time > COOLDOWN:
            self.last_command_time = time()

            bullet_text = self.pluralize(count)

            msg = (f'@{author_name} заряжает {count}'
                   f' {bullet_text}'
                   ' в револьвер и закручивает барабан')
            killed = random.randint(1, 7) <= count

            msg = f'@{author_name} нажимает на курок'
            if killed:
                msg += ' и получает пулю в голову. Отдохни немного'
            else:
                msg += ', слышет щелчок и успешно выживает'

            await ctx.send(msg)

            if killed:
                await ctx.timeout(author_name, 60, 'Застрелился')
        else:
            time_left = max(0,
                            COOLDOWN - ceil(time() - self.last_command_time))
            await ctx.send(f'кд еще {time_left} сек')

    @commands.command(name='icq')
    async def icq_command(self, ctx: twitchio.Context):
        if time() - self.last_command_time > COOLDOWN:
            self.last_command_time = time()

            words = ctx.message.content.strip().split(' ')
            if len(words) >= 2:
                user_name = words[1]
                if user_name[0] == '@':
                    user_name = user_name[1:]

                author = await self.find_user(ctx.author.name.lower())
                user = await self.find_user(user_name)

                if user is None:
                    chatters = await self.get_chatters('eskobartv')
                    all_chatters = chatters.all
                    if user_name.lower() in all_chatters:
                        user = await self.create_user(user_name)

                if user:
                    iq = user.iq
                else:
                    user_name = ' '.join(words[1:])
                    iq = random.randint(1, 200)

                await ctx.send(f'@{ctx.author.name}, у {user_name} ' +
                               f'{iq} icq' +
                               (', даже больше чем у тебя'
                                if author and author.iq < iq else ''))
            else:
                user_name = ctx.author.name
                user = await self.get_or_create_user(user_name)

                await ctx.send(f'@{user_name}, Твой icq: {user.iq}')
        else:
            time_left = max(0,
                            COOLDOWN - ceil(time() - self.last_command_time))
            await ctx.send(f'кд еще {time_left} сек')

    async def get_or_create_user(self, user_name, **kwargs):
        user = await self.find_user(user_name, **kwargs)

        user = user or await self.create_user(user_name, **kwargs)

        return user

    async def find_user(self, user_name, **kwargs):
        user_name = user_name.lower()

        # user_query = await self._conn.query(
        #     '''
        #     SELECT User {id, iq, name, twitch_id}
        #     Filter .name = <str>$name
        #     LIMIT 1;
        #     ''',
        #     name=user_name
        # )
        user_query = await User.objects.filter(name=user_name).all()
        if len(user_query):
            return user_query[0]

        return None

    async def create_user(self, user_name, iq=None):
        user_name = user_name.lower()

        chance = random.random()
        if not iq:
            if chance >= 0.8:
                iq = random.randint(100, 110)
            elif chance <= 0.2:
                iq = random.randint(60, 70)
            else:
                iq = random.randint(70, 100)

        user = await User.objects.create(
            name=user_name,
            iq=iq,
        )
        # user = await self._conn.query_one(
        #     '''
        #     SELECT (
        #         INSERT
        #             User {
        #                 name := <str>$name,
        #                 iq := <int64>$iq,
        #                 twitch_id := <int64>$twitch_id
        #             }
        #             UNLESS CONFLICT ON .name
        #             ELSE (
        #                 SELECT User Filter User.name = <str>$name
        #             )
        #     ) {id, iq, name, twitch_id}
        #     ''',
        #     name=user_name.lower(),
        #     iq=iq,
        #     twitch_id=twitch_id,
        # )
        return user


def start_bot():
    bot = Bot()
    bot.run()


async def db():
    user = await User.objects.filter(name='eskobartv').all()
    user = user[0]
    await user.update(iq=1)


if __name__ == '__main__':
    try:
        if sys.argv[1] == 'bot':
            start_bot()
        elif sys.argv[1] == 'db':
            asyncio.run(db())
    except IndexError:
        start_bot()
