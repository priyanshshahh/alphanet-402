# Configure Claude Code as an AI Assistant, with a crypto theme

*Andy Singleton, [andy@singleton.ai](mailto:andy@singleton.ai), @zingle on telegram*

You can use many different apps to run an AI assistant. This workshop uses the popular Claude Code as an AI app, and Whatsapp for group chat..

See the workshop agenda at [Singleton.ai/w1](http://Singleton.ai/w1)

## Setup

[Join the Whatsapp chat](https://chat.whatsapp.com/G1VKlwnuwJX4xN7IGvFlkT?mode=gi_t)

[Get a Claude account](https://claude.com/pricing)

[Install Claude Code](https://code.claude.com/docs/en/desktop-quickstart)

## Create a project directory

Claude Code can add objects like “skills” in a project directory.

* Create a new directory called “workshop”  
* *Enable “bypass permissions” mode in Claude settings*  
* Set the “workshop” directory as the default directory  
* *Optional: Open a shell window (Terminal on Mac, Powershell on Windows) and “cd workshop”*
* Initialize this folder as a Claude Code project

## Add the workshop plugin

I created a plugin to make it easier to install the skills for email-triage, token-info, and skill-creator.

* install the workshop plugin from zingleton/workshop with project scope
* *Start a new session*
* What skills are in this project?

## Make a [CLAUDE.md](http://CLAUDE.md) reference

AI assistants typically have a file with reference information about you and the bot.

* Write a [CLAUDE.md](http://CLAUDE.md) file. Add this information: This project accumulates skills for a personal assistant. The assistant can do communication, prioritization, and some crypto operations. Add new skills and plugins with project scope. My name is \<name\>. My LinkedIn account is \<URL\>. My email address is \<email\>  
* Show me the [Claude.md](http://Claude.md) file as an HTML artifact

## Assist with email

* *Go to Claude Settings/Connectors and connect gmail. The result is that your app gets an MCP server that provides tools for the AI to read your email.*

### Load a skill that uses the email connector

* *Add the email plugin from this repository: [https://github.com/zingleton/workshop](https://github.com/zingleton/workshop)*  
* *Start a new Claude Code session*  
* What skills are in this project?  
* *Look at the skill definition at [https://github.com/zingleton/workshop/blob/main/skills/email-triage/SKILL.md](https://github.com/zingleton/workshop/blob/main/skills/email-triage/SKILL.md)*  
* /email

### Make a new request

* *Make a new request. For example, “*Summarize the newsletters with one paragraph for each newsletter”  
* *Modify the skill*  
* Change the email-triage skill. Add “Summarize newsletters with one paragraph for each newsletter”

## Add a tool to operate a flight search app

The underlying use case of an AI assistant is to operate apps for you. The assistant gets “tools” to operate those apps, and skills that explain the tools. In this case, the “tool” is a command line interface. AI coders like Claude Code work well with CLI tools. 

* Add to [CLAUDE.md](http://CLAUDE.md) “I live in Boston.”

### PrintingPress version

Printing Press turns web sites into CLI tools.

* *Add the flight-goat CLI with “npx \-y @mvanhorn/printing-press install starter-pack”*  
  * It will unfortunately ask to install “go”  
* pp-flight-goat Go to Florence Italy on July 20, plus or minus one day, shortest first

### Optional LetsFG version

LetsFG MCP server is defined in the workshop plugin.

* Figure out how to install LetsFG. Requires Python. https://github.com/LetsFG/LetsFG  
* Use LetsFG to find a flight from Boston to Florence Italy, on July 20, plus or minus one day, shortest first

## View crypto token data

The plugin includes a [query-token-info](https://github.com/binance/binance-skills-hub/blob/main/skills/binance-web3/query-token-info/SKILL.md) skill that gets free data from Binance. This skill does not install an MCP or CLI tool. It defines HTTP calls inside the text of the skill file. Skills can also contain text scripts that implement tools.

* Get 30 days of kline data for ETH  
* Graph the ETH price for the last 30 days in the artifact window
* *What other data can we get from query-token-info? Can we display it graphically?*

## Add some crypto skills from Moonpay

* Add moonpay/skills marketplace with project scope  
* What skills are in the moonpay-agent-skills marketplace?  
* add the moonpay-skills with project scope. Install the moonpay CLI  
* Add the dune-skills with project scope  
* *New session to load skills*

### Create a wallet

This will create a wallet that uses the “Open Wallet Standard”. I think this is the best type of wallet for an AI agent. By default, it saves a key in the local operating system “keyring”. If you want to use it to handle commercial-scale assets, you can configure it with “policies” and move the signer to a remote server that your AI cannot hack.

* Create a default wallet using the moonpay-auth skill  
* Save the wallet addresses in the CLAUDE.md for this project  
* What is the balance in my ETH wallet?

### Get some assets for the wallet

* If you try moonpay-buy-crypto it will reject you, or ask you for  lot of personal information  
* Send yourself a small amount of crypto, or get a little bit from the instructor by posting your EVM address in the chat

## Create a new skill

The workshop plugin includes the skill-creator skill from Anthropic. It writes a skill in the correct format, and then suggests ways to evaluate and improve it.

* *Ask Claude to create a new skill*

