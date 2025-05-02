In config.json, Replace "YOUR_BOT_TOKEN" with your discord bot token key from Discord developer portal, if you want you can also add a ai chat model juet replace the model with model from openrouter ai models and get the key and paste that in config.json.

*FEATURES OF THE BOT* 


1. Moderation Features

/kick: Kick a member with a reason.

/ban: Ban a member with a reason.

/warn: Warn a member and log it.

/clear: Bulk delete messages in a channel.

/addrole and /removerole: Add or remove roles from members.

/autorole: Automatically assigns a role to new members.

/set_logs: Set channels for message/image/mod logs.



---

2. Logging System

Logs for:

Deleted messages

Edited messages

Command usage (log_command helper)

Member joins (with optional autorole)


Supports a mod log channel (MOD_LOG_CHANNEL_ID) for centralized logs.



---

3. Welcome & Leave System

/set_welcome: Configure a welcome message, channel, and optional image/GIF.

/remove_welcome: Disable the welcome system.

/set_leave: Set up a goodbye message and channel.

/remove_leave: Disable the leave message system.



---

4. Utility Commands

!say: Makes the bot say a message (permission-based).

/set_say_role: Set a specific role allowed to use !say.

/ping: Bot latency test.



---

5. Configuration & Persistence

Uses config.json to persist:

Prefix

Roles and channels for moderation

Autorole

Logging channels


Uses command_logs.json to track command usage history.



---

6. Code Design Strengths

Uses both prefix commands and slash commands (hybrid).

Admin/permission checks for all sensitive commands.

Clean use of embeds for logs and messages.

*⚠️IF YOU WANNA USE REPLIT TO MAKE BOT ACTIVE 24/7*
there's a keep_alive file which you can easily import to replit and also import the requirements file if you wanna run it properly!
