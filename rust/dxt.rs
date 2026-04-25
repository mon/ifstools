//! DXT1 / DXT5 decoders for Konami's byte-swapped texture format.
//!
//! Konami stores standard DXT-compressed pixel data with each 16-bit word's
//! bytes swapped. Standard DDS/PIL/texpresso expect the canonical little-endian
//! layout, so we un-swap before handing the bytes off to texpresso.

use texpresso::Format;

#[derive(Debug)]
pub enum DxtError {
    UnknownFormat(String),
    SizeMismatch {
        expected: usize,
        got: usize,
        format: &'static str,
    },
    OddByteCount(usize),
}

impl std::fmt::Display for DxtError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            DxtError::UnknownFormat(s) => write!(f, "unknown DXT format: {}", s),
            DxtError::SizeMismatch { expected, got, format } => write!(
                f,
                "{}: expected {} compressed bytes, got {}",
                format, expected, got
            ),
            DxtError::OddByteCount(n) => write!(f, "input length {} is not a multiple of 2", n),
        }
    }
}

impl std::error::Error for DxtError {}

fn parse_format(s: &str) -> Result<(Format, &'static str), DxtError> {
    match s {
        "dxt1" | "DXT1" | "bc1" => Ok((Format::Bc1, "DXT1")),
        "dxt3" | "DXT3" | "bc2" => Ok((Format::Bc2, "DXT3")),
        "dxt5" | "DXT5" | "bc3" => Ok((Format::Bc3, "DXT5")),
        other => Err(DxtError::UnknownFormat(other.to_string())),
    }
}

/// Decode Konami-format DXT data into raw RGBA8 pixels (`width * height * 4`
/// bytes). Pads short input with zero bytes to match the prior Python
/// behaviour, which warns and continues rather than failing on truncated
/// textures.
pub fn decode(
    data: &[u8],
    width: usize,
    height: usize,
    format: &str,
) -> Result<Vec<u8>, DxtError> {
    let (fmt, fmt_name) = parse_format(format)?;
    if data.len() % 2 != 0 {
        return Err(DxtError::OddByteCount(data.len()));
    }

    let expected = fmt.compressed_size(width, height);

    // Konami's per-WORD byte swap, with zero padding if the source is short.
    let mut swapped = vec![0u8; expected];
    let n = data.len().min(expected);
    let pairs = n / 2;
    for i in 0..pairs {
        swapped[i * 2] = data[i * 2 + 1];
        swapped[i * 2 + 1] = data[i * 2];
    }
    if n % 2 != 0 {
        // Trailing odd byte (only possible when source is shorter than expected).
        swapped[n - 1] = data[n - 1];
    }
    let _ = fmt_name; // currently only used for error formatting

    let mut rgba = vec![0u8; width * height * 4];
    fmt.decompress(&swapped, width, height, &mut rgba);
    Ok(rgba)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn dxt5_smoke() {
        // Single 4x4 DXT5 block: alpha 0xFF, RGB midgray.
        // Standard DXT5 layout (little-endian within blocks):
        //   alpha0 alpha1 [6 bytes alpha indices] [color block 8 bytes]
        // We Konami-swap it (per u16) before feeding to decode().
        let canonical = [
            0xFFu8, 0xFF, // both alpha endpoints = 255
            0, 0, 0, 0, 0, 0, // alpha indices (all zero → endpoint 0 = 255 everywhere)
            0xFF, 0x7F, 0xFF, 0x7F, // both colors = 0x7FFF (ish gray)
            0, 0, 0, 0,
        ];
        let mut konami = canonical;
        for chunk in konami.chunks_exact_mut(2) {
            chunk.swap(0, 1);
        }
        let rgba = decode(&konami, 4, 4, "dxt5").unwrap();
        assert_eq!(rgba.len(), 4 * 4 * 4);
        // Alpha should be 0xFF everywhere.
        for px in rgba.chunks_exact(4) {
            assert_eq!(px[3], 0xFF, "alpha not opaque: {:?}", px);
        }
    }

    #[test]
    fn unknown_format_errors() {
        assert!(decode(&[0; 16], 4, 4, "garbage").is_err());
    }
}
