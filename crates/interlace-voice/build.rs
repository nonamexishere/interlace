use std::path::{Path, PathBuf};

fn main() {
    let manifest = PathBuf::from(std::env::var("CARGO_MANIFEST_DIR").unwrap());
    let vendor = manifest.join("vendor");
    println!("cargo:rerun-if-changed=vendor/CMakeLists.txt");
    println!("cargo:rerun-if-changed=vendor/shim/transcribe.cpp");
    println!("cargo:rerun-if-changed=build.rs");

    let dst = cmake::Config::new(&vendor)
        .profile("Release")
        .define("CMAKE_POLICY_VERSION_MINIMUM", "3.5")
        .define("CMAKE_INSTALL_LIBDIR", "lib")
        .define("CMAKE_POSITION_INDEPENDENT_CODE", "ON")
        .define("BUILD_SHARED_LIBS", "OFF")
        .build();

    let lib_dir = find_lib_dir(&dst);
    // libggml-cpu.a contains two members named quants.c.o and two named
    // repack.cpp.o. Extracting by basename drops the generic quants.c.o
    // that defines quantize_row_*. Link the archives and let ld pull members.
    // Left to right: each archive's undefs are satisfied by a later archive.
    for name in [
        "libinterlace_whisper_shim.a",
        "libwhisper.a",
        "libggml.a",
        "libggml-cpu.a",
        "libggml-base.a",
    ] {
        let path = lib_dir.join(name);
        if !path.is_file() {
            panic!("missing {}", path.display());
        }
    }
    println!("cargo:rustc-link-search=native={}", lib_dir.display());
    for lib in [
        "interlace_whisper_shim",
        "whisper",
        "ggml",
        "ggml-cpu",
        "ggml-base",
    ] {
        println!("cargo:rustc-link-lib=static={lib}");
    }
    if cfg!(target_os = "macos") {
        println!("cargo:rustc-link-lib=c++");
    } else {
        println!("cargo:rustc-link-lib=stdc++");
        println!("cargo:rustc-link-lib=pthread");
        println!("cargo:rustc-link-lib=m");
        println!("cargo:rustc-link-lib=dl");
    }
}

fn find_lib_dir(prefix: &Path) -> PathBuf {
    for name in ["lib", "lib64"] {
        let dir = prefix.join(name);
        if dir.join("libggml.a").is_file() && dir.join("libwhisper.a").is_file() {
            return dir;
        }
    }
    panic!(
        "whisper static libraries were not installed under {}",
        prefix.display()
    );
}
