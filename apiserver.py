import flask
from flask import jsonify, request
from pyaspeller import YandexSpeller
import pymorphy2
import random
import time
import requests
from bs4 import BeautifulSoup
import sqlite3 as sl
from Levenshtein import ratio
morph = pymorphy2.MorphAnalyzer()


blueprint = flask.Blueprint(
    'bot_api',
    __name__,
    template_folder='templates'
)


@blueprint.route('/api/bot/<msg>', methods=['GET'])
def answer(msg):
    t = ['запусти сделай команда',
        'включить посмотреть рекомендация совет хочу смотреть',
         'как почему не работает сколько зачем плохо']
    speller = YandexSpeller()
    query = clear(speller.spelled(msg))
    syn_list = [parse_synonyms(word) for word in query]

    def accuracy(s):
        s = clear(s)
        acc = 0
        for el in syn_list:
            mx = 0
            for s1 in el:
                for s2 in s:
                    mx = max(mx, ratio(s1,s2))
            acc += mx
        if len(syn_list) == 0:
            return 1
        return acc / len(syn_list)

    select_type = [[i,t[i]] for i in range(len(t))]
    select_type = [(accuracy(x[1]), x) for x in select_type]
    select_type.sort(reverse=True)

    #print(select_type)
    type = select_type[0][1][0]
    #print(type)

    cmds = ['Поставить на паузу',
            'Включить песню',
            'Включить фильм',
            'Включить телевизор',
            'Купить фильм',
            'Мои фильмы']



    con = sl.connect('db.db')
    cur = con.cursor()
    films = cur.execute("SELECT * FROM ITEMS").fetchall()
    films = [[x[0], x[1] + "\n" + x[2] + "\n" + x[3]] for x in films]



    def parse_faq():
        f = open('parse.txt', 'r', encoding='utf8')
        lines = f.readlines()
        html_selected = [lines[2 * i + 2].rstrip('\n') for i in range(18)]
        f.close()

        faq_list = []
        for selected in range(18):
            for i in range(300):
                tmp = html_selected[selected].find(f'"/faq/{i}"')
                tmp2 = html_selected[selected].find('root_r1lbxtse title_t1mrmeg6 root_header1_r1et8e7w')
                if tmp != -1:
                    S = html_selected[selected][tmp + 15:tmp + 200]
                    L = S.find('>')
                    R = S.find('<')
                    S2 = html_selected[selected][tmp2:tmp2 + 200]
                    L2 = S2.find('>')
                    R2 = S2.find('<')
                    faq_list.append([selected, i, S2[L2 + 1:R2] + ': ' + S[L + 1:R]])
        faq_list.sort()
        return faq_list
    faq_list = parse_faq()

    MERGED = [[],[],[]]
    for i in range(len(cmds)):
        MERGED[0].append([i, cmds[i]])
    for i in range(len(films)):
        MERGED[1].append([films[i][0], f"https://wink.ru/media_items/{films[i][0]}\n\n" + films[i][1]])
    for i in range(len(faq_list)):
        MERGED[2].append([(faq_list[i][0], faq_list[i][1]), f"https://wink.ru/faq/{faq_list[i][1]}\n\n" + faq_list[i][2]])




    for i in range(len(MERGED)):
        if (i != type):
            continue
        MERGED[i] = [(accuracy(x[1]), x) for x in MERGED[i]]
        MERGED[i].sort(reverse=True)
    #print(*MERGED[type][:5], sep='\n')
    res = MERGED[type][0][1][1]
    if len(res) > 200:
        res = res[:197] + "..."
    return res



def clear(q):
    q = list(q.lower())
    for i in range(len(q)):
        if (not q[i].isalpha()):
            q[i] = ' '
    q = ''.join(q)
    q = q.split()

    res = []
    for i in range(len(q)):
        if (q[i] == 'не') and (i < len(q) - 1):
            q[i + 1] = 'не' + ' ' + q[i + 1]
            continue

        p = morph.parse(q[i])[0]
        DELETE = ['PREP', 'CONJ', 'INTJ']
        DELETE = []
        if all(d != p.tag.POS for d in DELETE):
            res.append(p.normal_form)
    return res

def parse_url(url):
    time.sleep(0.5)
    head = [
        'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.59 Safari/537.36 115Browser/8.3.0',
        'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.59 Safari/537.36 115Browser/8.6.2',
        'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML like Gecko) Chrome/31.0.1650.63 Safari/537.36 115Browser/5.2.6',
        'Mozilla/5.0 (X11; U; Linux i686 (x86_64); en-US; rv:1.8.1.11) Gecko/20080109 (Charlotte/0.9t; http://www.searchme.com/support/)']
    headers = {
        'User-Agent': random.choice(head)}
    response = requests.get(url, headers=headers)

    r = response.text
    r = r.replace('\x00', '')

    bs = BeautifulSoup(r, "lxml")
    return bs

def parse_synonyms(word):
    url = f'https://synonyms.su/{word[0].lower()}/{word.lower()}'
    bs = parse_url(url)
    syn = [x.previous_element.get_text() for x in bs.find_all(class_='synnumber')]
    return [word] + syn[:5]