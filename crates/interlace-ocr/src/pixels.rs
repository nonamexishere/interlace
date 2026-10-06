use image::RgbaImage;

enum CrateDecode {
    /// The `image` crate produced pixels.
    Ready(RgbaImage),
    /// Not a format that crate decodes (HEIC, BMP). macOS may try ImageIO.
    Unsupported,
    /// A format the crate knows, and it refused the bytes. Do not decode again.
    Refuse,
}

pub fn decode_rgba(bytes: &[u8]) -> Option<RgbaImage> {
    if bytes.is_empty() {
        return None;
    }
    match decode_image_crate(bytes) {
        CrateDecode::Ready(img) => finite_rgba(img),
        CrateDecode::Refuse => None,
        CrateDecode::Unsupported => decode_unsupported(bytes),
    }
}

/// Leptonica `pixCreate` returns null once a 32-bit image reaches 2^31 bytes.
/// Tesseract then writes through that null pointer and aborts the process.
pub(crate) fn fits_ocr(width: u32, height: u32) -> bool {
    if width == 0 || height == 0 {
        return false;
    }
    let width = u64::from(width);
    let height = u64::from(height);
    // A 32-bit pix uses one word per pixel. Leptonica rejects a row of
    // 2^24 words, or a buffer of 2^31 bytes.
    if width > (1u64 << 24) - 1 {
        return false;
    }
    4 * width * height < (1u64 << 31)
}

fn finite_rgba(img: RgbaImage) -> Option<RgbaImage> {
    if fits_ocr(img.width(), img.height()) {
        Some(img)
    } else {
        None
    }
}

fn decode_image_crate(bytes: &[u8]) -> CrateDecode {
    use image::{ImageDecoder, ImageError};
    let Ok(reader) = image::ImageReader::new(std::io::Cursor::new(bytes)).with_guessed_format()
    else {
        return CrateDecode::Refuse;
    };
    let mut decoder = match reader.into_decoder() {
        Ok(decoder) => decoder,
        Err(ImageError::Unsupported(_)) => return CrateDecode::Unsupported,
        Err(_) => return CrateDecode::Refuse,
    };
    let orientation = decoder
        .orientation()
        .unwrap_or(image::metadata::Orientation::NoTransforms);
    let mut img = match image::DynamicImage::from_decoder(decoder) {
        Ok(img) => img,
        Err(ImageError::Unsupported(_)) => return CrateDecode::Unsupported,
        Err(_) => return CrateDecode::Refuse,
    };
    img.apply_orientation(orientation);
    CrateDecode::Ready(img.to_rgba8())
}

#[cfg(target_os = "macos")]
fn decode_unsupported(bytes: &[u8]) -> Option<RgbaImage> {
    decode_imageio(bytes).and_then(finite_rgba)
}

#[cfg(not(target_os = "macos"))]
fn decode_unsupported(_bytes: &[u8]) -> Option<RgbaImage> {
    None
}

#[cfg(target_os = "macos")]
fn decode_imageio(bytes: &[u8]) -> Option<RgbaImage> {
    use objc2_core_foundation::CFData;
    use objc2_image_io::CGImageSource;

    let data = CFData::from_bytes(bytes);
    let src = unsafe { CGImageSource::with_data(&data, None) }?;
    let index = unsafe { src.primary_image_index() };
    let cg = unsafe { src.image_at_index(index, None) }?;
    let orientation = imageio_orientation(&src, index);
    let rgba = cgimage_rgba(&cg)?;
    let mut img = image::DynamicImage::ImageRgba8(rgba);
    if let Some(orientation) = image::metadata::Orientation::from_exif(orientation) {
        img.apply_orientation(orientation);
    }
    Some(img.to_rgba8())
}

#[cfg(target_os = "macos")]
fn imageio_orientation(src: &objc2_image_io::CGImageSource, index: usize) -> u8 {
    use objc2_core_foundation::CFNumber;
    use objc2_image_io::kCGImagePropertyOrientation;
    let Some(props) = (unsafe { src.properties_at_index(index, None) }) else {
        return 1;
    };
    let key = std::ptr::from_ref(unsafe { kCGImagePropertyOrientation }).cast::<std::ffi::c_void>();
    let raw = unsafe { props.value(key) };
    if raw.is_null() {
        return 1;
    }
    let num = unsafe { &*raw.cast::<CFNumber>() };
    num.as_i32()
        .and_then(|n| u8::try_from(n).ok())
        .filter(|n| (1..=8).contains(n))
        .unwrap_or(1)
}

#[cfg(target_os = "macos")]
fn bitmap_info() -> u32 {
    use objc2_core_graphics::{CGImageAlphaInfo, CGImageByteOrderInfo};
    CGImageAlphaInfo::PremultipliedLast.0 | CGImageByteOrderInfo::Order32Big.0
}

#[cfg(target_os = "macos")]
fn cgimage_rgba(cg: &objc2_core_graphics::CGImage) -> Option<RgbaImage> {
    use objc2_core_foundation::{CFRetained, CGPoint, CGRect, CGSize};
    use objc2_core_graphics::{
        CGBitmapContextCreate, CGBitmapContextGetBytesPerRow, CGBitmapContextGetData, CGColorSpace,
        CGContext, CGImage,
    };
    let width = CGImage::width(Some(cg));
    let height = CGImage::height(Some(cg));
    let tw = u32::try_from(width).ok()?;
    let th = u32::try_from(height).ok()?;
    if !fits_ocr(tw, th) {
        return None;
    }
    let raw_w = usize::try_from(tw).ok()?;
    let raw_h = usize::try_from(th).ok()?;
    let row = raw_w.checked_mul(4)?;
    let space = CGColorSpace::new_device_rgb()?;
    let ctx: CFRetained<CGContext> = unsafe {
        CGBitmapContextCreate(
            std::ptr::null_mut(),
            raw_w,
            raw_h,
            8,
            row,
            Some(&*space),
            bitmap_info(),
        )
    }?;
    let ctx_ref: &CGContext = &ctx;
    let rect = CGRect {
        origin: CGPoint::new(0.0, 0.0),
        size: CGSize::new(width as f64, height as f64),
    };
    CGContext::draw_image(Some(ctx_ref), rect, Some(cg));
    let ptr = CGBitmapContextGetData(Some(ctx_ref));
    if ptr.is_null() {
        return None;
    }
    let stride = CGBitmapContextGetBytesPerRow(Some(ctx_ref));
    let row_bytes = raw_w.checked_mul(4)?;
    if stride < row_bytes {
        return None;
    }
    let len = stride.checked_mul(raw_h)?;
    let slice = unsafe { std::slice::from_raw_parts(ptr.cast::<u8>(), len) };
    let mut packed = Vec::with_capacity(row_bytes.checked_mul(raw_h)?);
    for y in 0..raw_h {
        let start = y * stride;
        packed.extend_from_slice(slice.get(start..start + row_bytes)?);
    }
    RgbaImage::from_raw(tw, th, packed)
}

#[cfg(test)]
mod tests {
    use super::{decode_image_crate, decode_rgba, fits_ocr, CrateDecode};

    #[test]
    fn small_photo_fits_and_a_two_gib_bitmap_does_not() {
        assert!(fits_ocr(8, 8));
        assert!(fits_ocr(4_000, 3_000));
        // 23170² × 4 = 2,147,395,600 ≤ 2^31 − 1. 23171² × 4 crosses it.
        assert!(fits_ocr(23_170, 23_170));
        assert!(!fits_ocr(23_171, 23_171));
        // pixCreateHeader also rejects a row wider than 2^24 − 1 words.
        assert!(!fits_ocr(1 << 24, 1));
        assert!(!fits_ocr(0, 8));
    }

    #[test]
    fn tiny_png_decodes_and_a_huge_png_is_refused() {
        let tiny = image::DynamicImage::ImageRgba8(image::RgbaImage::from_pixel(
            8,
            8,
            image::Rgba([9, 9, 9, 255]),
        ));
        let mut png = Vec::new();
        tiny.write_to(&mut std::io::Cursor::new(&mut png), image::ImageFormat::Png)
            .unwrap();
        assert!(matches!(decode_image_crate(&png), CrateDecode::Ready(_)));
        assert_eq!(
            decode_rgba(&png).map(|img| (img.width(), img.height())),
            Some((8, 8))
        );

        let huge = png_ihdr(40_000, 40_000);
        assert!(
            matches!(decode_image_crate(&huge), CrateDecode::Refuse),
            "a png the image crate rejects must not fall through to ImageIO"
        );
        assert!(decode_rgba(&huge).is_none());
    }

    #[test]
    fn bytes_the_crate_does_not_decode_stay_unsupported() {
        assert!(matches!(
            decode_image_crate(b"not-an-image"),
            CrateDecode::Unsupported
        ));
        assert!(decode_rgba(b"not-an-image").is_none());
        // BMP is recognized and intentionally not linked into the image crate.
        let bmp = bmp32(2, 2, &[0u8; 16]);
        assert!(matches!(decode_image_crate(&bmp), CrateDecode::Unsupported));
    }

    #[cfg(target_os = "macos")]
    #[test]
    fn imageio_reads_a_small_bmp() {
        let small = bmp32(2, 2, &[0u8; 16]);
        assert_eq!(
            decode_rgba(&small).map(|img| (img.width(), img.height())),
            Some((2, 2))
        );
    }

    #[cfg(target_os = "macos")]
    #[test]
    fn imageio_refuses_a_bmp_leptonica_cannot_allocate() {
        let huge = bmp32(23_171, 23_171, &[]);
        assert!(decode_rgba(&huge).is_none());
    }

    fn png_ihdr(width: u32, height: u32) -> Vec<u8> {
        let mut data = Vec::with_capacity(13);
        data.extend(width.to_be_bytes());
        data.extend(height.to_be_bytes());
        data.extend_from_slice(&[8, 6, 0, 0, 0]);
        let mut out = vec![0x89, b'P', b'N', b'G', b'\r', b'\n', 0x1a, b'\n'];
        out.extend(png_chunk(b"IHDR", &data));
        out.extend(png_chunk(b"IEND", &[]));
        out
    }

    fn png_chunk(kind: &[u8; 4], data: &[u8]) -> Vec<u8> {
        let mut chunk = Vec::new();
        chunk.extend(u32::try_from(data.len()).unwrap().to_be_bytes());
        chunk.extend_from_slice(kind);
        chunk.extend_from_slice(data);
        let mut crc_src = kind.to_vec();
        crc_src.extend_from_slice(data);
        chunk.extend(crc32(&crc_src).to_be_bytes());
        chunk
    }

    fn crc32(data: &[u8]) -> u32 {
        let mut crc = 0xFFFF_FFFF;
        for &byte in data {
            crc ^= u32::from(byte);
            for _ in 0..8 {
                let mask = (crc & 1).wrapping_neg();
                crc = (crc >> 1) ^ (0xEDB8_8320 & mask);
            }
        }
        !crc
    }

    fn bmp32(width: i32, height: i32, pixels: &[u8]) -> Vec<u8> {
        let offset = 54u32;
        let image_size = u32::try_from(pixels.len()).unwrap();
        let mut out = Vec::new();
        out.extend_from_slice(b"BM");
        out.extend((offset + image_size).to_le_bytes());
        out.extend(0u32.to_le_bytes());
        out.extend(offset.to_le_bytes());
        out.extend(40u32.to_le_bytes());
        out.extend(width.to_le_bytes());
        out.extend(height.to_le_bytes());
        out.extend(1u16.to_le_bytes());
        out.extend(32u16.to_le_bytes());
        out.extend(0u32.to_le_bytes());
        out.extend(image_size.to_le_bytes());
        out.extend(0u32.to_le_bytes());
        out.extend(0u32.to_le_bytes());
        out.extend(0u32.to_le_bytes());
        out.extend(0u32.to_le_bytes());
        out.extend_from_slice(pixels);
        out
    }
}
