package main

import (
	"context"
	"fmt"
	"log"
	"net/http"

	"github.com/redis/go-redis/v9"
)

// 'ctx' works like a timer, telling Go how long to wait for Redis
// before giving up (Background() means "never stop until the app closes.")
var ctx = context.Background()

func main() {
	// connect to Redis "Memo Pad" we started with Docker (the RAM "database")
	rdb := redis.NewClient(&redis.Options{
		Addr: "localhost:6379", // address we opened in Docker
	})

	// check connectivity
	_, err := rdb.Ping(ctx).Result()
	if err != nil {
		log.Fatalf("Couldnt find Redis! Is Docker running? Error: %v", err)
	}
	fmt.Println("Go API connected to Redis.")

	// "ingest" door
	http.HandleFunc("/ingest", func(w http.ResponseWriter, r *http.Request) {
		// only allows POST methods and not GET
		if r.Method != http.MethodPost {
			http.Error(w, "Please use POST to send notes", http.StatusMethodNotAllowed)
			return
		}

		// grab the text content from the request
		note := r.FormValue("content")

		// write the "Memo" (data payload/message) to Redis
		// LPush means "List Push" where we are pushing the note into a list called "lattice_jobs"
		err := rdb.LPush(ctx, "lattice_jobs", note).Err()
		if err != nil {
			http.Error(w, "Failed to write to memo pad", http.StatusInternalServerError)
			return
		}

		fmt.Fprintf(w, "Success! Your note is in the queue.")

	})

	fmt.Println("API is awake at http://localhost:8080")
	log.Fatal(http.ListenAndServe(":8080", nil))

}
