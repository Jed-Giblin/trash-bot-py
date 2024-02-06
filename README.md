
# Trashbot (Now in Python via python-telegram-bot)

This is the repo for the #trashbot that integrates with quite a few services to make dumb things more fun. 

The currently supported feature set:
- Interact with Sonarr to manage TV Show collections
- Interact with Radarr to manage Movie collections
- Interact with Readarr to manage ebook & audiobook collections





## How does it work

Telegram has an API to fetch/send messages. The bot, running out of `main.py` sets up a listener that constantly checks the API for new messages. This includes messages in any group/super chats its in, as well as direct messages. 

Inside the bot are a set of modules. Each module is currently one of 2 types: 

### Command driven modules

Command drive modules are called when a user executs a cert `/<command>` and the bot sees the message. Commands execute a single handler and then usually send data back to the user

### Conversational modules

Conversational modules are designed like Wizards (not the magic missle kind). The wizard has an initial state which is invoked with a command, and it then defines a set of states it can transition into based on the messages it receives. 



## Exiting Modules

### Trash

This module is a meme. It will listen in chat for a set of words, configured by the user(s). Once it sees those words in chat, it will respond with either Trash! or, if enabled, memes of Danny Devito


### Oncall

This is a premium only module designed to track and parse the oncall status that we are forced into by the overlords.

Type: Conversation & Command

Author: Jed Giblin


### SonarrManager

This modules is used to interact with Sonarr to manage TV Shows

Type: Conversation

Author: Jed Giblin


### RadarrManager

This module is used to interact with Radarr to manage movies.

Type: Conversation

Author: Jed Giblin


### ReadarrManager

This module is used to interact with Readarr to manage books.

Type: Conversation

Author: Cole Aten


### SetupManager

This module is used to configure other modules & record some user data

Type: Conversation & Command

Author: Jed Giblin

### PollManager

This module is used to schedule polls on a configurable basis

Type: Conversation

Author: David Hoy





## Data & Architecture

