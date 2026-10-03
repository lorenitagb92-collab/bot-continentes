import socket, time, re, urllib.parse, urllib.request, json, os, random, threading

SERVER="irc.viciochat.org"
PORT=6667
NICK="BotGuardContinentes"
PASS="Inform@tico13686"
CANAL="#continentes"
CANAL_NO="#chat"
OPS_PERMA=["afrodita","exflakis","escorpiona","abby26"]
ops=set()

AKICK_FILE="akick.txt"
MENSAJES_FILE="mensajes.json"
OBSCENAS_FILE="obscenas.txt"

PALABRAS_DEFAULT=["polla","tetas","leche","semen","culo","verga","pollon","ano","pezones","follo","follar","coño","cono","pene","porno","orgia","orgía","puta","puto","zorra","chupar","corrida","pajero","pajera","masturbar","anal","vagina","chocho","coger","follador","folladora","pollas","tetona","culona"]

def cargar_obscenas():
    lista=set(PALABRAS_DEFAULT)
    if os.path.exists(OBSCENAS_FILE):
        try:
            for l in open(OBSCENAS_FILE,"r",encoding="utf-8").read().splitlines():
                if l.strip(): lista.add(l.strip().lower())
        except: pass
    return lista

def guardar_obscenas(lista):
    try:
        extras=[p for p in lista if p not in PALABRAS_DEFAULT]
        open(OBSCENAS_FILE,"w",encoding="utf-8").write("\n".join(sorted(extras)))
    except: pass

PALABRAS_OBSCENAS=cargar_obscenas()
avisos_obscenos={}
kickeados_obscenos=set()

def cargar_akick():
    try: return set([x.strip().lower() for x in open(AKICK_FILE).read().splitlines() if x.strip()])
    except: return set()

def guardar_akick(lista):
    open(AKICK_FILE,"w").write("\n".join(lista))

def cargar_mensajes():
    try:
        if os.path.exists(MENSAJES_FILE): return json.loads(open(MENSAJES_FILE).read())
    except: pass
    return {}

def guardar_mensajes(d):
    try: open(MENSAJES_FILE,"w").write(json.dumps(d, ensure_ascii=False))
    except: pass

akick_lista=cargar_akick()
mensajes_pendientes=cargar_mensajes()

TRIVIAS=[
    {"q":"¿Capital de Japón?","op":"1)Seúl 2)Tokio 3)Pekín","r":"2","a":"tokio"},
    {"q":"¿Año llegada Luna?","op":"1)1969 2)1972 3)1959","r":"1","a":"1969"},
    {"q":"¿Río más largo?","op":"1)Nilo 2)Amazonas 3)Yangtsé","r":"2","a":"amazonas"},
    {"q":"¿Quién pintó Mona Lisa?","op":"1)Picasso 2)Da Vinci 3)Miguel Ángel","r":"2","a":"da vinci"},
    {"q":"¿Cuántos continentes hay?","op":"1)5 2)6 3)7","r":"3","a":"7"},
]
trivia_actual=None
trivia_puntos={}

def limpiar_nick(u): return u.lstrip(":").lstrip("@%+~&!").lower().strip()
def limpiar_msg(t):
    t=re.sub(r'\x03\d{0,2}(?:,\d{1,2})?', '', t)
    return re.sub(r'[\x02\x1f\x16\x0f\x1d]', '', t).strip()
def es_op(n):
    nl=limpiar_nick(n)
    if nl in ops: return True
    for p in OPS_PERMA:
        if p in nl: return True
    return False
def es_perma(n):
    nl=limpiar_nick(n)
    for p in OPS_PERMA:
        if p in nl: return True
    return False
def es_obsceno(nick):
    nl=limpiar_nick(nick)
    for pal in PALABRAS_OBSCENAS:
        if pal in nl: return pal
    return None
def get_ia(p):
    try:
        q=urllib.parse.quote(f"Eres BotGuardContinentes divertido picaro español, respuesta corta 2 lineas max: {p}")
        url=f"https://text.pollinations.ai/{q}"
        req=urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
        data=urllib.request.urlopen(req, timeout=15).read().decode(errors='ignore')
        return data.strip()[:400]
    except Exception as e: return f"Error IA: {e}"
def buscar_yt(q):
    try:
        url="https://www.youtube.com/results?search_query="+urllib.parse.quote(q)
        req=urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
        html=urllib.request.urlopen(req, timeout=10).read().decode(errors='ignore')
        vid=re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"', html)[0]
        tit=re.search(r'"title":\{"runs":\[{"text":"([^"]+)"', html)
        nombre=tit.group(1) if tit else q
        return f"{nombre} - https://youtu.be/{vid}"
    except: return None
def get_tiempo(c):
    try:
        url=f"https://wttr.in/{urllib.parse.quote(c)}?format=j1"
        req=urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
        data=json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
        cur=data['current_condition'][0]
        return f"🌤️ {c.title()}: {cur['weatherDesc'][0]['value']}, {cur['temp_C']}°C Hum {cur['humidity']}%"
    except: return None
def get_horoscopo(s):
    mapa={"aries":"aries","tauro":"taurus","geminis":"gemini","cancer":"cancer","leo":"leo","virgo":"virgo","libra":"libra","escorpio":"scorpio","sagitario":"sagittarius","capricornio":"capricorn","acuario":"aquarius","piscis":"pisces"}
    s=mapa.get(s.lower().strip(), s.lower().strip())
    try:
        url=f"https://horoscope-app-api.vercel.app/api/v1/get-horoscope/daily?sign={s}&day=today"
        req=urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
        data=json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
        return f"♈ {s.capitalize()}: {data['data']['horoscope_data']}"
    except: return None
def enviar(s,m):
    try:
        s.send((m+"\r\n").encode())
        print(">>",m)
    except: pass
def entregar(s,nick_dest):
    base=limpiar_nick(nick_dest).split("|")[0].split("_")[0]
    for clave in [limpiar_nick(nick_dest), base]:
        if clave in mensajes_pendientes and mensajes_pendientes[clave]:
            for mm in mensajes_pendientes[clave]:
                enviar(s,f"PRIVMSG {nick_dest} :📩 De {mm['de']} ({mm['fecha']}): {mm['msg']}")
                time.sleep(0.8)
            del mensajes_pendientes[clave]
            guardar_mensajes(mensajes_pendientes)

def check_obsceno(s,nick,paso):
    nl=limpiar_nick(nick)
    if nl not in avisos_obscenos: return
    if paso==2:
        enviar(s,f"PRIVMSG {CANAL} :⚠️ {nick} ULTIMO AVISO - Cambia nick o KICK en 30s")
        threading.Timer(30, lambda: check_obsceno(s,nick,3)).start()
    elif paso==3:
        enviar(s,f"KICK {CANAL} {nick} :🚫 Nick obsceno")
        kickeados_obscenos.add(nl)

# BUCLE PRINCIPAL
while True:
    try:
        s=socket.socket()
        s.connect((SERVER,PORT))
        enviar(s,f"NICK {NICK}")
        enviar(s,f"USER {NICK} 0 * :Bot")
        while True:
            data=s.recv(4096).decode(errors='ignore')
            if not data: break
            for l in data.split("\r\n"):
                if not l: continue
                print(l)
                if l.startswith("PING"):
                    enviar(s,f"PONG {l.split()[1]}")
                if "registrado y protegido" in l or "elijas otro" in l:
                    enviar(s,f"PRIVMSG NiCK :IDENTIFY {PASS}")
                if " 900 " in l or "Password accepted" in l or "Has sido reconocido" in l:
                    time.sleep(1)
                    enviar(s,f"JOIN {CANAL}")
                if f":{NICK}!" in l and "JOIN" in l and CANAL_NO in l:
                    enviar(s,f"PART {CANAL_NO} :Solo {CANAL}")
                if " NICK :" in l:
                    try:
                        nuevo=l.split(" NICK :")[1].strip()
                        if es_obsceno(nuevo) and not es_op(nuevo):
                            enviar(s,f"PRIVMSG {CANAL} :⚠️ {nuevo} nick obsceno ({es_obsceno(nuevo)}) cambia o kick")
                    except: pass

                if ("JOIN "+CANAL in l or "JOIN :"+CANAL in l) and f":{NICK}!" not in l:
                    try:
                        nuevo=l.split("!")[0][1:]
                        if not nuevo or nuevo.lower()==NICK.lower(): continue
                        pal=es_obsceno(nuevo)
                        if pal and not es_op(nuevo):
                            nl=limpiar_nick(nuevo)
                            if nl in kickeados_obscenos:
                                enviar(s,f"MODE {CANAL} +b {nuevo}!*@*")
                                time.sleep(0.5)
                                enviar(s,f"KICK {CANAL} {nuevo} :🚫 Nick obsceno BAN")
                                continue
                            aviso=avisos_obscenos.get(nl,0)+1
                            avisos_obscenos[nl]=aviso
                            if aviso==1:
                                enviar(s,f"PRIVMSG {CANAL} :⚠️ {nuevo} nick con '{pal}' no permitido Aviso 1/2")
                                threading.Timer(30, lambda: check_obsceno(s,nuevo,2)).start()
                            elif aviso==2:
                                enviar(s,f"PRIVMSG {CANAL} :⚠️ {nuevo} SEGUNDO AVISO '{pal}' 2/2")
                                threading.Timer(30, lambda: check_obsceno(s,nuevo,3)).start()
                            continue
                        entregar(s,nuevo)
                        if nuevo.lower() in akick_lista:
                            enviar(s,f"MODE {CANAL} +b {nuevo}!*@*")
                            time.sleep(0.5)
                            enviar(s,f"KICK {CANAL} {nuevo} :AKICK")
                            continue
                        time.sleep(1.2)
                        enviar(s,f"PRIVMSG {CANAL} :Bienvenido/a a Continentes, pásalo bien {nuevo} 🎉")
                    except: pass

                # PRIVADO -> SALA
                if f"PRIVMSG {NICK} :" in l and "services@services.chat" not in l and ":NiCK!" not in l:
                    try:
                        nick=l.split("!")[0][1:]
                        msg_priv=limpiar_msg(l.split(f"PRIVMSG {NICK} :")[1])
                        if es_op(nick) or es_perma(nick):
                            if not msg_priv: continue
                            if msg_priv.startswith("#"):
                                partes=msg_priv.split(" ",1)
                                canal_dest=partes[0]
                                texto=partes[1] if len(partes)>1 else ""
                                if texto:
                                    enviar(s,f"PRIVMSG {canal_dest} :{texto}")
                                    enviar(s,f"PRIVMSG {nick} :✅ Enviado a {canal_dest}")
                            else:
                                enviar(s,f"PRIVMSG {CANAL} :{msg_priv}")
                                enviar(s,f"PRIVMSG {nick} :✅ Enviado a {CANAL}")
                    except: pass

                if f"PRIVMSG {CANAL} :" in l:
                    try:
                        nick=l.split("!")[0][1:]
                        raw=l.split(f"PRIVMSG {CANAL} :")[1]
                        msg=limpiar_msg(raw)
                    except: continue
                    if "services@services.chat" in l: continue
                    try: entregar(s,nick)
                    except: pass

                    if trivia_actual:
                        rl=msg.lower().strip()
                        if rl==trivia_actual["r"] or rl==trivia_actual["a"] or trivia_actual["a"] in rl:
                            enviar(s,f"PRIVMSG {CANAL} :🎉 ¡{nick} acertó! Era {trivia_actual['a'].upper()}")
                            trivia_puntos[nick]=trivia_puntos.get(nick,0)+1
                            trivia_actual=None
                            continue

                    low=msg.lower()
                    if low.startswith("!trivia"):
                        trivia_actual=random.choice(TRIVIAS)
                        enviar(s,f"PRIVMSG {CANAL} :🧠 {trivia_actual['q']} | {trivia_actual['op']}")
                        continue
                    if low.startswith("!rankingtrivia"):
                        if not trivia_puntos: enviar(s,f"PRIVMSG {CANAL} :Aún sin puntos")
                        else:
                            top=sorted(trivia_puntos.items(), key=lambda x:x[1], reverse=True)[:5]
                            txt=", ".join([f"{n}({p})" for n,p in top])
                            enviar(s,f"PRIVMSG {CANAL} :🏆 Ranking: {txt}")
                        continue
                    if low.startswith("!ia ") or low.startswith("!ai ") or low.startswith("!gemini "):
                        pregunta=msg.split(" ",1)[1] if " " in msg else ""
                        if pregunta:
                            enviar(s,f"PRIVMSG {CANAL} :🤖 Pensando...")
                            enviar(s,f"PRIVMSG {CANAL} :🤖 {nick}: {get_ia(pregunta)}")
                        continue
                    if low.strip()=="!ia" or low.strip()=="!ai" or low.strip()=="!gemini":
                        enviar(s,f"PRIVMSG {CANAL} :Usa:!ia <pregunta> Ej:!ia que es un agujero negro?")
                        continue
                    if low.startswith("!yt "):
                        res=buscar_yt(msg[4:].strip())
                        if res: enviar(s,f"PRIVMSG {CANAL} :🎵 {res}")
                        continue
                    if low.startswith("!tiempo "):
                        res=get_tiempo(msg[8:].strip())
                        enviar(s,f"PRIVMSG {CANAL} :{res if res else 'No encuentro esa ciudad'}")
                        continue
                    if low.startswith("!horoscopo "):
                        arg=msg[11:].strip().split()[0]
                        res=get_horoscopo(arg)
                        enviar(s,f"PRIVMSG {CANAL} :{res[:380] if res else 'Signo no válido. aries tauro geminis cancer leo virgo libra escorpio sagitario capricornio acuario piscis'}")
                        continue
                    if low.startswith("!dejar ") or low.startswith("!decir "):
                        try:
                            resto=msg[7:].strip()
                            partes=resto.split(" ",1)
                            if len(partes)>=2:
                                dest=limpiar_nick(partes[0])
                                fecha=time.strftime("%d/%m %H:%M")
                                if dest not in mensajes_pendientes: mensajes_pendientes[dest]=[]
                                mensajes_pendientes[dest].append({"de":nick,"msg":partes[1],"fecha":fecha})
                                guardar_mensajes(mensajes_pendientes)
                                enviar(s,f"PRIVMSG {CANAL} :✅ Recado para {partes[0]} guardado")
                        except: pass
                        continue

                    # PERMAS
                    if es_perma(nick):
                        if low.startswith("!recados"):
                            if not mensajes_pendientes: enviar(s,f"PRIVMSG {CANAL} :No hay recados pendientes")
                            else:
                                resumen=", ".join([f"{k}({len(v)})" for k,v in mensajes_pendientes.items()])
                                enviar(s,f"PRIVMSG {CANAL} :📩 Pendientes: {resumen}")
                            continue
                        if low.startswith("!addobsceno "):
                            pal=msg.split(" ",1)[1].strip().lower()
                            PALABRAS_OBSCENAS.add(pal)
                            guardar_obscenas(PALABRAS_OBSCENAS)
                            enviar(s,f"PRIVMSG {CANAL} :✅ Añadida obscena: {pal} Total:{len(PALABRAS_OBSCENAS)}")
                            continue
                        if low.startswith("!delobsceno "):
                            pal=msg.split(" ",1)[1].strip().lower()
                            PALABRAS_OBSCENAS.discard(pal)
                            guardar_obscenas(PALABRAS_OBSCENAS)
                            enviar(s,f"PRIVMSG {CANAL} :✅ Eliminada: {pal}")
                            continue
                        if low.startswith("!listobsceno"):
                            lista=", ".join(sorted(PALABRAS_OBSCENAS))
                            enviar(s,f"PRIVMSG {CANAL} :🚫 ({len(PALABRAS_OBSCENAS)}): {lista[:350]}")
                            continue

                    # OPS
                    if es_op(nick):
                        if low.startswith("!say "):
                            enviar(s,f"PRIVMSG {CANAL} :{msg[5:].strip()}")
                            continue
                        if low.startswith("!kick "):
                            try:
                                p=msg.split(" ",2)
                                v=p[1]
                                r=p[2] if len(p)>2 else f"Por {nick}"
                                enviar(s,f"KICK {CANAL} {v} :{r}")
                            except: pass
                            continue
                        if low.startswith("!kb "):
                            try:
                                p=msg.split(" ",2)
                                v=p[1]
                                r=p[2] if len(p)>2 else f"Por {nick}"
                                enviar(s,f"MODE {CANAL} +b {v}!*@*")
                                time.sleep(0.5)
                                enviar(s,f"KICK {CANAL} {v} :{r}")
                            except: pass
                            continue
                        if low.startswith("!ban "):
                            try: enviar(s,f"MODE {CANAL} +b {msg.split()[1]}!*@*")
                            except: pass
                            continue
                        if low.startswith("!unban "):
                            try: enviar(s,f"MODE {CANAL} -b {msg.split()[1]}!*@*")
                            except: pass
                            continue
                        if low.startswith("!voice "):
                            try: enviar(s,f"MODE {CANAL} +v {msg.split()[1]}")
                            except: pass
                            continue
                        if low.startswith("!devoice "):
                            try: enviar(s,f"MODE {CANAL} -v {msg.split()[1]}")
                            except: pass
                            continue
                        if low=="!voice":
                            try: enviar(s,f"MODE {CANAL} +v {nick}")
                            except: pass
                            continue
                        if low.startswith("!op"):
                            try:
                                partes=msg.split()
                                if len(partes)==1: enviar(s,f"MODE {CANAL} +o {nick}")
                                else: enviar(s,f"MODE {CANAL} +o {partes[1]}")
                            except: pass
                            continue
                        if low.startswith("!deop "):
                            try: enviar(s,f"MODE {CANAL} -o {msg.split()[1]}")
                            except: pass
                            continue
                        if low.startswith("!akick "):
                            try:
                                arg=msg.split()[1].lower()
                                if arg=="list":
                                    lista=", ".join(akick_lista) if akick_lista else "vacía"
                                    enviar(s,f"PRIVMSG {CANAL} :AKICK: {lista}")
                                elif arg in ["del","rem","remove"]:
                                    v=msg.split()[2].lower()
                                    if v in akick_lista:
                                        akick_lista.discard(v)
                                        guardar_akick(akick_lista)
                                        enviar(s,f"PRIVMSG {CANAL} :AKICK {v} eliminado")
                                else:
                                    v=arg
                                    akick_lista.add(v)
                                    guardar_akick(akick_lista)
                                    enviar(s,f"PRIVMSG {CANAL} :AKICK {v} añadido")
                            except: pass
                            continue
                    #!seen prohibido
                    if "!seen" in low and not es_op(nick):
                        enviar(s,f"MODE {CANAL} +b {nick}!*@*")
                        time.sleep(0.5)
                        enviar(s,f"KICK {CANAL} {nick} :!seen no permitido")
                        continue

                if " 353 " in l and CANAL in l:
                    try:
                        parte=l.split(" :")[-1]
                        for u in parte.split():
                            if u[0] in "@%~&": ops.add(limpiar_nick(u))
                    except: pass
                if f" MODE {CANAL} +o " in l:
                    try: ops.add(limpiar_nick(l.split()[-1]))
                    except: pass
                if f" MODE {CANAL} -o " in l:
                    try: ops.discard(limpiar_nick(l.split()[-1]))
                    except: pass
    except Exception as e:
        print("Error:",e)
        time.sleep(5)
