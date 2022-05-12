package main

import (
    "net"
    "net/http"
    "os"
    "fmt"
    "os/signal"
    "syscall"
)

func info(w http.ResponseWriter, req *http.Request) {
    hostname, err := os.Hostname()
    if err != nil {
        panic(err)
    }
    uri := req.URL.Path
    ip := GetLocalIP()
    output := fmt.Sprintf("demo(v1), uri: %s, pod: %s, ip: %s\n", uri, hostname, ip)
    nameByte := []byte(output)
    w.Write(nameByte)
}

// GetLocalIP returns the non loopback local IP of the host
func GetLocalIP() string {
    addrs, err := net.InterfaceAddrs()
    if err != nil {
        return ""
    }
    for _, address := range addrs {
        // check the address type and if it is not a loopback the display it
        if ipnet, ok := address.(*net.IPNet); ok && !ipnet.IP.IsLoopback() {
            if ipnet.IP.To4() != nil {
                return ipnet.IP.String()
            }
        }
    }
    return ""
}

func ExitFunc()  {
    fmt.Println("Demo server is shutting down")
    os.Exit(0)
}


func main() {
    c := make(chan os.Signal)
    signal.Notify(c, syscall.SIGHUP, syscall.SIGINT, syscall.SIGTERM, syscall.SIGQUIT, syscall.SIGUSR1, syscall.SIGUSR2)
    go func() {
        for s := range c {
         switch s {
            default:
                ExitFunc()
            }
        }
    }()
    http.HandleFunc("/", info)
    http.ListenAndServe(":80", nil)
}