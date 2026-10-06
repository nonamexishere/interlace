#include "whisper.h"

#include <stdlib.h>
#include <string.h>

static struct whisper_context *g_ctx = NULL;
static char g_path[4096];
static int g_logs = 0;

static void silent_log(enum ggml_log_level level, const char *text, void *user_data) {
    (void)level;
    (void)text;
    (void)user_data;
}

static struct whisper_context *load_model(const char *model_path) {
    if (!g_logs) {
        ggml_log_set(silent_log, NULL);
        g_logs = 1;
    }
    if (g_ctx && strcmp(g_path, model_path) == 0) {
        return g_ctx;
    }
    if (g_ctx) {
        whisper_free(g_ctx);
        g_ctx = NULL;
        g_path[0] = '\0';
    }
    size_t n = strlen(model_path);
    if (n == 0 || n >= sizeof(g_path)) {
        return NULL;
    }
    struct whisper_context_params cparams = whisper_context_default_params();
    cparams.use_gpu = false;
    struct whisper_context *ctx = whisper_init_from_file_with_params(model_path, cparams);
    if (!ctx) {
        return NULL;
    }
    memcpy(g_path, model_path, n + 1);
    g_ctx = ctx;
    return g_ctx;
}

extern "C" char *interlace_whisper_transcribe(
    const char *model_path,
    const float *samples,
    int n_samples
) {
    if (!model_path || !samples || n_samples <= 0) {
        return NULL;
    }
    struct whisper_context *ctx = load_model(model_path);
    if (!ctx) {
        return NULL;
    }
    struct whisper_full_params wparams = whisper_full_default_params(WHISPER_SAMPLING_GREEDY);
    wparams.language = "auto";
    wparams.detect_language = false;
    wparams.translate = false;
    wparams.no_timestamps = true;
    wparams.print_special = false;
    wparams.print_progress = false;
    wparams.print_realtime = false;
    wparams.print_timestamps = false;
    wparams.suppress_blank = true;
    wparams.suppress_nst = true;
    wparams.single_segment = false;
    if (whisper_full(ctx, wparams, samples, n_samples) != 0) {
        whisper_free(g_ctx);
        g_ctx = NULL;
        g_path[0] = '\0';
        return NULL;
    }
    const int n_seg = whisper_full_n_segments(ctx);
    size_t total = 1;
    for (int i = 0; i < n_seg; i++) {
        const char *text = whisper_full_get_segment_text(ctx, i);
        if (text) {
            total += strlen(text) + 1;
        }
    }
    char *out = (char *)malloc(total);
    if (!out) {
        return NULL;
    }
    size_t used = 0;
    out[0] = '\0';
    for (int i = 0; i < n_seg; i++) {
        const char *text = whisper_full_get_segment_text(ctx, i);
        if (!text || text[0] == '\0') {
            continue;
        }
        size_t len = strlen(text);
        if (used > 0) {
            if (used + 1 >= total) {
                break;
            }
            out[used++] = ' ';
            out[used] = '\0';
        }
        if (used + len >= total) {
            break;
        }
        memcpy(out + used, text, len);
        used += len;
        out[used] = '\0';
    }
    return out;
}

extern "C" void interlace_whisper_free(char *text) {
    free(text);
}
