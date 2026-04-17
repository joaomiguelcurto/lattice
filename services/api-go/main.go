package main

import (
	"context"
	"fmt"
	"log"
	"net/http"

	"github.com/redis/go-redis/v9"
)

// 'ctx' works like a timer, telling Go how long to wait for Redis
// we could think of it as a "signal" that just travels with our data
// it allows us to cancel operations or set timeouts so the app doesnt simply hang forever
var ctx = context.Background()

func main() {
	// create a 'Client' for Redis (this doesnt open the connection yet)
	// it works as a "phone number" so that Go can call Redis later on
	rdb := redis.NewClient(&redis.Options{
		Addr: "localhost:6379",
	})

	// check connectivity (simply ping Redis to check if its working
	// if it doesnt answer then the app stops)
	_, err := rdb.Ping(ctx).Result()
	if err != nil {
		log.Fatalf("Couldnt find Redis! Is Docker running? Error: %v", err)
	}
	fmt.Println("Go API connected to Redis.")

	// this is the endpoint that will work as the "gatekeeper" defining what happens at "/ingest" URL
	// 'w' (ResponseWriter) is how we talk back to the user
	// 'r' (Request) is how we read what the user sent us
	http.HandleFunc("/ingest", func(w http.ResponseWriter, r *http.Request) {
		// we reject any type of "GET" request
		if r.Method != http.MethodPost {
			http.Error(w, "Please use POST to send notes", http.StatusMethodNotAllowed)
			return
		}

		// data is sent in a 'Form'
		// we look for a specific key named "content"
		// example: content(key)->"This project is too much for my brain..."(value)
		note := r.FormValue("content")
		if note == "" {
			http.Error(w, "Note content cannot be empty", http.StatusBadRequest)
			return
		}

		// we push a note into a Redis list called "lattice_jobs"
		// Redis acts as a "Buffer", even if our Python worker is slow or crashes,
		// the notes will stay safe inside this Redis list until the worker is ready
		err := rdb.LPush(ctx, "lattice_jobs", note).Err()
		if err != nil {
			http.Error(w, "Failed to write to memo pad", http.StatusInternalServerError)
			return
		}

		// response for the request (useful specially to let me know if it worked)
		fmt.Fprintf(w, "Success! Your note is in the queue.")

	})

	// start the server and keeps listening for incoming traffic on the port 8080
	fmt.Println("API is awake at http://localhost:8080")
	log.Fatal(http.ListenAndServe(":8080", nil))

}
