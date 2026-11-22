# Set up a Symphony bot

A Symphony bot is a service account on a pod that signs in with an RSA key. Only a pod administrator can create service accounts, so on a company pod this guide comes down to generating a key pair and handing the public key to your administrator. Your company may have its own process for requesting bots; follow it if so.

## Get a pod

- **A company pod:** ask your pod administrator to create a service account for the bot. Symphony's [Creating a Bot User](https://docs.developers.symphony.com/bots/getting-started/creating-a-bot-user) page lists the steps they follow in the Admin Portal.
- **Symphony's developer sandbox:** if you have no pod to test on, register at the [Symphony Developer Center](https://developers.symphony.com/). The welcome email links to a request for bot credentials on the `develop2.symphony.com` sandbox.

## Generate the key pair

Symphony's [RSA authentication](https://docs.developers.symphony.com/bots/authentication/rsa-authentication) page uses these commands:

```bash
openssl genrsa -out privatekey.pem 4096
openssl rsa -in privatekey.pem -pubout -out publickey.pem
```

Send `publickey.pem` to whoever creates the service account; it goes in the account's **Authentication** field. Keep `privatekey.pem` in your secret store. Symphony's [Generator](https://docs.developers.symphony.com/dev-tools/generator) can create the pair for you as part of a new bot project.

The bot's username in the config must match the service account's username exactly.

## Add the bot to a room

In the Symphony client, open the room's settings and add the bot as a member. A bot only sees messages from rooms it belongs to and from direct chats.

## Connect with Chatom

```bash
pip install chatom symphony-bdk-python
```

```python
from chatom.symphony import SymphonyBackend, SymphonyConfig

backend = SymphonyBackend(
    config=SymphonyConfig(
        host="mycompany.symphony.com",
        bot_username="chatom-bot",
        bot_private_key_path="/path/to/privatekey.pem",
    )
)
```

Pass the key itself with `bot_private_key_content` instead of a path if you load it from a secret store. On a cloud pod the agent and key manager share the pod's host. If yours run elsewhere, set `agent_host`, `key_manager_host`, and `session_auth_host`, along with their ports.

## Check the setup

```bash
export SYMPHONY_HOST=mycompany.symphony.com
export SYMPHONY_BOT_USERNAME=chatom-bot
export SYMPHONY_BOT_PRIVATE_KEY_PATH=/path/to/privatekey.pem
export SYMPHONY_TEST_ROOM_NAME="Chatom Test"

python -m chatom.examples.basic_connection --backend symphony
python -m chatom.examples.send_message --backend symphony
python -m chatom.examples.listen_for_messages --backend symphony --timeout 60
```

`send_message` posts a greeting in the room. While `listen_for_messages` runs, send `!ping`, `!help`, or `!dm` in the room and the bot answers.
