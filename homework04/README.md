# Реализация простого асинхронного веб-сервера

В реализации используются модули asyncore и asynchat. `epoll` используется по умолчанию (на MacOS X работает только с python 3, в противном случае используется `select`).

Сервер можно запустить со следующими опциями:
- **-w** - число воркеров (по умолчанию 1)
- **-r** - DOCUMENT_ROOT (по умолчанию текущий каталог)
- **--host** - хост (по умолчанию 127.0.0.1)
- **--port** - номер порта (по умолчанию 9000)
- **--log** - уровень логирования (по умолчанию `info`)
- **--logfile** - имя лог-файла (по умолчанию станадртный поток вывода)

Результаты нагрузочного тестирования:
```sh
$ ab -n 50000 -c 100 -r http://localhost:80/

Server Software:        
Server Hostname:        localhost
Server Port:            80

Document Path:          /
Document Length:        0 bytes

Concurrency Level:      100
Time taken for tests:   110.833 seconds
Complete requests:      50000
Failed requests:        1
   (Connect: 0, Receive: 1, Length: 0, Exceptions: 0)
Write errors:           0
Total transferred:      2949941 bytes
HTML transferred:       0 bytes
Requests per second:    451.13 [#/sec] (mean)
Time per request:       221.665 [ms] (mean)
Time per request:       2.217 [ms] (mean, across all concurrent requests)
Transfer rate:          25.99 [Kbytes/sec] received

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0    0   0.2      0      15
Processing:     0    2   1.3      2     107
Waiting:        0    2   1.3      2     107
Total:          0    2   1.3      2     108

Percentage of the requests served within a certain time (ms)
  50%      2
  66%      2
  75%      2
  80%      2
  90%      3
  95%      3
  98%      5
  99%      6
 100%    108 (longest request)
```

