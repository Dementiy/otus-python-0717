#!/usr/bin/env python
# -*- coding: utf-8 -*-


# log_format ui_short '$remote_addr $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

import gzip
import collections
import re
import json
import os
import argparse


config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log"
}


def xreadlines(log_path):
    if log_path.endswith(".gz"):
        log = gzip.open(log_path, 'rb')
    else:
        log = open(log_path)
    for line in log:
        yield line
    log.close()


def consumer(f):
    def start(*args, **kwargs):
        c = f(*args, **kwargs)
        c.next()
        return c
    return start


def median(nums):
    nums = sorted(nums)
    n = len(nums)
    if n < 1:
        return None
    if n % 2 == 1:
        return nums[n//2]
    else:
        return sum(nums[n//2-1:n//2+1])/2.0


@consumer
def count_stat(target):
    stat = collections.defaultdict(list)
    while True:
        r = (yield)
        if r is None:
            break
        stat[r['request']].append(r['request_time'])

    total_count = sum(len(c) for c in stat.values())
    total_time = sum(sum(t) for t in stat.values())
    for url, times in stat.iteritems():
        target.send({
            'url': url,
            'count': len(times),
            'count_perc': round(100 * len(times) / float(total_count), 3),
            'time_avg': round(sum(times) / len(times), 3),
            'time_med': round(median(times), 3),
            'time_max': round(max(times), 3),
            'time_sum': round(sum(times), 3),
            'time_perc': round(100 * sum(times) / total_time, 3)
        })
    target.send(None)


def broadcast(source, consumers):
    for item in source:
        for c in consumers:
            c.send(item)
    for c in consumers:
        try:
            c.send(None)
        except StopIteration:
            pass


def field_map(dictseq, name, func):
    for d in dictseq:
        try:
            d[name] = func(d[name])
            yield d
        except:
            pass


@consumer
def to_report(template, report_path):
    stat = []
    while True:
        line = (yield)
        if line is None:
            break
        stat.append(line)

    with open(template) as f:
        text = f.read()
    text = text.replace('$table_json', json.dumps(stat))

    with open(report_path, "w") as f:
        f.write(text)


@consumer
def to_json(json_path):
    stat = []
    while True:
        line = (yield)
        if line is None:
            break
        stat.append(line)

    with open(json_path, "w") as f:
        f.write(json.dumps(stat))


def log_parser(log_path):
    logpat = re.compile(
        r"(?P<remote_addr>[\d\.]+)\s"
        r"(?P<remote_user>\S*)\s+"
        r"(?P<http_x_real_ip>\S*)\s"
        r"\[(?P<time_local>.*?)\]\s"
        r'"(?P<request>.*?)"\s'
        r"(?P<status>\d+)\s"
        r"(?P<body_bytes_sent>\S*)\s"
        r'"(?P<http_referer>.*?)"\s'
        r'"(?P<http_user_agent>.*?)"\s'
        r'"(?P<http_x_forwarded_for>.*?)"\s'
        r'"(?P<http_X_REQUEST_ID>.*?)"\s'
        r'"(?P<http_X_RB_USER>.*?)"\s'
        r"(?P<request_time>\d+\.\d+)\s*"
    )
    log_lines = xreadlines(log_path)
    log = (logpat.match(line).groupdict() for line in log_lines)
    log = field_map(log, 'request', lambda request: request.split(' ')[1]) # TODO: Fix '0' request
    log = field_map(log, 'request_time', float)
    return log


def main():
    """
    Папки из конфига уже должны быть созданы.
    Подразумевается, что формат логов такой logname-DATE[.gz]

    Варианты запуска:
    $ ./log_analyzer.py
    $ ./log_analyzer.py --log_path path/to/log
    $ ./log_analyzer.py --json
    $ ./log_analyzer.py --log_path path/to/log --json
    """
    parser = argparse.ArgumentParser(description="Process log files.")
    parser.add_argument('--log_path', dest='log_path', help='Path to log file')
    parser.add_argument('--json', action='store_true', default=False, help="Save data to JSON")
    args = parser.parse_args()

    # Находим последний лог-файл
    if args.log_path:
        log_path = args.log_path
    else:
        logs = [os.path.join(config["LOG_DIR"], logfile) for logfile in os.listdir(config['LOG_DIR'])]
        log_path = max(logs, key=os.path.getctime)

    # Проверяем существует ли отчет для лога (по дате в имени)
    date_pat = re.compile("([0-9]{4}\.*[0-9]{2}\.*[0-9]{2})")
    log_date = date_pat.search(log_path).group()
    log_date = log_date[:4] + "." + log_date[4:6] + "." + log_date[6:]
    reports = [report for report in os.listdir(config["REPORT_DIR"]) if report.endswith('.html')]
    for report in reports:
        try:
            if log_date == date_pat.search(report).group():
                print "Report already exists: ", report
                return
        except AttributeError:
            pass

    log = log_parser(log_path)
    template_path = os.path.join(config["REPORT_DIR"], "report.html")
    report_path = os.path.join(config["REPORT_DIR"], "report-%s.html" % log_date)
    json_path = os.path.join(config["REPORT_DIR"], "report-%s.json" % log_date)

    # Выбираем как сохранять обработанные результаты
    printer = [to_report(template_path, report_path), to_json(json_path)][args.json]
    broadcast(log, [count_stat(printer)])

if __name__ == "__main__":
    main()
