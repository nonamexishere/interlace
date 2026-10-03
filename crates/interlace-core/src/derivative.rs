//! Content-addressed stills for image, video, and PDF attachments.
//! Longest edge is 480. Failures leave a null pointer; they are not errors.

use std::path::Path;

use rusqlite::OptionalExtension;

use crate::db::Archive;
use crate::model::CoreError;

const STILL_EDGE: u32 = 480;

pub(crate) fn eligible(kind: &str, mime: Option<&str>, filename: Option<&str>) -> bool {
    is_image(kind, mime, filename) || is_video(kind, mime, filename) || is_pdf(mime, filename)
}

pub(crate) fn ensure_stored(
    archive: &Archive,
    attachment_id: i64,
    cas_hash: &str,
    filename: Option<&str>,
    mime: Option<&str>,
    kind: &str,
) -> Result<(), CoreError> {
    if !eligible(kind, mime, filename) {
        return Ok(());
    }
    let current = current_derivative(archive, attachment_id)?;
    if let Some(ref hash) = current {
        if blob_exists(archive, hash) {
            return Ok(());
        }
    }
    if let Some(hash) = sibling_derivative(archive, cas_hash, Some(attachment_id))? {
        point_derivative(archive, attachment_id, &hash, current.as_deref())?;
        return Ok(());
    }
    let original = match crate::cas::cas_get(archive, cas_hash) {
        Ok(bytes) => bytes,
        Err(_) => return Ok(()),
    };
    let path = crate::cas::cas_blob_path(&archive.root, cas_hash).ok();
    let Some((still, mime_hint)) =
        still_for_bytes(&original, filename, mime, kind, path.as_deref())
    else {
        archive.conn.execute(
            "UPDATE attachments SET derivative_cas_hash = NULL WHERE id = ?1",
            [attachment_id],
        )?;
        return Ok(());
    };
    let hash = crate::cas::cas_put(archive, &still, Some(mime_hint))?;
    point_derivative(archive, attachment_id, &hash, current.as_deref())?;
    Ok(())
}

pub(crate) fn still_for_bytes(
    bytes: &[u8],
    filename: Option<&str>,
    mime: Option<&str>,
    kind: &str,
    original_path: Option<&Path>,
) -> Option<(Vec<u8>, &'static str)> {
    if !eligible(kind, mime, filename) {
        return None;
    }
    if is_image(kind, mime, filename) {
        if let Some(still) = still_from_image_crate(bytes) {
            return Some(still);
        }
        return platform_image_fallback(bytes, original_path);
    }
    if is_video(kind, mime, filename) {
        return platform_video(bytes, original_path, mime, filename);
    }
    if is_pdf(mime, filename) {
        return platform_pdf(bytes, original_path);
    }
    None
}

pub(crate) fn still_hash_for_new_bytes(
    archive: &Archive,
    cas_hash: &str,
    bytes: &[u8],
    filename: Option<&str>,
    mime: Option<&str>,
    kind: &str,
) -> Result<Option<String>, CoreError> {
    if !eligible(kind, mime, filename) {
        return Ok(None);
    }
    if let Some(hash) = sibling_derivative(archive, cas_hash, None)? {
        return Ok(Some(hash));
    }
    let path = crate::cas::cas_blob_path(&archive.root, cas_hash).ok();
    let Some((still, mime_hint)) = still_for_bytes(bytes, filename, mime, kind, path.as_deref())
    else {
        return Ok(None);
    };
    let hash = crate::cas::cas_put(archive, &still, Some(mime_hint))?;
    Ok(Some(hash))
}

fn is_image(kind: &str, mime: Option<&str>, filename: Option<&str>) -> bool {
    let kind = kind.to_ascii_lowercase();
    let mime = lowered(mime);
    let name = lowered(filename);
    kind == "image"
        || kind == "sticker"
        || mime.starts_with("image/")
        || ends_with_any(
            &name,
            &[
                ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".heic", ".heif",
            ],
        )
}

fn is_video(kind: &str, mime: Option<&str>, filename: Option<&str>) -> bool {
    let kind = kind.to_ascii_lowercase();
    let mime = lowered(mime);
    let name = lowered(filename);
    kind == "video"
        || mime.starts_with("video/")
        || ends_with_any(&name, &[".mp4", ".mov", ".mkv", ".avi", ".webm"])
}

fn is_pdf(mime: Option<&str>, filename: Option<&str>) -> bool {
    let mime = lowered(mime);
    let name = lowered(filename);
    mime == "application/pdf" || name.ends_with(".pdf")
}

fn lowered(value: Option<&str>) -> String {
    value.unwrap_or("").to_ascii_lowercase()
}

fn ends_with_any(name: &str, exts: &[&str]) -> bool {
    exts.iter().any(|ext| name.ends_with(ext))
}

fn blob_exists(archive: &Archive, hash: &str) -> bool {
    crate::cas::cas_blob_path(&archive.root, hash)
        .map(|path| path.is_file())
        .unwrap_or(false)
}

fn current_derivative(archive: &Archive, attachment_id: i64) -> Result<Option<String>, CoreError> {
    let row: Option<Option<String>> = archive
        .conn
        .query_row(
            "SELECT derivative_cas_hash FROM attachments WHERE id = ?1",
            [attachment_id],
            |r| r.get(0),
        )
        .optional()?;
    Ok(row.flatten())
}

fn sibling_derivative(
    archive: &Archive,
    cas_hash: &str,
    skip_id: Option<i64>,
) -> Result<Option<String>, CoreError> {
    let mut stmt = archive.conn.prepare(
        "SELECT id, derivative_cas_hash FROM attachments
         WHERE cas_hash = ?1 AND derivative_cas_hash IS NOT NULL",
    )?;
    let mapped = stmt.query_map([cas_hash], |r| {
        Ok((r.get::<_, i64>(0)?, r.get::<_, String>(1)?))
    })?;
    let mut rows = Vec::new();
    for row in mapped {
        rows.push(row?);
    }
    drop(stmt);
    for (id, hash) in rows {
        if skip_id == Some(id) {
            continue;
        }
        if blob_exists(archive, &hash) {
            return Ok(Some(hash));
        }
    }
    Ok(None)
}

fn point_derivative(
    archive: &Archive,
    attachment_id: i64,
    hash: &str,
    previous: Option<&str>,
) -> Result<(), CoreError> {
    archive.conn.execute(
        "UPDATE attachments SET derivative_cas_hash = ?1 WHERE id = ?2",
        rusqlite::params![hash, attachment_id],
    )?;
    if previous != Some(hash) {
        archive.conn.execute(
            "UPDATE cas_blobs SET refcount = refcount + 1 WHERE hash = ?1",
            [hash],
        )?;
    }
    Ok(())
}

fn still_from_image_crate(bytes: &[u8]) -> Option<(Vec<u8>, &'static str)> {
    use image::ImageDecoder;

    // `load_from_memory` leaves EXIF orientation to the viewer. Bake it into
    // the pixels so the still carries no orientation tag.
    let reader = image::ImageReader::new(std::io::Cursor::new(bytes))
        .with_guessed_format()
        .ok()?;
    let mut decoder = reader.into_decoder().ok()?;
    let orientation = decoder
        .orientation()
        .unwrap_or(image::metadata::Orientation::NoTransforms);
    let mut img = image::DynamicImage::from_decoder(decoder).ok()?;
    img.apply_orientation(orientation);
    encode_dynamic(img, bytes)
}

fn encode_dynamic(img: image::DynamicImage, original: &[u8]) -> Option<(Vec<u8>, &'static str)> {
    let has_alpha = img.color().has_alpha();
    let img = fit_edge(img);
    if has_alpha {
        encode_png(img, original)
    } else {
        encode_jpeg(img, original)
    }
}

fn encode_png(img: image::DynamicImage, original: &[u8]) -> Option<(Vec<u8>, &'static str)> {
    use image::ImageEncoder;
    let rgba = img.to_rgba8();
    let mut buf = Vec::new();
    image::codecs::png::PngEncoder::new(&mut buf)
        .write_image(
            rgba.as_raw(),
            rgba.width(),
            rgba.height(),
            image::ExtendedColorType::Rgba8,
        )
        .ok()?;
    if buf.as_slice() == original {
        return None;
    }
    Some((buf, "image/png"))
}

fn encode_jpeg(img: image::DynamicImage, original: &[u8]) -> Option<(Vec<u8>, &'static str)> {
    let rgb = img.to_rgb8();
    let mut buf = Vec::new();
    image::codecs::jpeg::JpegEncoder::new_with_quality(&mut buf, 80)
        .encode(
            rgb.as_raw(),
            rgb.width(),
            rgb.height(),
            image::ExtendedColorType::Rgb8,
        )
        .ok()?;
    if buf.as_slice() == original {
        return None;
    }
    Some((buf, "image/jpeg"))
}

fn fit_edge(img: image::DynamicImage) -> image::DynamicImage {
    let width = img.width();
    let height = img.height();
    if width.max(height) <= STILL_EDGE {
        return img;
    }
    let (nw, nh) = if width >= height {
        let nh = u32::max(
            1,
            ((u64::from(height) * u64::from(STILL_EDGE)) / u64::from(width)) as u32,
        );
        (STILL_EDGE, nh)
    } else {
        let nw = u32::max(
            1,
            ((u64::from(width) * u64::from(STILL_EDGE)) / u64::from(height)) as u32,
        );
        (nw, STILL_EDGE)
    };
    img.resize(nw, nh, image::imageops::FilterType::Triangle)
}

#[cfg(not(target_os = "macos"))]
fn platform_image_fallback(_bytes: &[u8], _path: Option<&Path>) -> Option<(Vec<u8>, &'static str)> {
    None
}

#[cfg(not(target_os = "macos"))]
fn platform_video(
    _bytes: &[u8],
    _path: Option<&Path>,
    _mime: Option<&str>,
    _filename: Option<&str>,
) -> Option<(Vec<u8>, &'static str)> {
    None
}

#[cfg(not(target_os = "macos"))]
fn platform_pdf(_bytes: &[u8], _path: Option<&Path>) -> Option<(Vec<u8>, &'static str)> {
    None
}

/// ImageIO bitmaps are premultiplied. JPEG and PNG stills store straight alpha.
#[cfg(target_os = "macos")]
fn straight_alpha(img: image::DynamicImage) -> (image::DynamicImage, bool) {
    let mut rgba = img.into_rgba8();
    let mut opaque = true;
    for px in rgba.pixels_mut() {
        let alpha = px.0[3];
        if alpha != 255 {
            opaque = false;
        }
        if alpha == 0 || alpha == 255 {
            continue;
        }
        let alpha = u32::from(alpha);
        for channel in &mut px.0[..3] {
            let straight = u32::from(*channel) * 255 / alpha;
            *channel = u8::try_from(straight).unwrap_or(255);
        }
    }
    (image::DynamicImage::ImageRgba8(rgba), opaque)
}

#[cfg(target_os = "macos")]
fn platform_image_fallback(bytes: &[u8], path: Option<&Path>) -> Option<(Vec<u8>, &'static str)> {
    let rgba = macos::imageio_rgba(path?)?;
    let (straight, opaque) = straight_alpha(fit_edge(image::DynamicImage::ImageRgba8(rgba)));
    if opaque {
        encode_jpeg(straight, bytes)
    } else {
        encode_png(straight, bytes)
    }
}

#[cfg(target_os = "macos")]
fn platform_video(
    original: &[u8],
    path: Option<&Path>,
    mime: Option<&str>,
    filename: Option<&str>,
) -> Option<(Vec<u8>, &'static str)> {
    let path = path?;
    let rgba = macos::video_rgba(path, &video_mime_hint(mime, filename))?;
    // ImageRgba8 reports alpha, so encode_dynamic would emit a PNG. Posters are JPEG.
    let img = fit_edge(image::DynamicImage::ImageRgba8(rgba));
    encode_jpeg(img, original)
}

#[cfg(target_os = "macos")]
fn video_mime_hint(mime: Option<&str>, filename: Option<&str>) -> String {
    if let Some(mime) = mime {
        let trimmed = mime.trim();
        if trimmed.to_ascii_lowercase().starts_with("video/") {
            return trimmed.to_string();
        }
    }
    let name = filename.unwrap_or("").to_ascii_lowercase();
    if name.ends_with(".mov") {
        "video/quicktime".to_string()
    } else if name.ends_with(".webm") {
        "video/webm".to_string()
    } else if name.ends_with(".mkv") {
        "video/x-matroska".to_string()
    } else if name.ends_with(".avi") {
        "video/x-msvideo".to_string()
    } else {
        "video/mp4".to_string()
    }
}

#[cfg(target_os = "macos")]
fn platform_pdf(original: &[u8], path: Option<&Path>) -> Option<(Vec<u8>, &'static str)> {
    let path = path?;
    let rgba = macos::pdf_rgba(path)?;
    encode_jpeg(image::DynamicImage::ImageRgba8(rgba), original)
}

#[cfg(target_os = "macos")]
mod macos {
    use std::path::Path;

    use image::RgbaImage;
    use objc2::runtime::AnyObject;
    use objc2::ClassType;
    use objc2_av_foundation::{AVAssetImageGenerator, AVURLAsset, AVURLAssetOverrideMIMETypeKey};
    use objc2_core_foundation::{
        CFBoolean, CFDictionary, CFNumber, CFType, CGPoint, CGRect, CGSize, CFURL,
    };
    use objc2_core_graphics::{
        CGBitmapContextCreate, CGBitmapContextGetBytesPerRow, CGBitmapContextGetData, CGColorSpace,
        CGContext, CGImage, CGImageAlphaInfo, CGImageByteOrderInfo, CGPDFBox, CGPDFDocument,
        CGPDFPage,
    };
    use objc2_core_media::{CMTime, CMTimeFlags};
    use objc2_foundation::{NSDictionary, NSString, NSURL};
    use objc2_image_io::{
        kCGImageSourceCreateThumbnailFromImageAlways, kCGImageSourceCreateThumbnailWithTransform,
        kCGImageSourceThumbnailMaxPixelSize,
    };

    pub(super) fn imageio_rgba(path: &Path) -> Option<RgbaImage> {
        let url = CFURL::from_file_path(path)?;
        // SAFETY: `url` is a file URL for a CAS blob. Source options are unused.
        let src = unsafe { objc2_image_io::CGImageSource::with_url(&url, None) }?;
        // SAFETY: the primary index is the image ImageIO marks current. HEIF may not be 0.
        let index = unsafe { src.primary_image_index() };
        let opts = thumbnail_options();
        // SAFETY: option keys are ImageIO thumbnail CFStrings. Values are CFBoolean or
        // CFNumber. `as_opaque` only erases those CF types for `thumbnail_at_index`.
        let cg = unsafe { src.thumbnail_at_index(index, Some(opts.as_opaque())) }?;
        cgimage_rgba(&cg)
    }

    fn thumbnail_options() -> objc2_core_foundation::CFRetained<CFDictionary<CFType, CFType>> {
        let max_px = CFNumber::new_i32(480);
        // SAFETY: these ImageIO keys are process-lifetime CFStrings.
        let keys: [&CFType; 3] = unsafe {
            [
                kCGImageSourceCreateThumbnailFromImageAlways.as_ref(),
                kCGImageSourceCreateThumbnailWithTransform.as_ref(),
                kCGImageSourceThumbnailMaxPixelSize.as_ref(),
            ]
        };
        let values: [&CFType; 3] = [
            CFBoolean::new(true).as_ref(),
            CFBoolean::new(true).as_ref(),
            max_px.as_ref(),
        ];
        CFDictionary::from_slices(&keys, &values)
    }

    pub(super) fn video_rgba(path: &Path, mime_hint: &str) -> Option<RgbaImage> {
        let path_str = path.to_str()?;
        let url = NSURL::fileURLWithPath(&NSString::from_str(path_str));
        // CAS paths have no extension. Without a MIME hint AVFoundation reports
        // file-format-not-recognized (-11828) for an otherwise valid MP4.
        let mime = NSString::from_str(mime_hint);
        let key = unsafe { AVURLAssetOverrideMIMETypeKey };
        let value: &AnyObject = &mime;
        let opts = NSDictionary::<NSString, AnyObject>::from_slices(&[key], &[value]);
        // SAFETY: `url` is a file URL. The MIME override is an NSString. The asset outlives the generator.
        let asset = unsafe { AVURLAsset::URLAssetWithURL_options(&url, Some(&opts)) };
        let gen = unsafe { AVAssetImageGenerator::assetImageGeneratorWithAsset(asset.as_super()) };
        unsafe { gen.setAppliesPreferredTrackTransform(true) };
        let time = CMTime {
            value: 0,
            timescale: 1,
            flags: CMTimeFlags::Valid,
            epoch: 0,
        };
        // SAFETY: a null actual-time pointer is allowed; the caller ignores the snapped time.
        // `copyCGImageAtTime` is the synchronous frame API this crate pins.
        #[allow(deprecated)]
        let cg =
            unsafe { gen.copyCGImageAtTime_actualTime_error(time, std::ptr::null_mut()) }.ok()?;
        cgimage_rgba(&cg)
    }

    pub(super) fn pdf_rgba(path: &Path) -> Option<RgbaImage> {
        let url = CFURL::from_file_path(path)?;
        let doc = CGPDFDocument::with_url(Some(&url))?;
        // CoreGraphics PDF pages are 1-based. Page 1 is the first page.
        let page = CGPDFDocument::page(Some(&doc), 1)?;
        let media = CGPDFPage::box_rect(Some(&page), CGPDFBox::MediaBox);
        let (tw, th) = fit_pdf_px(media.size.width, media.size.height)?;
        let ctx = bitmap_context(tw, th)?;
        let ctx_ref: &CGContext = &ctx;
        let dest = CGRect {
            origin: CGPoint::new(0.0, 0.0),
            size: CGSize::new(f64::from(tw), f64::from(th)),
        };
        CGContext::set_rgb_fill_color(Some(ctx_ref), 1.0, 1.0, 1.0, 1.0);
        CGContext::fill_rect(Some(ctx_ref), dest);
        let transform =
            CGPDFPage::drawing_transform(Some(&page), CGPDFBox::MediaBox, dest, 0, true);
        CGContext::concat_ctm(Some(ctx_ref), transform);
        CGContext::draw_pdf_page(Some(ctx_ref), Some(&page));
        rgba_from_context(ctx_ref, tw, th)
    }

    fn bitmap_info() -> u32 {
        CGImageAlphaInfo::PremultipliedLast.0 | CGImageByteOrderInfo::Order32Big.0
    }

    fn bitmap_context(
        width: u32,
        height: u32,
    ) -> Option<objc2_core_foundation::CFRetained<CGContext>> {
        let raw_w = usize::try_from(width).ok()?;
        let raw_h = usize::try_from(height).ok()?;
        let row = raw_w.checked_mul(4)?;
        let space = CGColorSpace::new_device_rgb()?;
        // SAFETY: a null data pointer asks CoreGraphics to allocate the buffer.
        unsafe {
            CGBitmapContextCreate(
                std::ptr::null_mut(),
                raw_w,
                raw_h,
                8,
                row,
                Some(&*space),
                bitmap_info(),
            )
        }
    }

    fn cgimage_rgba(cg: &CGImage) -> Option<RgbaImage> {
        let width = CGImage::width(Some(cg));
        let height = CGImage::height(Some(cg));
        let tw = u32::try_from(width).ok()?;
        let th = u32::try_from(height).ok()?;
        if tw == 0 || th == 0 {
            return None;
        }
        let ctx = bitmap_context(tw, th)?;
        let ctx_ref: &CGContext = &ctx;
        let rect = CGRect {
            origin: CGPoint::new(0.0, 0.0),
            size: CGSize::new(width as f64, height as f64),
        };
        CGContext::draw_image(Some(ctx_ref), rect, Some(cg));
        rgba_from_context(ctx_ref, tw, th)
    }

    fn rgba_from_context(ctx: &CGContext, width: u32, height: u32) -> Option<RgbaImage> {
        let ptr = CGBitmapContextGetData(Some(ctx));
        if ptr.is_null() {
            return None;
        }
        let stride = CGBitmapContextGetBytesPerRow(Some(ctx));
        let row_bytes = usize::try_from(width).ok()?.checked_mul(4)?;
        let rows = usize::try_from(height).ok()?;
        if stride < row_bytes {
            return None;
        }
        let len = stride.checked_mul(rows)?;
        // SAFETY: `ptr` is the context's pixel buffer and stays alive while `ctx` is borrowed.
        let slice = unsafe { std::slice::from_raw_parts(ptr.cast::<u8>(), len) };
        let mut packed = Vec::with_capacity(row_bytes.checked_mul(rows)?);
        for y in 0..rows {
            let start = y * stride;
            packed.extend_from_slice(slice.get(start..start + row_bytes)?);
        }
        RgbaImage::from_raw(width, height, packed)
    }

    fn fit_pdf_px(width: f64, height: f64) -> Option<(u32, u32)> {
        if !width.is_finite() || !height.is_finite() || width <= 0.0 || height <= 0.0 {
            return None;
        }
        let longest = width.max(height);
        let scale = if longest > 480.0 {
            480.0 / longest
        } else {
            1.0
        };
        let tw = (width * scale).round().clamp(1.0, 480.0);
        let th = (height * scale).round().clamp(1.0, 480.0);
        Some((tw as u32, th as u32))
    }
}
