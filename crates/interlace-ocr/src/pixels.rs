use image::RgbaImage;

pub fn decode_rgba(bytes: &[u8]) -> Option<RgbaImage> {
    if bytes.is_empty() {
        return None;
    }
    if let Some(img) = decode_image_crate(bytes) {
        return Some(img);
    }
    #[cfg(target_os = "macos")]
    {
        decode_imageio(bytes)
    }
    #[cfg(not(target_os = "macos"))]
    {
        None
    }
}

fn decode_image_crate(bytes: &[u8]) -> Option<RgbaImage> {
    use image::ImageDecoder;
    let reader = image::ImageReader::new(std::io::Cursor::new(bytes))
        .with_guessed_format()
        .ok()?;
    let mut decoder = reader.into_decoder().ok()?;
    let orientation = decoder
        .orientation()
        .unwrap_or(image::metadata::Orientation::NoTransforms);
    let mut img = image::DynamicImage::from_decoder(decoder).ok()?;
    img.apply_orientation(orientation);
    Some(img.to_rgba8())
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
    if tw == 0 || th == 0 {
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
