# Set up an IRC bot

IRC has no bot accounts or tokens: a bot is a client with a nickname. This guide registers that nickname on [Libera.Chat](https://libera.chat/) so nobody else can take it, and checks the connection with Chatom's examples. Other networks work the same way, though their services commands may differ.

## Register the nickname

Connect with any IRC client, switch to the bot's nickname, and register it with NickServ. Libera.Chat's [registration guide](https://libera.chat/guides/registration) asks for a separate account for each bot.

```text
/nick chatom-bot
/msg NickServ REGISTER <password> <email>
```

NickServ emails a verification command; run it within about 24 hours or the account is dropped. Keep the password in your secret store.

## Follow the network's bot rules

Libera.Chat's [policies](https://libera.chat/policies/) require a bot to be labeled as a bot and traceable to someone who runs it, which the realname can do. A bot may only join a channel with permission from the channel's operators, or after being invited. Ask the operators to voice the bot, which exempts it from some spam limits.

## Connect with Chatom

Chatom needs no extra packages for IRC:

```bash
pip install chatom
```

```python
import os

from chatom.irc import IRCBackend, IRCConfig

backend = IRCBackend(
    config=IRCConfig(
        server="irc.libera.chat",
        nickname="chatom-bot",
        realname="chatom bot run by <your nick>",
        password=f"chatom-bot:{os.environ['IRC_NICKSERV_PASSWORD']}",
        channels=["#chatom-test"],
    )
)
```

The backend connects with TLS on port 6697 by default and joins `channels` once it is registered with the server. It sends `password` as the server password. Libera.Chat accepts `<account>:<password>` there and logs the bot in to its NickServ account as it connects.

History depends on the server: `fetch_messages` only works on servers that offer the IRCv3 `chathistory` capability.

## Check the setup

```bash
export IRC_SERVER=irc.libera.chat
export IRC_NICKNAME=chatom-bot
export IRC_PASSWORD="chatom-bot:<password>"
export IRC_TEST_CHANNEL="#chatom-test"
export IRC_TEST_USER_NICK=<your nick>

python -m chatom.examples.basic_connection --backend irc
python -m chatom.examples.send_message --backend irc
python -m chatom.examples.listen_for_messages --backend irc --timeout 60
```

`send_message` posts a greeting in the channel. While `listen_for_messages` runs, send `!ping`, `!help`, or `!dm` in the channel and the bot answers; `!dm` arrives as a private message.
