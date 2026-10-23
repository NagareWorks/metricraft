# Query playground

Build a monitoring query by choosing conditions. The Python calls and generated
PromQL update together; run the query against editable local samples to see the
result. Start with the counter preset, then try grouping without `instance`,
adding a threshold, or switching to queue-depth data. **Try regex filters** selects
`instance=~"api-.*"` and `environment!~"staging|development"`. Use **Arithmetic**
and **Value filter** to see Python operators such as `expression * 100` and
`expression > 5` in action.

For the production integration pattern, see [accept application inputs](configurable-query-contract.md).
