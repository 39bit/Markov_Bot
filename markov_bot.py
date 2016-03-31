# -*- coding: utf-8 -*-

# markovbot.py


T = "BOT_TOKEN"


















groups = {}

import os.path, pickle
if os.path.isfile("MarkovBot_stats.dat"):
    with open("MarkovBot_stats.dat", "rb") as f:
        groups = pickle.load(f)
else:
    print("not a file")
    print("1-800-FIX-YOUR-SHIT")















SKIP = False

import logging
# https://github.com/python-telegram-bot/python-telegram-bot
import telegram
import time
from time import sleep

import sys, traceback

try:
    from urllib.error import URLError
except ImportError:
    from urllib2 import URLError  # python 2

def save():
    if os.path.isfile("MarkovBot_stats.dat"):
        print("SAVING")
        with open("MarkovBot_stats.dat", "wb") as f:
            pickle.dump(groups, f)
        print("SAVED")

def main():
    update_id = None

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    bot = telegram.Bot(T)

    counter = 0
    rate_lim = False
    last_uid = None

    ij = 0
    try:
        while True:
            try:
                update_id = echo(bot, update_id)
                ij += 1
                if ij == 256:
                    ij = 0
                    save()
                if last_uid == None:
                    last_uid = update_id
                elif update_id > last_uid:
                    rate_lim = False
                    counter = 0
                elif update_id == last_uid and SKIP:
                    print("Queue flushed")
                last_uid = update_id
                #print(":" + str(update_id))
            except telegram.TelegramError as e:
                if e.message in ("Bad Gateway", "Timed out"):
                    counter = 0
                    sleep(1)
                elif "Too many requests" in e.message:
                    counter += 1
                    print("Ratelimit: sleeping for ", 5*counter, " seconds")
                    sleep(5*counter)
                    rate_lim = True
                else:
                    counter = 0
                    raise e
            except KeyboardInterrupt as e:
                print("EXITING - DO NOT TERMINATE")
                save()
                return
            except URLError as e:
                sleep(1)
                counter = 0
            if not rate_lim:
                counter = 0
    except BaseException as e:
        save()
        raise e
            

import random, unicodedata, os
ALLOWABLE = ["Lc","Ll","Lm","Lo","Lt","Lu","Nd","Nl","No"]
COMMON_T = 0

def addMessage(message, g):
    w = [""] + message.lower().split(" ") + [""]
    for i in range(1,len(w)):
        lw = "".join(filter(lambda x:(unicodedata.category(x) in ALLOWABLE),w[i-1]))
        nw = w[i]
        if len(lw) < 50 and len(nw) < 50:
            if lw not in g.keys():
                g[lw] = []
            g[lw].append(nw)

SPLIT_LINES = False
LAST_USER = {}

import os

def limit(s):
    t = " ".join(s.split(" ")[:50])
    return t[:400]

LANGS = ["af","an","bg","bs","ca","cs","cy","da","de","el","en","en-gb","en-sc","en-uk-north","en-uk-rp","en-uk-wmids","en-us","en-wi","eo","es","es-la","et","fa","fa-pin","fi","fr-be","fr-fr","ga","grc","hi","hr","hu","hy","hy-west","id","is","it","jbo","ka","kn","ku","la","lfn","lt","lv","mk","ml","ms","ne","nl","no","pa","pl","pt-br","pt-pt","ro","ru","sk","sq","sr","sv","sw","ta","tr","vi","vi-hue","vi-sgn","zh","zh-yue"]

def echo(bot, update_id):
    global COMMON_T

    for update in bot.getUpdates(offset=update_id, timeout=10):
        chat_id = update.message.chat_id
        update_id = update.update_id + 1
        message = update.message.text
        replyto = update.message.message_id
        user = update.message.from_user.id

        if chat_id not in groups.keys():
            groups[chat_id] = {}
                
        g = groups[chat_id]
        if 0 not in g.keys():
            g[0] = 1
        if 1 not in g.keys():
            g[1] = "en"
        if 2 not in g.keys():
            g[2] = 100
            
        curtime = time.time()
        t = (user, chat_id)
        
        if len(message) < 1:
            continue
        if message[0] == "/":
            rcmd = message.split(" ")[0].split("@")[0]
            cmd = rcmd.lower()
            if cmd == "/markov":
                if SKIP: continue
                if t in LAST_USER.keys():
                    if (curtime - LAST_USER[t]) < g[0]:
                        continue
                LAST_USER[t] = curtime
                COMMON_T += 1
                if COMMON_T == 8:
                    COMMON_T = 0
                    save()
                if "" in g.keys():
                    while True:
                        words = []
                        word = ""
                        word = random.choice(g[""])
                        while word != "" and len(words) < 100:
                            words.append(word)
                            word = "".join(filter(lambda x:(unicodedata.category(x) in ALLOWABLE),word)).lower()
                            if word not in g.keys():
                                word = ""
                            else:
                                word = random.choice(g[word])
                            if word == "" and random.randint(0,8)<5:
                                word = random.choice(list(g.keys()))
                                while type(word) != str:
                                    word = random.choice(list(g.keys()))
                                if random.randint(0,10)<3 and len(words)>0:
                                    if words[-1] not in "!:,.?;":
                                        words[-1] += "."
                        msg = " ".join(words)
                        if len(msg) > 0: break
                    bot.sendMessage(chat_id=chat_id,
                            text=msg)
                else:
                    bot.sendMessage(chat_id=chat_id,
                            text="[Chain is empty]",
                            reply_to_message_id=replyto)
            if cmd == "/mlimit":
                if SKIP: continue
                t = " ".join(message.split(" ")[1:]).strip()
                if len(t) < 1:
                    bot.sendMessage(chat_id=chat_id,
                            text="[Usage: /mlimit seconds]",
                            reply_to_message_id=replyto)
                    continue
                try:
                    v = int(t)
                except:
                    bot.sendMessage(chat_id=chat_id,
                            text="[Usage: /mlimit seconds]",
                            reply_to_message_id=replyto)
                    continue
                if v <= 0 or v > 10000:
                    bot.sendMessage(chat_id=chat_id,
                            text="[limit must be between 1-10 000 seconds]",
                            reply_to_message_id=replyto)
                    continue
                bot.sendMessage(chat_id=chat_id,
                        text="[Limit set]",
                        reply_to_message_id=replyto)
                g[0] = v
            if cmd == "/markovttsspeed":
                if SKIP: continue
                t = " ".join(message.split(" ")[1:]).strip()
                if len(t) < 1:
                    bot.sendMessage(chat_id=chat_id,
                            text="[Usage: /markovttsspeed wpm]",
                            reply_to_message_id=replyto)
                    continue
                try:
                    v = int(t)
                except:
                    bot.sendMessage(chat_id=chat_id,
                            text="[Usage: /markovttsspeed wpm]",
                            reply_to_message_id=replyto)
                    continue
                if v < 80 or v > 500:
                    bot.sendMessage(chat_id=chat_id,
                            text="[Speed must be between 80-500 wpm]",
                            reply_to_message_id=replyto)
                    continue
                bot.sendMessage(chat_id=chat_id,
                        text="[Speed set]",
                        reply_to_message_id=replyto)
                g[2] = v
            if cmd == "/markovtts":
                if t in LAST_USER.keys():
                    if (curtime - LAST_USER[t]) < max(5,g[0]):
                        continue
                LAST_USER[t] = curtime
                COMMON_T += 1
                if COMMON_T == 8:
                    COMMON_T = 0
                    save()
                if "" in g.keys():
                    while True:
                        words = []
                        word = ""
                        word = random.choice(g[""])
                        while word != "" and len(words) < 120:
                            words.append(word)
                            word = "".join(filter(lambda x:(unicodedata.category(x) in ALLOWABLE),word)).lower()
                            if word not in g.keys():
                                word = ""
                            else:
                                word = random.choice(g[word])
                            if word == "" and random.randint(0,8)<6:
                                word = random.choice(list(g.keys()))
                                while type(word) != str:
                                    word = random.choice(list(g.keys()))
                                if random.randint(0,10)<3 and len(words)>0:
                                    if words[-1] not in "!:,.?;":
                                        words[-1] += "."
                        msg = " ".join(words)
                        if len(msg) > 0: break
                    def quoteEscape(s):
                        return s.replace("\\","\\\\").replace("\"","\\\"")
                    try:
                        os.system("rm markov.ogg 2>nul")
                        os.system("espeak -s" + str(g[2]) + " -v" + g[1] + " \"" + limit(quoteEscape(msg)) + "\" --stdout | opusenc - markov.ogg >nul 2>&1")
                        bot.sendVoice(chat_id=chat_id,
                            voice=open("markov.ogg","rb"))
                    except BaseException as e:
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        print("\n".join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
                        bot.sendMessage(chat_id=chat_id,
                                text="Could not send voice",
                                reply_to_message_id=replyto)                    
                else:
                    bot.sendMessage(chat_id=chat_id,
                            text="[Chain is empty]",
                            reply_to_message_id=replyto)
            if cmd == "/markovttslang":
                v = " ".join(message.split(" ")[1:]).strip()
                if v not in LANGS:
                    bot.sendMessage(chat_id=chat_id,
                            text=("[Unknown language]\n" if len(v) > 0 else "") + ", ".join(LANGS),
                            reply_to_message_id=replyto)
                    continue
                bot.sendMessage(chat_id=chat_id,
                        text="[Language set]",
                        reply_to_message_id=replyto)
                g[1] = v
        elif message[0] != "/":
            g = groups[chat_id]
            if SPLIT_LINES:
                for line in message.split("\n"):
                    addMessage(line, g)
            else:
                addMessage(message, g)
            
        
    sleep(0.5)
    return update_id
    
    
    
import logging

if __name__ == '__main__':
    while True:
        try:
            main()
            save()
            import sys
            sys.exit(0)
        except SystemExit as e:
            break
        except BaseException as e:
            logging.exception(e)
