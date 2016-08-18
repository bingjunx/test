#encoding=utf-8
from connection import JR


def ops_tickets(assignees=[]):
    jql = u'project = HELPDESK AND issuetype = zabbix告警 AND status in ("In Progress", "To Do") AND 告警负责人 ~ devopsgroups'
    if assignees:
        jql += u' AND assignee in ("%s")' % '","'.join(assignees)

    issues = JR.search_issues(jql_str=jql)
    return issues
