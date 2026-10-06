fn main() -> std::process::ExitCode {
    interlace_ocr::install_decoder();
    interlace_voice::install_decoder();
    interlace_core::cli::run()
}
