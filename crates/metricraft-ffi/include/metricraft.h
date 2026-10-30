#ifndef METRICRAFT_H
#define METRICRAFT_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

/* ABI 4. Every McExpr* returned by this library owns one immutable shared root.
 * Borrowed arguments must stay live during each call. Free each owner once. */
typedef struct McExpr McExpr;
typedef struct McError { uint32_t code; char *message; } McError;
uint32_t mc_abi_version(void);
McError *mc_last_error(void);
void mc_error_free(McError *error);
void mc_string_free(char *text);
void mc_expr_free(McExpr *expr);
McExpr *mc_expr_new(const char *op, const char *a, const char *b,
                    const McExpr *const *children, size_t count);
char *mc_expr_build(const McExpr *expr, uint32_t mode);
char *mc_expr_build_with_limits(const McExpr *expr, uint32_t mode,
                                size_t max_output_bytes, size_t max_expanded_nodes);
char *mc_expr_build_with_options(const McExpr *expr, uint32_t mode,
                                 size_t max_output_bytes, size_t max_expanded_nodes,
                                 uint32_t flags);
char *mc_expr_inspect(const McExpr *expr, uint32_t kind, uint32_t mode,
                      size_t max_output_bytes, size_t max_items, uint32_t flags);

/* Optional additive parsing symbol; older ABI-4 binaries may not export it.
 * These structures have a fixed layout. Zero option fields select defaults.
 * Mode: 0 PromQL; 1 MetricsQL (parsing currently unsupported).
 * Flags: bit 0 experimental functions, 1 duration expressions,
 *        2 extended range selectors, 3 binary fill modifiers. */
typedef struct McParseOptions {
    size_t max_input_bytes, max_tokens, max_depth, max_work;
    size_t max_output_bytes, max_expanded_nodes;
    uint32_t flags;
} McParseOptions;
typedef struct McParseErrorInfo {
    /* 0 no parser error; 1 syntax; 2 validation; 3 dialect;
     * 4 unsupported; 5 limit; 6 other. Byte range is end-exclusive. */
    uint32_t kind;
    size_t start, end;
} McParseErrorInfo;
/* source is borrowed for this call; null is allowed only when source_len == 0.
 * options and error_info may be null. Output must not alias input. Error info
 * is caller-owned and zeroed on entry; message uses mc_last_error as above.
 * Returns null on failure, otherwise an owner freed with mc_expr_free. */
McExpr *mc_expr_parse(const uint8_t *source, size_t source_len, uint32_t mode,
                      const McParseOptions *options, McParseErrorInfo *error_info);

/* Optional additive editing exports. No operation mutates an input expression.
 * Returned owners survive freeing their inputs; unaffected subtrees are shared. */
typedef struct McBuildOptions {
    size_t max_output_bytes, max_expanded_nodes;
    uint32_t flags;
} McBuildOptions;
/* kind 0 = node kind, 1 = value type. Free output with mc_string_free. */
char *mc_expr_node_info(const McExpr *expr, uint32_t kind);
/* Query count with (output=NULL, capacity=0); otherwise fill caller-owned slots.
 * Returns count or -1. Free each returned owner with mc_expr_free. Capacity errors
 * leave output untouched. The caller owns the output array, not the library.
 * Inputs must stay live, and output must not alias them. Leaves have zero children. */
ptrdiff_t mc_expr_children(const McExpr *expr, McExpr **output, size_t capacity);
/* Paths contain at most 1024 zero-based child indexes; empty path selects root.
 * Nonempty paths require len readable size_t values. Returned handles are owners. */
McExpr *mc_expr_at_path(const McExpr *expr, const size_t *indexes, size_t len);
/* Returns 1 if native node identity matches, 0 otherwise, -1 on error. */
int32_t mc_expr_shares_node(const McExpr *expr, const McExpr *other);
/* Null options or zero budgets use build defaults; flags are described above.
 * Mode is explicit: 0 PromQL, 1 MetricsQL. No-op edits still validate the root.
 * Non-root replacements must preserve value type. Null result reports failure. */
McExpr *mc_expr_replace_at(const McExpr *expr, const size_t *indexes, size_t len,
                         const McExpr *replacement, uint32_t mode,
                         const McBuildOptions *options);

#ifdef __cplusplus
}
#endif
#endif
