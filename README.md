
# Trashbot (Now in Python via python-telegram-bot)

This is the repo for the #trashbot that integrates with quite a few services to make dumb things more fun. 

The currently supported feature set:
- Interact with Sonarr to manage TV Show collections
- Interact with Radarr to manage Movie collections
- Interact with Readarr to manage ebook & audiobook collections





## Installation

You can install the required packages with:

`pip install -r requirements.txt`

You may need some additional system / OS packages though. 

## Local Development

On Telegram, message the BotFather (@BotFather) (Should be searchable and verified)

Message him `/newbot` and follow his instructions

Eventually, you will get a bot token.

Put that token in a `.env` file
``````
TOKEN=your_token_goes_here
``````

In the `main.py` file, find the `modules` list, and replace `oncall` with your module. Make sure it follows the import pattern of the other modules!

## Environmentals

`token` is the only one you need if you disable `oncall`. Please disable `oncall`

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

### app

The app is the actual bot code provided by the python-telegram-bot library. It's the core of the application. For the most part, you won't need to interact with it except:

-


### persistence

This is the layer of the app that will initially load saved state data via pickle. You should never interact with this layer because data access in flight is controlled by the application, and anything you write to this layer will get overwritten by the application anyways.

### update

In the scope of a handler, an update is an object that represents the incomming message. This is important to check things like message text/author, but also gives you helper methods to reply / delete / change messages. 

### context

Inside a handler, the context acts like a hook back to the application. This is the primary way you interact with saved state on a per user/chat basis. Context is read/write and things set will be persisted both to future messages AND to the disk (unless cleared)


### context.user_data

This is `TGUser` object that represents a user (usually in the context of a message author). 

### context.chat_data

This is a `TGChat` object that represents a group/super chat (usually in the context of the space a message was sent in)


### updater / dispatcher

updates are queued as they are received and processing of messages is performed serially (with current configuration). Do not execute long running tasks inside a handler unless needed.
