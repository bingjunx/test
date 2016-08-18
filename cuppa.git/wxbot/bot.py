#encoding=utf-8
import os, sys, json, time, datetime, re, random
import xml.dom.minidom, HTMLParser
import webbrowser, pyqrcode
import urllib, requests
from requests.exceptions import ConnectionError, ReadTimeout


def show_image(file):
    if sys.version_info >= (3, 3):
        from shlex import quote
    else:
        from pipes import quote

    if sys.platform == "win32":
        webbrowser.open(file)
    elif sys.platform == "darwin":
        def get_command(file, **options):
            command = "open -a /Applications/Preview.app"
            command = "(%s %s)&" % (command, quote(file))
            return command

        os.system(get_command(file))

class WXBot(object):
    """WXBot, a framework to process WeChat messages"""

    def __init__(self):
        self.DEBUG = False
        self.uuid = ''
        self.base_uri = ''
        self.redirect_uri = ''
        self.uin = ''
        self.sid = ''
        self.skey = ''
        self.pass_ticket = ''
        self.device_id = 'e' + repr(random.random())[2:17]
        self.base_request = {}
        self.sync_key_str = ''
        self.sync_key = []
        self.sync_host = ''

        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Linux i686; U;) Gecko/20070322 Kazehakase/0.4.5'})
        self.conf = {'qr_file_path': 'qr.png'}

        self.contacts = {}

    def run(self):
        self.get_uuid()
        self.gen_qr_code()
        self.scan_qr()
        self.login()
        self.init()
        self.status_notify()
        self.get_contact()
        print '[INFO] Get %d contacts' % len(self.contacts)
        print '[INFO] Start to process messages '
        self.proc_msg()

    def update_contact(self, contact, username=None):
        username = username or contact['UserName']
        if self.contacts.has_key(username):
            self.contacts[username].update(contact)
        else:
            self.contacts[username] = contact

    def get_contact_name(self, username):
        try:
            contact = self.contacts[username]
            return contact.get('NickName') or username
        except:
            return username

    def get_uuid(self):
        url = 'https://login.weixin.qq.com/jslogin'
        params = {
            'appid': 'wx782c26e4c19acffb',
            'fun': 'new',
            'lang': 'zh_CN',
            '_': int(time.time()) * 1000 + random.randint(1, 999),
        }
        r = self.session.get(url, params=params)
        r.encoding = 'utf-8'
        data = r.text
        regx = r'window.QRLogin.code = (\d+); window.QRLogin.uuid = "(\S+?)"'
        pm = re.search(regx, data)
        if pm:
            code = pm.group(1)
            if code == '200':
                self.uuid = pm.group(2)
                return
        else:
            raise Exception(u'Failed to get uuid from data "%s"' % data)

    def gen_qr_code(self):
        qr_string = 'https://login.weixin.qq.com/l/' + self.uuid

        qr = pyqrcode.create(qr_string)
        qr.png(self.conf['qr_file_path'], scale=8)
        print '[INFO] Please use WeChat to scan the QR code .'
        show_image(self.conf['qr_file_path'])

    def scan_qr(self):
        '''
        url params and response codes:
        tip=1, the request wait for user to scan the qr,
               201: scaned
               408: timeout
        tip=0, the request wait for user confirm,
               200: confirmed
        '''
        UNKONWN = 'unkonwn'
        SUCCESS = '200'
        SCANED  = '201'
        TIMEOUT = '408'

        LOGIN_TEMPLATE = 'https://login.weixin.qq.com/cgi-bin/mmwebwx-bin/login?tip=%s&uuid=%s&_=%s'
        tip = 1

        MAX_RETRY_TIMES = 10
        RETRY_WAIT_SECS = 1

        code = UNKONWN

        retry_count = 0
        while retry_count < MAX_RETRY_TIMES:
            url = LOGIN_TEMPLATE % (tip, self.uuid, int(time.time()))
            r = self.session.get(url)
            r.encoding = 'utf-8'
            data = r.text
            param = re.search(r'window.code=(\d+);', data)
            code = param.group(1)

            if code == SCANED:
                print '[INFO] Please confirm to login .'
                tip = 0

            elif code == SUCCESS: #confirmed sucess
                param = re.search(r'window.redirect_uri="(\S+?)";', data)
                if param:
                    redirect_uri = param.group(1)
                    if len(redirect_uri) < 4:
                        raise Exception(u'redirect_uri "%s" is too short' % redirect_uri)

                    self.redirect_uri = redirect_uri + '&fun=new'
                    self.base_uri = redirect_uri[:redirect_uri.rfind('/')]
                    break
                else:
                    raise Exception(u'Failed to get redirect_uri from response "%s"' % data)

            elif code == TIMEOUT:
                print '[ERROR] WeChat login timeout. retry in %s secs later...'%(RETRY_WAIT_SECS, )
                tip = 1 #need to reset tip, because the server will reset the peer connection
                retry_count += 1
                time.sleep(RETRY_WAIT_SECS)

            else:
                print ('[ERROR] WeChat login exception return_code=%s. retry in %s secs later...' %
                        (code, RETRY_WAIT_SECS))
                tip = 1
                retry_count += 1
                time.sleep(RETRY_WAIT_SECS)

        if code != SUCCESS:
            raise Exception(u'Failed to scan qr')

    def login(self):
        r = self.session.get(self.redirect_uri)
        r.encoding = 'utf-8'
        data = r.text
        doc = xml.dom.minidom.parseString(data)
        root = doc.documentElement

        for node in root.childNodes:
            if node.nodeName == 'skey':
                self.skey = node.childNodes[0].data
            elif node.nodeName == 'wxsid':
                self.sid = node.childNodes[0].data
            elif node.nodeName == 'wxuin':
                self.uin = node.childNodes[0].data
            elif node.nodeName == 'pass_ticket':
                self.pass_ticket = node.childNodes[0].data

        if '' in (self.skey, self.sid, self.uin, self.pass_ticket):
            raise Exception(u'Invalid login response data "data"' % data)

        self.base_request = {
            'Uin': self.uin,
            'Sid': self.sid,
            'Skey': self.skey,
            'DeviceID': self.device_id,
        }

    def init(self):
        url = self.base_uri + '/webwxinit?r=%i&lang=en_US&pass_ticket=%s' % (int(time.time()), self.pass_ticket)
        params = {
            'BaseRequest': self.base_request
        }
        r = self.session.post(url, data=json.dumps(params))
        r.encoding = 'utf-8'
        dic = json.loads(r.text)
        if dic['BaseResponse']['Ret'] != 0:
            raise Exception(u'Invalid init response data "%s"' % dic['BaseResponse'])

        self.sync_key = dic['SyncKey']
        self.sync_key_str = '|'.join([str(keyVal['Key']) + '_' + str(keyVal['Val'])
                                      for keyVal in self.sync_key['List']])

        self.contacts['self'] = dic['User']
        self.update_contact(dic['User'])
        for contact in dic['ContactList']:
            self.update_contact(contact)

    def status_notify(self):
        url = self.base_uri + '/webwxstatusnotify?lang=zh_CN&pass_ticket=%s' % self.pass_ticket
        self.base_request['Uin'] = int(self.base_request['Uin'])
        params = {
            'BaseRequest': self.base_request,
            "Code": 3,
            "FromUserName": self.contacts['self']['UserName'],
            "ToUserName": self.contacts['self']['UserName'],
            "ClientMsgId": int(time.time())
        }
        r = self.session.post(url, data=json.dumps(params))
        r.encoding = 'utf-8'
        dic = json.loads(r.text)
        if dic['BaseResponse']['Ret'] != 0:
            raise Exception(u'Invalid statusnotify response data "%s"' % dic['BaseResponse'])

    def get_contact(self):
        """Get information of all contacts of current account."""
        url = self.base_uri + '/webwxgetcontact?pass_ticket=%s&skey=%s&r=%s' \
                              % (self.pass_ticket, self.skey, int(time.time()))
        r = self.session.post(url, data='{}')
        r.encoding = 'utf-8'
        dic = json.loads(r.text)
        if dic['BaseResponse']['Ret'] != 0:
            raise Exception(u'Invalid getcontact response data "%s"' % dic['BaseResponse'])
        for contact in dic['MemberList']:
            self.update_contact(contact)

    def proc_msg(self):
        if not self.test_sync_check():
            raise Exception(u'Failed to synccheck')

        passed_checks = 0
        while True:
            [retcode, selector] = self.sync_check()
            if retcode == '1100':  # logout from mobile
                break
            elif retcode == '1101':  # login web WeChat from other devide
                break
            elif retcode == '0':
                sys.stdout.write(selector)
                if int(selector) > 0:  # new message
                    r = self.sync()
                    if r is not None:
                        self.handle_msg(r)
                else:
                    passed_checks += 1
                    if passed_checks > 10:
                        r = self.sync()
                        passed_checks = 0


            time.sleep(1)

    def test_sync_check(self):
        for host in ['webpush', 'webpush2']:
            self.sync_host = host
            retcode = self.sync_check()[0]
            if retcode == '0':
                return True
        return False

    def sync_check(self):
        sys.stdout.write('.')
        params = {
            'r': int(time.time()),
            'sid': self.sid,
            'uin': self.uin,
            'skey': self.skey,
            'deviceid': self.device_id,
            'synckey': self.sync_key_str,
            '_': int(time.time()),
        }
        url = 'https://' + self.sync_host + '.weixin.qq.com/cgi-bin/mmwebwx-bin/synccheck?' + urllib.urlencode(params)
        try:
            r = self.session.get(url, timeout=60)
        except (ConnectionError, ReadTimeout):
            return [-1, -1]
        r.encoding = 'utf-8'
        data = r.text
        pm = re.search(r'window.synccheck=\{retcode:"(\d+)",selector:"(\d+)"\}', data)
        retcode = pm.group(1)
        selector = pm.group(2)
        return [retcode, selector]

    def sync(self):
        print 'sync', datetime.datetime.now()
        url = self.base_uri + '/webwxsync?sid=%s&skey=%s&lang=en_US&pass_ticket=%s' % (self.sid, self.skey, self.pass_ticket)
        params = {
            'BaseRequest': self.base_request,
            'SyncKey': self.sync_key,
            'rr': ~int(time.time())
        }
        try:
            r = self.session.post(url, data=json.dumps(params), timeout=60)
        except (ConnectionError, ReadTimeout):
            return None
        r.encoding = 'utf-8'
        dic = json.loads(r.text)
        if dic['BaseResponse']['Ret'] != 0:
            raise Exception(u'Invalid sync response data "%s"' % dic['BaseResponse'])

        self.sync_key = dic['SyncKey']
        self.sync_key_str = '|'.join([str(keyVal['Key']) + '_' + str(keyVal['Val'])
                                      for keyVal in self.sync_key['List']])
        return dic

    def handle_msg(self, r):
        pass

    def send_msg_by_uid(self, word, dst='filehelper'):
        url = self.base_uri + '/webwxsendmsg?pass_ticket=%s' % self.pass_ticket
        msg_id = str(int(time.time() * 1000)) + str(random.random())[:5].replace('.', '')
        if type(word) == 'str':
            word = word.decode('utf-8')
        params = {
            'BaseRequest': self.base_request,
            'Msg': {
                "Type": 1,
                "Content": word,
                "FromUserName": self.contacts['self']['UserName'],
                "ToUserName": dst,
                "LocalID": msg_id,
                "ClientMsgId": msg_id
            }
        }
        headers = {'content-type': 'application/json; charset=UTF-8'}
        data = json.dumps(params, ensure_ascii=False).encode('utf8')
        try:
            r = self.session.post(url, data=data, headers=headers)
        except (ConnectionError, ReadTimeout):
            return False
        dic = r.json()
        return dic['BaseResponse']['Ret'] == 0
