from flask import Flask,render_template,request #,redirect
import sqlite3
import re
import copy
#import json


all_points = ('0-0', '0-15', '0-30', '0-40', '15-0', '15-15', '15-30', '15-40', '30-0',
              '30-15', '30-30', '30-40', '40-0', '40-15', '40-30', '40-40', 'AD-40', '40-AD')
all_bp = ('0-40', '15-40', '30-40', '40-AD')
single_bp = ('30-40', '40-AD')
multi_bp = ('0-40', '15-40')


class AllServes:
    def __init__(self, scaffold):
        self.scores = {'4': 0, '5': 0, '6': 0}
        self.scaffold = scaffold
        self.pts = {i: copy.deepcopy(self.scores) for i in self.scaffold}


class RetDir:
    def __init__(self):
        self.ret = {1: 0, 2: 0, 3: 0}


class ServDir:
    def __init__(self):
        self.dir = [4, 5, 6]
        self.srv = {i: RetDir() for i in self.dir}


class AllReturns:
    def __init__(self, scaffold):
        self.scaffold = scaffold
        self.pts = {i: ServDir() for i in self.scaffold}

    def __str__(self):
        bp = ''
        for i in self.pts:
            bp += '{0:5s}: '.format(i)
            for j in self.pts[i].srv:
                bp += '  {}- '.format(j)
                for k in self.pts[i].srv[j].ret:
                    bp += '{0}:{1:<4} '.format(k, self.pts[i].srv[j].ret[k])
            bp += '\n'
        return bp


def player_name_initials(_player):
    ini_exp = '^([A-Z]).+\s([A-Z])'
    ini_grp = re.findall(ini_exp, _player)
    initials = ''
    for i in ini_grp[0]:
        initials = initials+i
    criteria = (_player, _player, initials)
    return criteria


def get_query(_query, query_list):
    conn = sqlite3.connect(sqldb_path)
    c = conn.cursor()
    c.execute(_query, query_list)

    _subq = c.fetchall()
    conn.close()
    return _subq


def serves_by_location(_fs, _ss):
    # All first and second serves compiled by location
    fs_t = {'4': 0, '5': 0, '6': 0}
    for i, j in _fs.items():
        for k in j:
            fs_t[k] += j[k]

    ss_t = {'4': 0, '5': 0, '6': 0}
    for i, j in _ss.items():
        for k in j:
            ss_t[k] += j[k]

    total_fs = sum(fs_t.values())
    total_ss = sum(ss_t.values())

    fs_p, ss_p, as_p = {}, {}, {}  # first serve percentages by position

    for i in fs_t:
        fs_p[i] = fs_t[i]/total_fs
    for i in ss_t:
        ss_p[i] = ss_t[i]/total_ss

    for i, j in zip(fs_t, ss_t):
        as_p[i] = (fs_t[i]+ss_t[i]) / (total_ss + total_fs)

    fs_p = rename_num_to_pos(fs_p)
    ss_p = rename_num_to_pos(ss_p)
    as_p = rename_num_to_pos(as_p)

    return fs_p, ss_p, as_p


def rename_num_to_pos(di):
    di['Wide'] = di.pop('4')
    di['Body'] = di.pop('5')
    di['Down T'] = di.pop('6')
    return di


def single_break_points(_fs, _ss):
    bpfs = {'30-40':{}, '40-AD':{}}
    bpss = {'30-40': {}, '40-AD': {}}
    for i in _fs:
        if i in bpfs:
            bpfs[i] = _fs[i]
    for i in _ss:
        if i in bpfs:
            bpss[i] = _ss[i]

    _sbp_srv1p, _sbp_srv2p, _sbp_srvp = serves_by_location(bpfs,bpss)

    return _sbp_srv1p, _sbp_srv2p, _sbp_srvp


def multi_break_points(_fs, _ss):
    bpfs = {'0-40': {}, '15-40': {}}
    bpss = {'0-40': {}, '15-40': {}}
    for i in _fs:
        if i in bpfs:
            bpfs[i] = _fs[i]
    for i in _ss:
        if i in bpfs:
            bpss[i] = _ss[i]

    _mbp_srv1p, _mbp_srv2p, _mbp_srvp = serves_by_location(bpfs,bpss)

    return _mbp_srv1p, _mbp_srv2p, _mbp_srvp


def ret_serves(_player):
    ql = player_name_initials(_player)  # query list
    qry = 'SELECT serving, pts, first, second FROM all_points WHERE (player1 = ? OR player2 = ?) AND serving = ?;'
    subq = get_query(qry, ql)

    fs = AllServes(all_points)
    ss = AllServes(all_points)

    # all first and second serves compiled by score
    # the extra conditions are due to dirty data
    # sometimes the scores are wrong (e.g. 2-1 instead of 30-40)
    # or the directions are wrong (not 4,5,6)
    for i in subq:
        if i[2] and (i[1] in fs.pts) and (i[2][0] in fs.pts[i[1]]):
            fs.pts[i[1]][i[2][0]] += 1
        if i[3] and (i[1] in ss.pts) and (i[3][0] in ss.pts[i[1]]):
            ss.pts[i[1]][i[3][0]] += 1
        # else:
        #   add a dictionary to catch all the skipped rows

    # for i, j in zip(fs.pts, ss.pts):
    #     print(i, fs.pts[i], ss.pts[j])

    all_srv1p, all_srv2p, all_srvp = serves_by_location(fs.pts, ss.pts)
    sbp_srv1p, sbp_srv2p, sbp_srvp = single_break_points(fs.pts, ss.pts)
    mbp_srv1p, mbp_srv2p, mbp_srvp = multi_break_points(fs.pts, ss.pts)

    _compiled_serves = {'all_serves': {'srv1': all_srv1p, 'srv2': all_srv2p, 'all': all_srvp},
                       'sbp_serves': {'srv1': sbp_srv1p, 'srv2': sbp_srv2p, 'all': sbp_srvp},
                       'mbp_serves': {'srv1': mbp_srv1p, 'srv2': mbp_srv2p, 'all': mbp_srvp}}

    return _compiled_serves


app_tennis = Flask(__name__)

app_tennis.vars = {}

sqldb_path = 'tmcp.db'

@app_tennis.route('/', methods=['GET', 'POST'])
def index_tennis():

    if request.method == 'GET':
        return render_template('index_form.html')
    else:
        # Request was a POST
        #print(request.form)
        player = request.form['player_name']
        compiled_serves = ret_serves(player)

        as1w = round(100 * compiled_serves['all_serves']['srv1']['Wide'])
        as1b = round(100 * compiled_serves['all_serves']['srv1']['Body'])
        as1t = round(100 * compiled_serves['all_serves']['srv1']['Down T'])

        ss1w = round(100 * compiled_serves['sbp_serves']['srv1']['Wide'])
        ss1b = round(100 * compiled_serves['sbp_serves']['srv1']['Body'])
        ss1t = round(100 * compiled_serves['sbp_serves']['srv1']['Down T'])

        ms1w = round(100 * compiled_serves['mbp_serves']['srv1']['Wide'])
        ms1b = round(100 * compiled_serves['mbp_serves']['srv1']['Body'])
        ms1t = round(100 * compiled_serves['mbp_serves']['srv1']['Down T'])

        as2w = round(100 * compiled_serves['all_serves']['srv2']['Wide'])
        as2b = round(100 * compiled_serves['all_serves']['srv2']['Body'])
        as2t = round(100 * compiled_serves['all_serves']['srv2']['Down T'])

        ss2w = round(100 * compiled_serves['sbp_serves']['srv2']['Wide'])
        ss2b = round(100 * compiled_serves['sbp_serves']['srv2']['Body'])
        ss2t = round(100 * compiled_serves['sbp_serves']['srv2']['Down T'])

        ms2w = round(100 * compiled_serves['mbp_serves']['srv2']['Wide'])
        ms2b = round(100 * compiled_serves['mbp_serves']['srv2']['Body'])
        ms2t = round(100 * compiled_serves['mbp_serves']['srv2']['Down T'])

        asaw = round(100 * compiled_serves['all_serves']['all']['Wide'])
        asab = round(100 * compiled_serves['all_serves']['all']['Body'])
        asat = round(100 * compiled_serves['all_serves']['all']['Down T'])

        #return redirect('/index_quand')
        return render_template('chart_out_all.html',
                               pname = player,
                               a1w=as1w, a1b=as1b, a1t=as1t,
                               s1w=ss1w, s1b=ss1b, s1t=ss1t,
                               m1w=ms1w, m1b=ms1b, m1t=ms1t,
                               a2w=as2w, a2b=as2b, a2t=as2t,
                               s2w=ss2w, s2b=ss2b, s2t=ss2t,
                               m2w=ms2w, m2b=ms2b, m2t=ms2t,
                               aaw=asaw, aab=asab, aat=asat )



if __name__ == "__main__":
    app_tennis.run()