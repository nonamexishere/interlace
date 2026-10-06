//! On-device photo text. Tesseract links only into this crate.

mod pixels;

use std::ffi::{CStr, CString};
use std::os::unix::ffi::OsStrExt;
use std::path::Path;

use interlace_core::CoreError;

/// Register [`text_from_image`] with core before the CLI or IPC runs.
pub fn install_decoder() {
    interlace_core::cli::install_ocr_decoder(text_from_image);
}

/// Recognized text, or `Ok(None)` when the bytes or the weights cannot be used.
pub fn text_from_image(bytes: &[u8], weights: &Path) -> Result<Option<String>, CoreError> {
    let Some(rgba) = pixels::decode_rgba(bytes) else {
        return Ok(None);
    };
    if rgba.is_empty() || !weights.is_file() {
        return Ok(None);
    }
    let Ok(path) = CString::new(weights.as_os_str().as_bytes()) else {
        return Ok(None);
    };
    let width = i32::try_from(rgba.width()).unwrap_or(0);
    let height = i32::try_from(rgba.height()).unwrap_or(0);
    let stride = i32::try_from(rgba.width().saturating_mul(4)).unwrap_or(0);
    if width <= 0 || height <= 0 || stride <= 0 {
        return Ok(None);
    }
    let ptr = unsafe {
        interlace_ocr_utf8(
            path.as_ptr(),
            rgba.as_raw().as_ptr(),
            width,
            height,
            4,
            stride,
        )
    };
    if ptr.is_null() {
        return Ok(None);
    }
    let text = unsafe { CStr::from_ptr(ptr) }
        .to_str()
        .ok()
        .map(str::to_owned);
    unsafe { libc::free(ptr.cast()) };
    match text {
        Some(text) if !text.trim().is_empty() => Ok(Some(text)),
        _ => Ok(None),
    }
}

unsafe extern "C" {
    fn interlace_ocr_utf8(
        weights_path: *const libc::c_char,
        pixels: *const u8,
        width: i32,
        height: i32,
        bytes_per_pixel: i32,
        bytes_per_line: i32,
    ) -> *mut libc::c_char;
}
