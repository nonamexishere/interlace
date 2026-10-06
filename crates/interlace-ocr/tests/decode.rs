use std::path::Path;

use interlace_ocr::text_from_image;

#[test]
fn garbage_is_none() {
    let got = text_from_image(b"not-an-image", Path::new("/no/such/tur.traineddata")).unwrap();
    assert!(got.is_none());
}

#[test]
fn png_missing_weights_is_none() {
    let image = image::DynamicImage::ImageRgba8(image::RgbaImage::from_pixel(
        8,
        8,
        image::Rgba([9, 9, 9, 255]),
    ));
    let mut png = Vec::new();
    image
        .write_to(&mut std::io::Cursor::new(&mut png), image::ImageFormat::Png)
        .unwrap();
    let got = text_from_image(&png, Path::new("/no/such/tur.traineddata")).unwrap();
    assert!(got.is_none());
}
