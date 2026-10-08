// Test-only oracle using the upstream MetricsQL parser. No service is started.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"

	"github.com/VictoriaMetrics/metricsql"
)

func main() {
	jsonOutput := flag.Bool("json", false, "emit one result per expression")
	flag.Parse()
	var expressions []string
	if err := json.NewDecoder(os.Stdin).Decode(&expressions); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	failed := false
	results := make([]map[string]interface{}, 0, len(expressions))
	for i, expression := range expressions {
		_, err := metricsql.Parse(expression)
		message := ""
		if err != nil {
			message = err.Error()
		}
		results = append(results, map[string]interface{}{"ok": err == nil, "error": message})
		if err != nil && !*jsonOutput {
			fmt.Fprintf(os.Stderr, "case %d: %s: %v\n", i, expression, err)
			failed = true
		}
	}
	if *jsonOutput {
		if err := json.NewEncoder(os.Stdout).Encode(results); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		return
	}
	if failed {
		os.Exit(1)
	}
	fmt.Printf("MetricsQL v0.87.4 parsed %d expressions\n", len(expressions))
}
