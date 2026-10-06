use std::path::{Path, PathBuf};

fn main() {
    let manifest = PathBuf::from(std::env::var("CARGO_MANIFEST_DIR").unwrap());
    let vendor = manifest.join("vendor");
    println!("cargo:rerun-if-changed=build.rs");
    println!("cargo:rerun-if-changed=vendor/shim/ocr.cpp");

    let lept = cmake::Config::new(vendor.join("leptonica"))
        .profile("Release")
        .define("CMAKE_POLICY_VERSION_MINIMUM", "3.5")
        .define("CMAKE_INSTALL_LIBDIR", "lib")
        .define("CMAKE_POSITION_INDEPENDENT_CODE", "ON")
        .define("BUILD_SHARED_LIBS", "OFF")
        .define("BUILD_PROG", "OFF")
        .define("SW_BUILD", "OFF")
        .define("ENABLE_ZLIB", "ON")
        .define("ENABLE_PNG", "OFF")
        .define("ENABLE_GIF", "OFF")
        .define("ENABLE_JPEG", "OFF")
        .define("ENABLE_TIFF", "OFF")
        .define("ENABLE_WEBP", "OFF")
        .define("ENABLE_OPENJPEG", "OFF")
        .build();

    let lept_cmake = find_file(&lept, "LeptonicaConfig.cmake")
        .and_then(|p| p.parent().map(|p| p.to_path_buf()))
        .unwrap_or_else(|| panic!("LeptonicaConfig.cmake missing under {}", lept.display()));

    let tess = cmake::Config::new(vendor.join("tesseract"))
        .profile("Release")
        .define("CMAKE_POLICY_VERSION_MINIMUM", "3.5")
        .define("CMAKE_INSTALL_LIBDIR", "lib")
        .define("CMAKE_PREFIX_PATH", lept.as_os_str())
        .define("Leptonica_DIR", lept_cmake.as_os_str())
        .define("CMAKE_POSITION_INDEPENDENT_CODE", "ON")
        .define("BUILD_SHARED_LIBS", "OFF")
        .define("BUILD_TRAINING_TOOLS", "OFF")
        .define("BUILD_TESTS", "OFF")
        .define("SW_BUILD", "OFF")
        .define("OPENMP_BUILD", "OFF")
        .define("ENABLE_NATIVE", "OFF")
        .define("GRAPHICS_DISABLED", "ON")
        .define("INSTALL_CONFIGS", "OFF")
        .define("DISABLE_CURL", "ON")
        .define("DISABLE_ARCHIVE", "ON")
        .define("DISABLE_TIFF", "ON")
        .build();

    cc::Build::new()
        .cpp(true)
        .file(vendor.join("shim/ocr.cpp"))
        .include(tess.join("include"))
        .include(lept.join("include"))
        .flag("-std=c++17")
        .compile("interlace_ocr_shim");

    let tess_lib = lib_dir(&tess, &["libtesseract.a"]);
    let lept_lib = lib_dir(&lept, &["libleptonica.a", "liblept.a"]);
    println!("cargo:rustc-link-search=native={}", tess_lib.display());
    println!("cargo:rustc-link-search=native={}", lept_lib.display());
    println!("cargo:rustc-link-lib=static=tesseract");
    let lept_name = if lept_lib.join("libleptonica.a").is_file() {
        "leptonica"
    } else {
        "lept"
    };
    println!("cargo:rustc-link-lib=static={lept_name}");
    println!("cargo:rustc-link-lib=z");
    if cfg!(target_os = "macos") {
        println!("cargo:rustc-link-lib=c++");
    } else {
        println!("cargo:rustc-link-lib=stdc++");
        println!("cargo:rustc-link-lib=pthread");
        println!("cargo:rustc-link-lib=m");
        println!("cargo:rustc-link-lib=dl");
    }
}

fn find_file(root: &Path, name: &str) -> Option<PathBuf> {
    let mut stack = vec![root.to_path_buf()];
    while let Some(dir) = stack.pop() {
        let Ok(entries) = std::fs::read_dir(&dir) else {
            continue;
        };
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_dir() {
                stack.push(path);
            } else if path.file_name().and_then(|s| s.to_str()) == Some(name) {
                return Some(path);
            }
        }
    }
    None
}

fn lib_dir(prefix: &Path, archives: &[&str]) -> PathBuf {
    for name in ["lib", "lib64"] {
        let dir = prefix.join(name);
        if archives.iter().any(|a| dir.join(a).is_file()) {
            return dir;
        }
    }
    for archive in archives {
        if let Some(path) = find_file(prefix, archive) {
            if let Some(parent) = path.parent() {
                return parent.to_path_buf();
            }
        }
    }
    panic!("missing {:?} under {}", archives, prefix.display());
}
