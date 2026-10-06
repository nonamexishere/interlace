#include <tesseract/baseapi.h>

#include <cstdint>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>

static tesseract::TessBaseAPI *g_api = nullptr;
static std::string g_path;

static tesseract::TessBaseAPI *api_for(const char *weights_path) {
    if (weights_path == nullptr || weights_path[0] == '\0') {
        return nullptr;
    }
    if (g_api != nullptr && g_path == weights_path) {
        return g_api;
    }
    if (g_api != nullptr) {
        g_api->End();
        delete g_api;
        g_api = nullptr;
        g_path.clear();
    }
    std::ifstream in(weights_path, std::ios::binary);
    if (!in) {
        return nullptr;
    }
    std::vector<char> data((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
    if (data.empty()) {
        return nullptr;
    }
    auto *api = new tesseract::TessBaseAPI();
    const int rc = api->Init(
        data.data(),
        static_cast<int>(data.size()),
        "tur",
        tesseract::OEM_LSTM_ONLY,
        nullptr,
        0,
        nullptr,
        nullptr,
        false,
        nullptr);
    if (rc != 0) {
        delete api;
        return nullptr;
    }
    g_api = api;
    g_path = weights_path;
    return g_api;
}

extern "C" char *interlace_ocr_utf8(
    const char *weights_path,
    const uint8_t *pixels,
    int width,
    int height,
    int bytes_per_pixel,
    int bytes_per_line) {
    if (pixels == nullptr || width <= 0 || height <= 0 || bytes_per_pixel <= 0 || bytes_per_line <= 0) {
        return nullptr;
    }
    tesseract::TessBaseAPI *api = api_for(weights_path);
    if (api == nullptr) {
        return nullptr;
    }
    api->SetImage(pixels, width, height, bytes_per_pixel, bytes_per_line);
    char *utf = api->GetUTF8Text();
    if (utf == nullptr) {
        return nullptr;
    }
    const size_t n = std::strlen(utf);
    char *out = static_cast<char *>(std::malloc(n + 1));
    if (out == nullptr) {
        delete[] utf;
        return nullptr;
    }
    std::memcpy(out, utf, n + 1);
    delete[] utf;
    return out;
}
