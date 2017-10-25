package main

import (
    "flag"
    "log"
    "errors"
    "fmt"
    "strings"
    "strconv"
    "path/filepath"
    "compress/gzip"
    "bufio"
    "os"
    "github.com/golang/protobuf/proto"
    "github.com/bradfitz/gomemcache/memcache"
    "./appsinstalled"
)


type AppsInstalled struct {
    dev_type string
    dev_id string
    lat float64
    lon float64
    apps []uint32
}


type Config struct {
    logfile string
    nworkers int
    bufsize int
    pattern string
    device_memc map[string]string
}


type MemcacheItem struct {
    key string
    data []byte
}


type Stat struct {
    errors int
    processed int
}

const NORMAL_ERR_RATE = 0.01


func parseAppsInstalled(line string) (*AppsInstalled, error) {
    line_parts := strings.Split(line, "\t")
    if len(line_parts) < 5 {
        return nil, errors.New("Not all parts was found in line")
    }

    dev_type := line_parts[0]
    dev_id := line_parts[1]
    if dev_type == "" || dev_id == "" {
        return nil, errors.New("dev_type or dev_id was missed")
    }

    lat, err := strconv.ParseFloat(line_parts[2], 64)
    if err != nil {
        return nil, err
    }

    lon, err := strconv.ParseFloat(line_parts[3], 64)
    if err != nil {
        return nil, err
    }

    raw_apps := line_parts[4]
    apps := make([]uint32, 0)
    for _, app := range strings.Split(raw_apps, ",") {
        app_id, _ := strconv.Atoi(app)
        apps = append(apps, uint32(app_id))
    }

    return &AppsInstalled{
        dev_type: dev_type,
        dev_id: dev_id,
        lat: lat,
        lon: lon,
        apps: apps,
    }, nil
}


func SerializeAppsInstalled(apps_installed *AppsInstalled) (*MemcacheItem, error) {
    ua := &appsinstalled.UserApps{
        Lat: proto.Float64(apps_installed.lat),
        Lon: proto.Float64(apps_installed.lon),
        Apps: apps_installed.apps,
    }
    key := fmt.Sprintf("%s:%s", apps_installed.dev_type, apps_installed.dev_id)
    packed, err := proto.Marshal(ua);
    if err != nil {
        // TODO: Log error
        return nil, err
    }
    return &MemcacheItem{key, packed}, nil
}


func MemcacheWorker(mc *memcache.Client, items chan *MemcacheItem, results_queue chan Stat) {
    processed, errors := 0, 0
    for item := range items {
        err := mc.Set(&memcache.Item{
            Key: item.key,
            Value: item.data,
        })
        if err != nil {
            errors += 1
        } else {
            processed += 1
        }
    }
    results_queue <- Stat{errors, processed}
}


func LineParser(lines chan string, memc_queues map[string]chan *MemcacheItem, results_queue chan Stat) {
    errors := 0
    for line := range lines {
        apps_installed, err := parseAppsInstalled(line);
        if err != nil {
            errors += 1
            continue
        }
        item, err := SerializeAppsInstalled(apps_installed);
        if err != nil {
            errors += 1
            continue
        }
        queue, ok := memc_queues[apps_installed.dev_type];
        if !ok {
            log.Println("Unknow device type:", apps_installed.dev_type)
            errors += 1
            continue
        }
        queue <- item
    }
    results_queue <- Stat{errors:errors}
}


func dotRename(path string) error {
    head := filepath.Dir(path)
    fn := filepath.Base(path)
    if err := os.Rename(path, filepath.Join(head, "." + fn)); err != nil {
        log.Printf("Can't rename a file: %s", path)
        return err
    }
    return nil
}


func fileReader(filename string, lines_queue chan string) error {
    log.Println("Processing:", filename)
    f, err := os.Open(filename)
    if err != nil {
        log.Printf("Can't open file: %s", filename)
        return err
    }
    defer f.Close()

    gz, err := gzip.NewReader(f)
    if err != nil {
        // Handle error
        log.Printf("Can't create a new Reader %v", err)
        return err
    }
    defer gz.Close()

    scanner := bufio.NewScanner(gz)
    for scanner.Scan() {
        line := scanner.Text()
        line = strings.Trim(line, " ")
        if line == "" {
            continue
        }
        lines_queue <- line
    }

    if err := scanner.Err(); err != nil {
        log.Printf("Scanner error: %v", err)
        return err
    }

    return nil
}


func processFiles(config *Config) error {
    files, err := filepath.Glob(config.pattern)
    if err != nil {
        log.Printf("Could not find files for the given pattern: %s", config.pattern)
        return err
    }

    // Канал со статистикой, в который пишут воркеры по завершению работы
    results_queue := make(chan Stat)

    // Создаем воркеров, которые пишут в мемкеш. Каждый воркер пишет в своей мемкеш
    memc_queues := make(map[string]chan *MemcacheItem)
    for dev_type, memc_addr := range config.device_memc {
        memc_queues[dev_type] = make(chan *MemcacheItem, config.bufsize)
        mc := memcache.New(memc_addr)
        go MemcacheWorker(mc, memc_queues[dev_type], results_queue)
    }

    // Создаем воркеров, которые будут парсить строки лог-файла
    lines_queue := make(chan string, config.bufsize)
    for i := 0; i < config.nworkers; i++ {
        go LineParser(lines_queue, memc_queues, results_queue)
    }

    for _, filename := range files {
        fileReader(filename, lines_queue)
        dotRename(filename)
    }
    close(lines_queue)

    // Обходим воркеров, которые парсили строки
    processed, errors := 0, 0
    for i := 0; i < config.nworkers; i++ {
        results := <-results_queue
        processed += results.processed
        errors += results.errors
    }

    // Закрываем каналы для задач мемкеша и собираем с них статистику
    for _, queue := range memc_queues {
        close(queue)
        results := <-results_queue
        processed += results.processed
        errors += results.errors
    }

    err_rate := float32(errors) / float32(processed)
    if err_rate < NORMAL_ERR_RATE {
        log.Printf("Acceptable error rate (%g). Successfull load\n", err_rate)
    } else {
        log.Printf("High error rate (%g > %g). Failed load\n", err_rate, NORMAL_ERR_RATE)
    }

    return nil
}


var (
    logfile string
    pattern string
    nworkers int
    bufsize int
    idfa string
    gaid string
    adid string
    dvid string
)

func init() {
    flag.StringVar(&pattern, "pattern", "/data/appsinstalled/*.tsv.gz", "")
    flag.StringVar(&logfile, "log", "", "")
    flag.IntVar(&nworkers, "workers", 5, "")
    flag.IntVar(&bufsize, "bufsize", 10, "")
    flag.StringVar(&idfa, "idfa", "127.0.0.1:33013", "")
    flag.StringVar(&gaid, "gaid", "127.0.0.1:33014", "")
    flag.StringVar(&adid, "adid", "127.0.0.1:33015", "")
    flag.StringVar(&dvid, "dvid", "127.0.0.1:33016", "")
}


func newConfig() *Config {
    return &Config{
        logfile: logfile,
        pattern: pattern,
        nworkers: nworkers,
        bufsize: bufsize,
        device_memc: map[string]string{
            "idfa": idfa,
            "gaid": gaid,
            "adid": adid,
            "dvid": dvid,
        },
    }
}


func main() {
    flag.Parse()
    config := newConfig()
    if config.logfile != "" {
        f, err := os.OpenFile(config.logfile, os.O_WRONLY|os.O_CREATE|os.O_APPEND, 0644)
        if err != nil {
            log.Fatalf("Cannot open log file: %s", config.logfile)
        }
        defer f.Close()
        log.SetOutput(f)
    }
    log.Println("Memc loader started with config:", config)
    processFiles(config)
}
