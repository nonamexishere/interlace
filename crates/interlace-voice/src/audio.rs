//! Container decode to 16 kHz mono f32. Weights are not opened here.

use std::io::{Cursor, ErrorKind, Read, Seek, SeekFrom};

use symphonia::core::audio::SampleBuffer;
use symphonia::core::codecs::{DecoderOptions, CODEC_TYPE_NULL};
use symphonia::core::errors::Error as AudioError;
use symphonia::core::formats::FormatOptions;
use symphonia::core::io::{MediaSource, MediaSourceStream};
use symphonia::core::meta::MetadataOptions;
use symphonia::core::probe::Hint;

const TARGET_HZ: u32 = 16_000;
const OPUS_HZ: u32 = 48_000;

enum Container {
    Opus,
    Symphonia,
}

pub fn decode_pcm_16k(bytes: &[u8]) -> Option<Vec<f32>> {
    let (pcm, rate) = match container(bytes)? {
        Container::Opus => decode_opus(bytes)?,
        Container::Symphonia => decode_symphonia(bytes)?,
    };
    let mono = mix_mono(&pcm, rate.1)?;
    let out = resample(&mono, rate.0, TARGET_HZ);
    if out.is_empty() {
        None
    } else {
        Some(out)
    }
}

fn container(bytes: &[u8]) -> Option<Container> {
    if bytes.is_empty() || is_image(bytes) {
        return None;
    }
    if bytes.starts_with(b"OggS") {
        let window = &bytes[..bytes.len().min(64 * 1024)];
        if window.windows(8).any(|w| w == b"OpusHead") {
            return Some(Container::Opus);
        }
        return Some(Container::Symphonia);
    }
    if is_wav(bytes) || is_mp3_or_adts(bytes) || is_m4a(bytes) {
        Some(Container::Symphonia)
    } else {
        None
    }
}

fn is_image(bytes: &[u8]) -> bool {
    bytes.starts_with(&[0xFF, 0xD8])
        || bytes.starts_with(b"\x89PNG")
        || bytes.starts_with(b"GIF87a")
        || bytes.starts_with(b"GIF89a")
        || bytes.starts_with(b"BM")
        || is_webp(bytes)
        || is_image_ftyp(bytes)
}

fn is_webp(bytes: &[u8]) -> bool {
    bytes.len() >= 12 && bytes.starts_with(b"RIFF") && &bytes[8..12] == b"WEBP"
}

fn is_image_ftyp(bytes: &[u8]) -> bool {
    if bytes.len() < 12 || &bytes[4..8] != b"ftyp" {
        return false;
    }
    matches!(
        &bytes[8..12],
        b"heic" | b"heix" | b"heif" | b"mif1" | b"msf1" | b"avif"
    )
}

fn is_wav(bytes: &[u8]) -> bool {
    bytes.len() >= 12 && bytes.starts_with(b"RIFF") && &bytes[8..12] == b"WAVE"
}

fn is_m4a(bytes: &[u8]) -> bool {
    bytes.len() >= 12 && &bytes[4..8] == b"ftyp" && !is_image_ftyp(bytes)
}

fn is_mp3_or_adts(bytes: &[u8]) -> bool {
    if bytes.starts_with(b"ID3") {
        return true;
    }
    bytes.len() >= 2 && bytes[0] == 0xFF && (bytes[1] & 0xE0) == 0xE0
}

fn decode_opus(bytes: &[u8]) -> Option<(Vec<f32>, (u32, usize))> {
    let (pcm, head) = ruopus::decode_ogg_opus(bytes).ok()?;
    let channels = usize::from(head.channel_count);
    if channels == 0 || pcm.is_empty() || pcm.len() % channels != 0 {
        return None;
    }
    Some((pcm, (OPUS_HZ, channels)))
}

fn decode_symphonia(bytes: &[u8]) -> Option<(Vec<f32>, (u32, usize))> {
    let source = BytesSource {
        cursor: Cursor::new(bytes.to_vec()),
    };
    let mss = MediaSourceStream::new(Box::new(source), Default::default());
    let probed = symphonia::default::get_probe()
        .format(
            &Hint::new(),
            mss,
            &FormatOptions::default(),
            &MetadataOptions::default(),
        )
        .ok()?;
    let mut format = probed.format;
    let (track_id, params) = {
        let track = format
            .tracks()
            .iter()
            .find(|track| track.codec_params.codec != CODEC_TYPE_NULL)?;
        (track.id, track.codec_params.clone())
    };
    let mut decoder = symphonia::default::get_codecs()
        .make(&params, &DecoderOptions::default())
        .ok()?;
    let mut pcm = Vec::new();
    let mut shape: Option<(u32, usize)> = None;
    loop {
        let packet = match format.next_packet() {
            Ok(packet) => packet,
            Err(AudioError::IoError(err)) if err.kind() == ErrorKind::UnexpectedEof => break,
            Err(AudioError::ResetRequired) => break,
            Err(_) => return None,
        };
        while !format.metadata().is_latest() {
            format.metadata().pop();
        }
        if packet.track_id() != track_id {
            continue;
        }
        let decoded = match decoder.decode(&packet) {
            Ok(decoded) => decoded,
            Err(_) => return None,
        };
        let spec = *decoded.spec();
        let channels = spec.channels.count();
        if spec.rate == 0 || channels == 0 {
            return None;
        }
        match shape {
            Some((rate, count)) if rate != spec.rate || count != channels => return None,
            None => shape = Some((spec.rate, channels)),
            Some(_) => {}
        }
        let frames = decoded.frames();
        if frames == 0 {
            continue;
        }
        let dur = (decoded.capacity() as u64).max(u64::try_from(frames).ok()?);
        let mut buf = SampleBuffer::<f32>::new(dur, spec);
        buf.copy_interleaved_ref(decoded);
        pcm.extend_from_slice(buf.samples());
    }
    let shape = shape?;
    if pcm.is_empty() {
        None
    } else {
        Some((pcm, shape))
    }
}

fn mix_mono(interleaved: &[f32], channels: usize) -> Option<Vec<f32>> {
    if channels == 0 || interleaved.len() % channels != 0 {
        return None;
    }
    if channels == 1 {
        return Some(interleaved.to_vec());
    }
    let mut mono = Vec::with_capacity(interleaved.len() / channels);
    for frame in interleaved.chunks_exact(channels) {
        let sum: f32 = frame.iter().copied().sum();
        mono.push(sum / channels as f32);
    }
    Some(mono)
}

fn resample(input: &[f32], from_hz: u32, to_hz: u32) -> Vec<f32> {
    if input.is_empty() || from_hz == 0 || to_hz == 0 {
        return Vec::new();
    }
    if from_hz == to_hz {
        return input.to_vec();
    }
    let out_len = usize::try_from(
        (u64::try_from(input.len()).unwrap_or(0)).saturating_mul(u64::from(to_hz))
            / u64::from(from_hz),
    )
    .unwrap_or(0);
    if out_len == 0 {
        return Vec::new();
    }
    let mut out = Vec::with_capacity(out_len);
    let step = f64::from(from_hz) / f64::from(to_hz);
    for i in 0..out_len {
        let pos = i as f64 * step;
        let idx = pos.floor() as usize;
        let frac = (pos - idx as f64) as f32;
        let a = input.get(idx).copied().unwrap_or(0.0);
        let b = input.get(idx + 1).copied().unwrap_or(a);
        out.push(a + (b - a) * frac);
    }
    out
}

struct BytesSource {
    cursor: Cursor<Vec<u8>>,
}

impl Read for BytesSource {
    fn read(&mut self, buf: &mut [u8]) -> std::io::Result<usize> {
        self.cursor.read(buf)
    }
}

impl Seek for BytesSource {
    fn seek(&mut self, pos: SeekFrom) -> std::io::Result<u64> {
        self.cursor.seek(pos)
    }
}

impl MediaSource for BytesSource {
    fn is_seekable(&self) -> bool {
        true
    }

    fn byte_len(&self) -> Option<u64> {
        u64::try_from(self.cursor.get_ref().len()).ok()
    }
}
