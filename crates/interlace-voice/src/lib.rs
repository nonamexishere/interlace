//! On-device voice transcripts. Whisper.cpp links only into this crate.

mod audio;
mod whisper;

use std::path::Path;

use interlace_core::CoreError;

/// Register [`transcript_from_audio`] with core before the CLI or IPC runs.
pub fn install_decoder() {
    interlace_core::cli::install_voice_decoder(transcript_from_audio);
}

/// Plain transcript, or `Ok(None)` when the bytes or the weights cannot be used.
/// A bad note is not an error: one failure must not fail the pass.
pub fn transcript_from_audio(
    bytes: &[u8],
    weights_path: &Path,
) -> Result<Option<String>, CoreError> {
    let Some(pcm) = audio::decode_pcm_16k(bytes) else {
        return Ok(None);
    };
    if pcm.is_empty() || !weights_path.is_file() {
        return Ok(None);
    }
    Ok(whisper::transcribe(&pcm, weights_path))
}
