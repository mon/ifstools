//! Thin wrapper over the `png` crate for fast PNG encoding from raw pixel
//! buffers. Used in place of Pillow's PNG path during IFS extraction.

use png::{BitDepth, ColorType, Encoder};

#[derive(Debug)]
pub enum EncodeError {
    UnknownColorType(String),
    SizeMismatch { expected: usize, got: usize },
    Png(png::EncodingError),
}

impl std::fmt::Display for EncodeError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            EncodeError::UnknownColorType(s) => write!(f, "unknown color type: {}", s),
            EncodeError::SizeMismatch { expected, got } => write!(
                f,
                "pixel buffer size mismatch (expected {} bytes, got {})",
                expected, got
            ),
            EncodeError::Png(e) => write!(f, "png error: {}", e),
        }
    }
}

impl std::error::Error for EncodeError {}

impl From<png::EncodingError> for EncodeError {
    fn from(e: png::EncodingError) -> Self {
        EncodeError::Png(e)
    }
}

fn parse_color(s: &str) -> Result<(ColorType, usize), EncodeError> {
    match s {
        "rgba" | "RGBA" => Ok((ColorType::Rgba, 4)),
        "rgb" | "RGB" => Ok((ColorType::Rgb, 3)),
        "la" | "LA" => Ok((ColorType::GrayscaleAlpha, 2)),
        "l" | "L" => Ok((ColorType::Grayscale, 1)),
        other => Err(EncodeError::UnknownColorType(other.to_string())),
    }
}

pub fn encode(
    width: u32,
    height: u32,
    pixels: &[u8],
    color: &str,
) -> Result<Vec<u8>, EncodeError> {
    let (ct, bpp) = parse_color(color)?;
    let expected = (width as usize) * (height as usize) * bpp;
    if pixels.len() != expected {
        return Err(EncodeError::SizeMismatch {
            expected,
            got: pixels.len(),
        });
    }

    // Reasonable starting capacity: assume PNG is no larger than raw pixels.
    let mut out = Vec::with_capacity(pixels.len());
    {
        let mut encoder = Encoder::new(&mut out, width, height);
        encoder.set_color(ct);
        encoder.set_depth(BitDepth::Eight);
        encoder.set_compression(png::Compression::Balanced);
        let mut writer = encoder.write_header()?;
        writer.write_image_data(pixels)?;
    }
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rgba_smoke() {
        let pixels: Vec<u8> = (0..4 * 4 * 4).map(|i| i as u8).collect();
        let png = encode(4, 4, &pixels, "rgba").unwrap();
        // PNG signature.
        assert_eq!(&png[..8], &[137, 80, 78, 71, 13, 10, 26, 10]);
    }

    #[test]
    fn size_mismatch_errors() {
        let pixels = vec![0u8; 16];
        assert!(encode(4, 4, &pixels, "rgba").is_err());
    }
}
