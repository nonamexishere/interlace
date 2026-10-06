fn main() -> std::process::ExitCode {
    interlace_voice::install_decoder();
    interlace_core::cli::run()
}
