import argparse
import pathlib
import json
import logging
import datetime
import re
import gzip
import collections
import statistics
import string
import os
from typing import NamedTuple, Union, Optional, List, Dict, Any, cast

default_config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log",
    "LOG_FILE": None,
    "ERRORS_TRESHOLD": 0.01,
    "TS_FILE": "./log_analyzer.ts",
}

log_pattern = re.compile(
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

Config  = Dict[str, Any]
Log = NamedTuple('Log', [('path', pathlib.Path), ('date', datetime.date), ('ext', str)])
Request = NamedTuple('Request', [('url', str), ('request_time', float)])

def update_ts(ts_file: pathlib.Path) -> None:
    now = datetime.datetime.now()
    timestamp = int(now.timestamp())
    ts_file.write_text(str(timestamp))
    os.utime(ts_file.absolute(), times=(timestamp, timestamp))

def create_report(template_path: pathlib.Path, destination_path: pathlib.Path, log_statistics: List[Dict[str, Union[str, float]]]) -> None:
    with template_path.open() as f:
        template = string.Template(f.read())
    report = template.safe_substitute(table_json=json.dumps(log_statistics))
    with destination_path.open(mode='w') as f:
        f.write(report)

def process_line(line: str) -> Optional[Request]:
    m = log_pattern.match(line)
    if not m:
        return None
    
    log_line = m.groupdict()
    try:
        method, url, protocol = log_line['request'].split()
        request_time = float(log_line['request_time'])
    except (ValueError, TypeError):
        return None
    else:
        return Request(url, request_time)

def process_log(log: Log, errors_treshold: float) -> List[Dict[str, Union[str, float]]]:
    if log.ext == '.gz':
        f = gzip.open(log.path.absolute(), mode='rt')
    else:
        f = log.path.open()
    
    n_loglines = 0
    n_fails = 0
    url2times: Dict[str, List[float]] = collections.defaultdict(list)
    with f:
        for line in f:
            n_loglines += 1
            request = process_line(line)
            if not request:
                n_fails += 1
                continue
            url2times[request.url].append(request.request_time)

    errors = n_fails / n_loglines
    if errors > errors_treshold:
        raise Exception(f"Доля ошибок {errors} превышает {errors_treshold}")

    total_count = 0
    total_time = 0.
    for request_times in url2times.values():
        total_count += len(request_times)
        total_time  += sum(request_times)
    
    stat = []
    for url, request_times in url2times.items():
        stat.append({
            'url': url,
            'count': len(request_times),
            'count_perc': round(100. * len(request_times) / float(total_count), 3),
            'time_sum': round(sum(request_times), 3),
            'time_perc': round(100. * sum(request_times) / total_time, 3),
            'time_avg': round(statistics.mean(request_times), 3),
            'time_max': round(max(request_times), 3),
            "time_med": round(statistics.median(request_times), 3),
        })
    
    return stat # type: ignore

def get_report_path(report_dir: pathlib.Path, log: Log) -> pathlib.Path:
    if not report_dir.exists() or not report_dir.is_dir():
        raise FileNotFoundError("Неверно указан путь к директории с отчетами")
    
    report_filename = f'report-{log.date:%Y.%m.%d}.html'
    report_path = report_dir / report_filename
    return report_path

def get_last_logfile(log_dir: pathlib.Path) -> Optional[Log]:
    if not log_dir.exists() or not log_dir.is_dir():
        raise FileNotFoundError("Неверно указан путь к директории с журналами")
    
    logfile = None
    pattern = re.compile(r"^nginx-access-ui\.log-(\d{8})(\.gz)?$")
    for path in log_dir.iterdir():
        try:
            [(date, ext)] = re.findall(pattern, str(path))
            log_date = datetime.datetime.strptime(date, "%Y%m%d").date()
            if not logfile or logfile.date > log_date:
                logfile = Log(path, log_date, ext)
        except ValueError:
            pass
    
    return logfile

def setup_logging(logfile: Optional[str]) -> None:
    logging.basicConfig( # type: ignore
        level=logging.INFO,
        format="[%(asctime)s] %(levelname).1s %(message)s",
        datefmt="%Y.%m.%d %H:%M:%S",
        filename=logfile)

def get_config(path: str, default_config: Config) -> Config:
    if not path:
        return default_config
    
    p = pathlib.Path(path)
    if not p.exists() or not p.is_file():
        raise FileNotFoundError("Неверно указан путь к конфигурационному файлу")
    
    with p.open() as f:
        config = json.load(f)
    
    return {**default_config, **config}

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser("Обработка лог-файлов и генерирование отчета")
    parser.add_argument("--config",
        dest="config_path",
        help="Путь к конфигурационному файлу")
    return parser.parse_args()

def main(config: Config) -> None:
    log_dir = pathlib.Path(cast(str, config.get("LOG_DIR")))
    last_log = get_last_logfile(log_dir)
    if not last_log:
        logging.info(f"Нет логов в '{log_dir}' для обработки")
        return

    report_dir = pathlib.Path(cast(str, config.get("REPORT_DIR")))
    report_path = get_report_path(report_dir, last_log)
    if report_path.exists():
        logging.info(f"Отчет для '{last_log.path}' уже существует")
        return
        
    log_statistics = process_log(last_log, cast(float, config.get("ERRORS_TRESHOLD")))
    log_statistics = sorted(log_statistics, key=lambda r: r['time_sum'], reverse=True)
    log_statistics = log_statistics[:config.get("REPORT_SIZE")]
    report_template_path = report_dir / "report.html"
    create_report(report_template_path, report_path, log_statistics)
    
    ts_path = pathlib.Path(cast(str, config.get('TS_FILE')))
    update_ts(ts_path)

if __name__ == "__main__":
    args = parse_args()
    config = get_config(args.config_path, default_config)
    setup_logging(config.get('LOG_FILE'))

    try:
        main(config)
    except Exception as e:
        logging.exception(str(e))