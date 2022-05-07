package main

import (
    "net/http"
    "os"
    "fmt"
    "os/signal"
    "syscall"
)

func hostName(w http.ResponseWriter, req *http.Request) {
    name, err := os.Hostname()
    if err != nil {
        panic(err)
    }
    nameByte := []byte("Demo(v1) [POD: " + name + "]\n")
    w.Write(nameByte)
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
    http.HandleFunc("/", hostName)
    http.ListenAndServe(":80", nil)
}