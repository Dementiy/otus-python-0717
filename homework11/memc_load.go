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
    "reflect"
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


type Options struct {
    dry bool
    pattern string
    idfa string
    gaid string
    adid string
    dvid string
}

const NORMAL_ERR_RATE = 0.01


func insertAppsInstalled(memc_pool map[string]*memcache.Client, memc_addr string, apps_installed *AppsInstalled, dry_run bool) bool {
    ua := &appsinstalled.UserApps{
        Lat: proto.Float64(apps_installed.lat),
        Lon: proto.Float64(apps_installed.lon),
        Apps: apps_installed.apps,
    }
    key := fmt.Sprintf("%s:%s", apps_installed.dev_type, apps_installed.dev_id)
    packed, _ := proto.Marshal(ua)
    if dry_run {
        log.Printf("%s - %s -> %s", memc_addr, key, ua.String())
    } else {
        mc, ok := memc_pool[memc_addr]
        if !ok {
            mc = memcache.New(memc_addr)
            memc_pool[memc_addr] = mc
        }
        err := mc.Set(&memcache.Item{
            Key: key,
            Value: packed,
        })
        if err != nil {
            log.Printf("Cannot write to memc %s: %v", memc_addr, err)
            return false
        }
    }
    return true
}


func parseAppsInstalled(line string) (*AppsInstalled, error) {
    line_parts := strings.Split(line, "\t")
    if len(line_parts) < 5 {
        return nil, errors.New("")
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


func processFile(fname string, options Options) {
    log.Println("Processing:", fname)
    f, err := os.Open(fname)
    if err != nil {
        // Handle error
    }
    defer f.Close()

    gz, err := gzip.NewReader(f)
    if err != nil {
        // Handle error
    }
    defer gz.Close()

    device_memc := map[string]string{
        "idfa": options.idfa,
        "gaid": options.gaid,
        "adid": options.adid,
        "dvid": options.dvid,
    }

    processed, errors := 0, 0
    memc_pool := map[string]*memcache.Client{}
    scanner := bufio.NewScanner(gz)
    for scanner.Scan() {
        line := scanner.Text()
        line = strings.Trim(line, " ")

        if line == "" {
            continue
        }

        apps_installed, err := parseAppsInstalled(line)
        if err != nil {
            errors += 1
            continue
        }

        memc_addr, ok := device_memc[apps_installed.dev_type]
        if !ok {
            errors += 1
            log.Println("Unknow device type:", apps_installed.dev_type)
            continue
        }

        ok = insertAppsInstalled(memc_pool, memc_addr, apps_installed, options.dry)
        if ok {
            processed += 1
        } else {
            errors += 1
        }
    }

    err_rate := float32(errors) / float32(processed)
    if err_rate < NORMAL_ERR_RATE {
        log.Printf("Acceptable error rate (%g). Successfull load\n", err_rate)
    } else {
        log.Printf("High error rate (%g > %g). Failed load\n", err_rate, NORMAL_ERR_RATE)
    }
}


func prototest() {
    sample := "idfa\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,43,567,3,7,23\ngaid\t7rfw452y52g2gq4g\t55.55\t42.42\t7423,424"
    for _, line := range strings.Split(sample, "\n") {
        apps_installed, _ := parseAppsInstalled(line)
        ua := &appsinstalled.UserApps{
            Lat: proto.Float64(apps_installed.lat),
            Lon: proto.Float64(apps_installed.lon),
            Apps: apps_installed.apps,
        }
        packed, err := proto.Marshal(ua)
        if err != nil {
            // Handle error
        }

        unpacked := &appsinstalled.UserApps{}
        err = proto.Unmarshal(packed, unpacked)
        if err != nil {
            // Handle error
        }

        // TODO: replace to Assert
        if ua.GetLat() != unpacked.GetLat() || !reflect.DeepEqual(ua.GetApps(), unpacked.GetApps()) {
            os.Exit(1)
        }
    }
}


func dotRename(path string) {
    head := filepath.Dir(path)
    fn := filepath.Base(path)
    if err := os.Rename(path, filepath.Join(head, "." + fn)); err != nil {
        log.Fatalf("Can't rename a file: %s", path)
    }
}


func processFiles(options Options) {
    files, err := filepath.Glob(options.pattern)
    if err != nil {
        log.Fatalf("Could not find files for the given pattern: %s", options.pattern)
    }
    for _, fname := range files {
        processFile(fname, options)
        dotRename(fname)
    }
}


func main() {
    // Parse arguments
    dry := flag.Bool("dry", false, "")
    test := flag.Bool("test", false, "")
    pattern := flag.String("pattern", "/data/appsinstalled/*.tsv.gz", "")
    logfile := flag.String("log", "", "")
    idfa := flag.String("idfa", "127.0.0.1:33013", "")
    gaid := flag.String("gaid", "127.0.0.1:33014", "")
    adid := flag.String("adid", "127.0.0.1:33015", "")
    dvid := flag.String("dvid", "127.0.0.1:33016", "")
    flag.Parse()

    options := Options{
        dry: *dry,
        pattern: *pattern,
        idfa: *idfa,
        gaid: *gaid,
        adid: *adid,
        dvid: *dvid,
    }

    if *logfile != "" {
        f, err := os.OpenFile(*logfile, os.O_WRONLY|os.O_CREATE|os.O_APPEND, 0644)
        if err != nil {
            log.Fatalf("Cannot open log file: %s", logfile)
        }
        defer f.Close()
        log.SetOutput(f)
    }

    if *test {
        prototest()
        os.Exit(0)
    }

    log.Println("Memc loader started with options:", options)
    processFiles(options)
}
