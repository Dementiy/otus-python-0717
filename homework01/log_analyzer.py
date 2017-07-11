#!/usr/bin/env python
# -*- coding: utf-8 -*-


# log_format ui_short '$remote_addr $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

import gzip
import collections
import functools
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


def field_map(dictseq, name, func):
    for d in dictseq:
        try:
            d[name] = func(d[name])
            yield d
        except:
            pass


def save2html(stat, template, report_path):
    with open(template) as f:
        text = f.read()
    text = text.replace('$table_json', json.dumps(stat))

    with open(report_path, "w") as f:
        f.write(text)


def save2json(stat, json_path):
    with open(json_path, "w") as f:
        f.write(json.dumps(stat))


def median(nums):
    nums = sorted(nums)
    n = len(nums)
    if n < 1:
        return None
    if n % 2 == 1:
        return nums[n//2]
    else:
        return sum(nums[n//2-1:n//2+1])/2.0


def process_log(log):
    url2times = collections.defaultdict(list)
    for logline in log:
        url2times[logline['request']].append(logline['request_time'])

    total_count = total_time = 0
    for v in url2times.itervalues():
        total_count += len(v)
        total_time += sum(v)

    stat = []
    for url, times_list in url2times.iteritems():
        stat.append({
            'url': url,
            'count': len(times_list),
            'count_perc': round(100 * len(times_list) / float(total_count), 3),
            'time_avg': round(sum(times_list) / len(times_list), 3),
            'time_med': round(median(times_list), 3),
            'time_max': round(max(times_list), 3),
            'time_sum': round(sum(times_list), 3),
            'time_perc': round(100 * sum(times_list) / total_time, 3)
        })
    return stat


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


def main(log_path, fmt):
    """
    Папки из конфига уже должны быть созданы.
    Подразумевается, что формат логов такой logname-DATE[.gz]

    Варианты запуска:
    $ ./log_analyzer.py
    $ ./log_analyzer.py --log_path path/to/log
    $ ./log_analyzer.py -f json
    $ ./log_analyzer.py --log_path path/to/log --format json
    """

    # Находим последний лог-файл по дате в имени файла
    if not log_path:
        logs = [os.path.join(config["LOG_DIR"], logfile) for logfile in os.listdir(config['LOG_DIR'])]
        log_path = max(logs, key=lambda logfile: re.findall('(\d{8})', logfile)[0])

    # Извлекаем дату из имени файла
    log_date = re.findall('(\d{8})', log_path)[0]
    log_date = log_date[:4] + "." + log_date[4:6] + "." + log_date[6:]

    # Проверяем существует ли уже отчет в соответствующем формате
    output_path = os.path.join(config["REPORT_DIR"], "report-%s.%s" % (log_date, fmt))
    if os.path.exists(output_path):
        print "Report already exists", output_path
        return

    log = log_parser(log_path)
    stat = process_log(log)

    if fmt == "json":
        save2json(stat, output_path)
    else:
        tmpl_path = os.path.join(config["REPORT_DIR"], "report.html")
        save2html(stat, tmpl_path, output_path)


def parse_args():
    parser = argparse.ArgumentParser("Process log files")
    parser.add_argument("--log_path",
        dest="log_path",
        default=None,
        help="Path to the log file")
    parser.add_argument("-f", "--format",
        dest="fmt",
        default="html",
        help="Output format")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(args.log_path, args.fmt)
