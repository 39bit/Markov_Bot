import os.path, pickle, hashlib, logging, telegram, time, sys, traceback, random, unicodedata, os, gc
 
T = "BOT_TOKEN_GOES_HERE"

groups = {}
          
# Unicode character categories considered    
ALLOWABLE = ["Lc","Ll","Lm","Lo","Lt","Lu","Nd","Nl","No"]
COMMON_T = 0

SPLIT_LINES = False
LAST_USER = {}

# Supported TTS languages
LANGS = ["af","an","bg","bs","ca","cs","cy","da","de","el","en","en-gb","en-sc","en-uk-north","en-uk-rp","en-uk-wmids","en-us","en-wi","eo","es","es-la","et","fa","fa-pin","fi","fr-be","fr-fr","ga","grc","hi","hr","hu","hy","hy-west","id","is","it","jbo","ka","kn","ku","la","lfn","lt","lv","mk","ml","ms","ne","nl","no","pa","pl","pt-br","pt-pt","ro","ru","sk","sq","sr","sv","sw","ta","tr","vi","vi-hue","vi-sgn","zh","zh-yue"]

gcache = []
# how many groups will be cached at most at one time
max_cache_size = 10
# GC is forced every N group unloads
gc_every_unload = 30
gc_counter = gc_every_unload

# obtained when the bot is initialized
MY_USERNAME = ""

try:
    from urllib.error import URLError
except ImportError:
    from urllib2 import URLError 

def save(reason):
    print("SAVING ",reason)
    for key in groups:
        save_group(key)
    print("SAVED")

last_msg_id = 0
def main():
    global last_msg_id, MY_USERNAME
    update_id = None

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    bot = telegram.Bot(T)
    MY_USERNAME = bot.getMe()["username"].lower()

    counter = 0
    rate_lim = False
    last_uid = None
    save_counter = 0
    try:
        while True:
            try:
                update_id = echo(bot, update_id)
                save_counter += 1
                if save_counter == 1024:
                    save_counter = 0
                    save("/"+str(save_counter)+" update")
                if last_uid == None:
                    last_uid = update_id
                elif update_id > last_uid:
                    rate_lim = False
                    counter = 0
                last_uid = update_id
            except telegram.error.NetworkError as e:
                if "400" in str(e) or "message not found" in str(e):
                    update_id = last_msg_id + 1
                    print("!!",update_id)
                else:
                    time.sleep(1)
                    counter = 0
            except telegram.TelegramError as e:
                if e.message in ("Bad Gateway", "Timed out"):
                    counter = 0
                    time.sleep(1)
                elif "Too many requests" in e.message:
                    counter += 1
                    print("Ratelimit: sleeping for ", 5*counter, " seconds")
                    time.sleep(5*counter)
                    rate_lim = True
                elif "Unauthorized" in e.message:
                    update_id = last_msg_id + 1
                    print("!!",update_id)
                elif "400" in e.message:
                    update_id=last_msg_id+1
                    print("!!",update_id)
                elif "invalid server response" in e.message.lower():
                    time.sleep(1)
                else:
                    counter = 0
                    raise e
            except KeyboardInterrupt as e:
                print("EXITING - DO NOT TERMINATE")
                save("Ctrl-C")
                return
            except URLError as e:
                time.sleep(1)
                counter = 0
            if not rate_lim:
                counter = 0
    except BaseException as e:
        save("Exception")
        raise e

def addMessage(message, g):
    w = [""] + message.lower().split(" ") + [""]
    for i in range(1,len(w)):
        lw = "".join(filter(lambda x:(unicodedata.category(x) in ALLOWABLE),w[i-1]))
        nw = w[i]
        if len(lw) < 50 and len(nw) < 50:
            if lw not in g.keys():
                g[lw] = []
            g[lw].append(nw)


def limit(s):
    t = " ".join(s.split(" ")[:50])
    return t[:400]

def load_group(chat_id):
    global gcache
    try:
        with open("markov/chat_" + str(chat_id) + ".dat", "rb") as f:
            groups[chat_id] = pickle.load(f)
        gcache.append(chat_id)
    except:
        pass
    check_cache()

def check_cache():
    global gcache
    while len(gcache) > max_cache_size:
        unload_group(gcache[0])
        gcache = gcache[1:]

def unload_group(chat_id):
    global gcache, gc_counter
    try:
        with open("markov/chat_" + str(chat_id) + ".dat", "wb") as f:
            pickle.dump(groups[chat_id], f)
            groups[chat_id] = None
            del groups[chat_id]
        gcache.remove(chat_id)
        gc_counter -= 1
        if gc_counter < 1:
            gc_counter = gc_every_unload
            gc.collect()
    except:
        pass

def save_group(chat_id):
    try:
        with open("markov/chat_" + str(chat_id) + ".dat", "wb") as f:
            pickle.dump(groups[chat_id], f)
    except:
        pass
    
def generateMarkovOgg(msg, g):
    # g are the group settings
    # msg is the message data
    # call espeak and opusenc
    os.system("rm markov.ogg 2>nul")
    os.system("espeak -s" + str(g[2]) + " -v" + g[1] + " \"" + limit(quoteEscape(msg)) + "\" --stdout | opusenc - markov.ogg >nul 2>&1")

def echo(bot, update_id):
    global COMMON_T, last_msg_id, gcache

    for update in bot.getUpdates(offset=update_id, timeout=10):
        last_msg_id = update.update_id
        if update.message == None:
            continue
        chat_id = update.message.chat_id
        chat_type = update.message.chat.type
        update_id = update.update_id + 1
        message = update.message.text
        replyto = update.message.message_id
        user = update.message.from_user.id
        admbypass = False
        try:
            admbypass = admbypass or update.message.chat.all_members_are_administrators
        except:
            pass

        if chat_id not in gcache:
            load_group(chat_id)

        if chat_id not in groups.keys():
            groups[chat_id] = {}
            gcache.append(chat_id)
            check_cache()
                
        # g contents
        # [mlimit, tts language, tts speed, markov collecting (pause/resume), ~ maximum words]
        g = groups[chat_id]
        if g == None:   
            groups[chat_id] = {}
            g = {}
        if 0 not in g.keys():
            g[0] = 1
        if 1 not in g.keys():
            g[1] = "en"
        if 2 not in g.keys():
            g[2] = 100
        if 3 not in g.keys():
            g[3] = True
        if 4 not in g.keys():
            g[4] = 10000
            
        curtime = time.time()
        t = str(user) + ":" + str(chat_id)
        
        if len(message) < 1:
            continue
        if message[0] == "/":
            rcmd = message.split(" ")[0].split("@")[0]
            if "@" in message.split(" ")[0]:
                cmdtarget = message.split(" ")[0].split("@")[1]
                # if the command is aimed at some other bot
                if cmdtarget.lower() != MY_USERNAME:
                    continue
            cmd = rcmd.lower()
            if cmd == "/markov":
                if t in LAST_USER.keys():
                    if (curtime - LAST_USER[t]) < g[0]:
                        continue

                LAST_USER[t] = curtime
                COMMON_T += 1
                if COMMON_T == 8:
                    COMMON_T = 0
                tries_o = 0
                if "" in g.keys():
                    while True:
                        tries_o += 1
                        words = []
                        word = ""
                        if random.randint(0,10)<5:
                            word = random.choice(list(filter(lambda x:type(x)==str,g.keys())))
                        else:
                            word = random.choice(g[word])
                        while word != "" and len(words) < min(g[4],100):
                            words.append(word)
                            word = "".join(filter(lambda x:(unicodedata.category(x) in ALLOWABLE),word)).lower()
                            if word not in g.keys():
                                word = ""
                            else:
                                word = random.choice(g[word])
                        msg = " ".join(words)
                        if len(msg) > 0: break
                        if tries_o > 1000: break
                    try:
                        bot.sendMessage(chat_id=chat_id,
                            text=msg)
                    except:
                        pass
                else:
                    try:
                        bot.sendMessage(chat_id=chat_id,
                            text="[Chain is empty]",
                            reply_to_message_id=replyto)
                    except:
                        pass
            if cmd == "/mlimit":
                if t in LAST_USER.keys():
                    if (curtime - LAST_USER[t]) < 1:
                        continue
                try:
                    st = bot.getChatMember(chat_id=chat_id, user_id=user).status
                    if chat_type in ["group","supergroup","channel"] and not admbypass and (st != "administrator" and st != "creator"):
                        continue
                except:
                    pass
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
                if v <= 0 or v > 100000:
                    bot.sendMessage(chat_id=chat_id,
                            text="[limit must be between 1-100 000 seconds]",
                            reply_to_message_id=replyto)
                    continue
                #print(t, "=", g[0])
                bot.sendMessage(chat_id=chat_id,
                        text="[Limit set]",
                        reply_to_message_id=replyto)
                g[0] = v
            if cmd == "/markovttsspeed":
                if t in LAST_USER.keys():
                    if (curtime - LAST_USER[t]) < 1:
                        continue
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
            if cmd == "/markovmaxwords":
                if t in LAST_USER.keys():
                    if (curtime - LAST_USER[t]) < 1:
                        continue
                try:
                    st = bot.getChatMember(chat_id=chat_id, user_id=user).status
                    if chat_type in ["group","supergroup","channel"] and not admbypass and (st != "administrator" and st != "creator"):
                        continue
                except:
                    pass
                t = " ".join(message.split(" ")[1:]).strip()
                if len(t) < 1:
                    bot.sendMessage(chat_id=chat_id,
                            text="[Usage: /markovmaxwords words]",
                            reply_to_message_id=replyto)
                    continue
                try:
                    v = int(t)
                except:
                    bot.sendMessage(chat_id=chat_id,
                            text="[Usage: /markovmaxwords words]",
                            reply_to_message_id=replyto)
                    continue
                if v < 1 or v > 120:
                    bot.sendMessage(chat_id=chat_id,
                            text="[Limit for words is 1-120]",
                            reply_to_message_id=replyto)
                    continue
                g[4] = v
                save_group(chat_id)
                bot.sendMessage(chat_id=chat_id,
                    text="[Maximum words set]",
                    reply_to_message_id=replyto)                    
            if cmd == "/markovclear":
                if t in LAST_USER.keys():
                    if (curtime - LAST_USER[t]) < 1:
                        continue
                try:
                    # do not allow non-admins to clear
                    st = bot.getChatMember(chat_id=chat_id, user_id=user).status
                    if chat_type in ["group","supergroup","channel"] and not admbypass and (st != "administrator" and st != "creator"):
                        continue
                except:
                    pass
                checkhash = hashlib.md5((str(chat_id)+str(user)+str(time.time()//1000)).encode("utf-8")).hexdigest()[:12].upper()
                what = ""
                try:
                    what = message.split(" ")[1].upper()
                except:
                    pass
                if what == checkhash:
                    groups[chat_id] = {}
                    save_group(chat_id)
                    bot.sendMessage(chat_id=chat_id,
                        text="[Messages cleared]",
                        reply_to_message_id=replyto)                    
                else:
                    bot.sendMessage(chat_id=chat_id,
                        text="[Copy this to confirm]\n/markovclear " + checkhash,
                        reply_to_message_id=replyto)
            if cmd == "/markovpause":
                if t in LAST_USER.keys():
                    if (curtime - LAST_USER[t]) < 1:
                        continue
                try:
                    st = bot.getChatMember(chat_id=chat_id, user_id=user).status
                    if chat_type in ["group","supergroup","channel"] and not admbypass and (st != "administrator" and st != "creator"):
                        continue
                except:
                    pass
                g[3] = False
                save_group(chat_id)
                bot.sendMessage(chat_id=chat_id,
                    text="[Reading paused]",
                    reply_to_message_id=replyto)                    
            if cmd == "/markovresume":
                if t in LAST_USER.keys():
                    if (curtime - LAST_USER[t]) < 1:
                        continue
                try:
                    st = bot.getChatMember(chat_id=chat_id, user_id=user).status
                    if chat_type in ["group","supergroup","channel"] and not admbypass and (st != "administrator" and st != "creator"):
                        continue
                except:
                    pass
                g[3] = True
                save_group(chat_id)
                bot.sendMessage(chat_id=chat_id,
                    text="[Reading resumed]",
                    reply_to_message_id=replyto)                    
            if cmd == "/markovtts":
                if t in LAST_USER.keys():
                    if (curtime - LAST_USER[t]) < max(5,g[0]):
                        continue
                LAST_USER[t] = curtime
                COMMON_T += 1
                if COMMON_T == 8:
                    COMMON_T = 0
                if "" in g.keys():
                    while True:
                        words = []
                        word = ""
                        if random.randint(0,10)<5:
                            word = random.choice(list(filter(lambda x:type(x)==str,g.keys())))
                        else:
                            word = random.choice(g[word])
                        while word != "" and len(words) < min(g[4],120):
                            words.append(word)
                            word = "".join(filter(lambda x:(unicodedata.category(x) in ALLOWABLE),word)).lower()
                            if word not in g.keys():
                                word = ""
                            else:
                                word = random.choice(g[word])
                        msg = " ".join(words)
                        if len(msg) > 0: break
                    def quoteEscape(s):
                        return s.replace("\\","\\\\").replace("\"","\\\"")
                    try:
                        generateMarkovOgg(msg, g)
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
                if t in LAST_USER.keys():
                    if (curtime - LAST_USER[t]) < 1:
                        continue
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
            if g[3]:
                if SPLIT_LINES:
                    for line in message.split("\n"):
                        addMessage(line, g)
                else:
                    addMessage(message, g)       
    return update_id
    
import logging

if __name__ == '__main__':
    while True:
        try:
            main()
            import sys
            sys.exit(0)
        except KeyboardInterrupt:
            input()
            import sys
            sys.exit(0)
        except SystemExit:
            break
        except BaseException as e:
            logging.exception(e)
            input()
