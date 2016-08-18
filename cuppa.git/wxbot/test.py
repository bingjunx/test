#encoding=utf-8
import re, json, requests, HTMLParser, logging, pprint, locale
from requests.exceptions import ConnectionError, ReadTimeout
from bot import WXBot
from config import conf
#from jirahelper import searcher

logger = logging.getLogger('wxbot')
default_encoding = locale.getdefaultlocale()[1]

class MyWXBot(WXBot):

    def handle_msg(self, r):
        """
        The inner function that processes raw WeChat messages.
        :param r: The raw data of the messages.
        :return: None

        """
        for msg in r['AddMsgList']:
            content = HTMLParser.HTMLParser().unescape(msg['Content'])
            logger.info('MsgType: %s Content %s' % (msg['MsgType'], content))

            user = None
            group = None

            if msg['MsgType'] == 1: # text
               # import pdb;pdb.set_trace()
                #if msg.get('FromUserName'):
                #    self.send_msg_by_uid('12323123', msg['FromUserName'])
                if msg['FromUserName'].startswith('@@'):
                    group = msg['FromUserName']
                    try:
                        user, content = content.split(':<br/>', 1)
                    except:
                        pprint.pprint(msg)
                        print u'cannot find :<br/> in msg content "%s"' % content

                elif msg['ToUserName'].startswith('@@'):
                    group = msg['ToUserName']
                    user = msg['FromUserName']

            else:
                print msg['MsgType'], content.encode(default_encoding, 'ignore')

            if group:
                self.handle_group_msg(content, user, group, msg)

    def handle_group_msg(self, content, user, group, msg):
        print self.get_contact_name(group)

        sender_name = self.get_contact_name(user)
        print 'from %s: %s' % (sender_name.encode(default_encoding, 'ignore'), content.encode(default_encoding, 'ignore'))


        if content.startswith(('%', u'\uff01')):
            content = content[1:].strip()

            if content.startswith('help'):
                resp = (u'\n'
                        u'输入“！i”为您查询当前所有未关闭问题\n'
                        u'输入“！id”为！i的详情模式\n'
                        u'输入“！其它”和机器人聊天\n'
                        u'输入“@包涵”寻求帮助\n')
            else:
                if content.startswith('i'):
                    resp = '\n' + self.search_ops_tickets(content[1:])
                    print resp
                else:
                    resp = self.tuling_auto_reply(user, content)

            if resp:
                prefix = u'@%s\u2005' % sender_name
                self.send_msg_by_uid(prefix + resp, group)

    '''def search_ops_tickets(self, content):
        if content[:1] == 'd':
            detail_mode = True
            content = content[1:]
        else:
            detail_mode = False

        names = filter(None, re.split(r'[^\w^\.]+', content))
        issues = []
        for issue in searcher.ops_tickets(names):
            issues.append({ 'key': issue.key,
                            'summary': issue.fields.summary,
                            'assignee': issue.fields.assignee.displayName,
                            'server': issue.fields.customfield_12115,
                            'created': issue.fields.created[:-9]})
        issues.sort(key=lambda k: k['assignee'])
        issue_descriptions = []
        if detail_mode:
            current_assignee = None
            for i in issues:
                if i['assignee'] != current_assignee:
                    current_assignee = i['assignee']
                    issue_descriptions.append('==================')
                    issue_descriptions.append(i['assignee'])
                issue_descriptions.append(i['key'])
                issue_descriptions.append(i['summary'])
                issue_descriptions.append(i['server'])
                issue_descriptions.append(i['created'])
                issue_descriptions.append('')
        else:
            for i in issues:
                issue_descriptions.append(u'%s %s' % (i['key'], i['assignee']))
        return '\n'.join(issue_descriptions)
        '''

    def tuling_auto_reply(self, uid, msg):
        if self.conf['tuling_key']:
            body = {'key': self.conf['tuling_key'], 'info': msg.encode('utf8'), 'userid': uid[:32]}
            try:
                r = requests.post(self.conf['tuling_api'], data=body, timeout=5)
            except (ConnectionError, ReadTimeout):
                return None

            respond = json.loads(r.text)
            result = ''
            if respond['code'] == 100000:
                result = respond['text'].replace('<br>', '  ')
            elif respond['code'] == 200000:
                result = respond['url']
            else:
                result = respond['text'].replace('<br>', '  ')

            print '  to', self.get_contact_name(uid), '^ROBOT:', result
            return result
        else:
            return None


def main():
    bot = MyWXBot()
    bot.DEBUG = True
    bot.conf.update(conf)
    bot.run()


if __name__ == '__main__':
    main()

