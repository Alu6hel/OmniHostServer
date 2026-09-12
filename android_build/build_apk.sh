#!/bin/bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$DIR")"

echo "=== Building OmniHost Pro Standalone Native Android APK ==="

ANDROID_JAR="/home/davidalujones/Android/Sdk/platforms/android-36/android.jar"
BUILD_TOOLS="/home/davidalujones/Android/Sdk/build-tools/36.1.0"
AAPT2="$BUILD_TOOLS/aapt2"
D8="$BUILD_TOOLS/d8"
ZIPALIGN="$BUILD_TOOLS/zipalign"
APKSIGNER="$BUILD_TOOLS/apksigner"

# Clean build artifacts
rm -rf "$DIR/build"
mkdir -p "$DIR/build/compiled_res" "$DIR/build/gen" "$DIR/build/classes" "$DIR/build/dex"

# 1. Compile Resources with AAPT2
echo "[1/6] Compiling Android Resources with AAPT2..."
"$AAPT2" compile --dir "$DIR/res" -o "$DIR/build/compiled_res.zip"

echo "[2/6] Linking Android Resources..."
"$AAPT2" link "$DIR/build/compiled_res.zip" \
  -I "$ANDROID_JAR" \
  --manifest "$DIR/AndroidManifest.xml" \
  --java "$DIR/build/gen" \
  -o "$DIR/build/resources.apk" \
  --auto-add-overlay

# 2. Compile Java Source
echo "[3/6] Compiling Java Sources..."
javac -encoding UTF-8 \
  -cp "$ANDROID_JAR" \
  -d "$DIR/build/classes" \
  $(find "$DIR/src" -name "*.java") \
  $(find "$DIR/build/gen" -name "*.java")

# 3. Convert Bytecode to DEX with D8
echo "[4/6] Converting Bytecode to DEX with D8..."
"$D8" --output "$DIR/build/dex" \
  --lib "$ANDROID_JAR" \
  $(find "$DIR/build/classes" -name "*.class")

# 4. Package & Align APK
echo "[5/6] Packaging, Aligning APK..."
cp "$DIR/build/resources.apk" "$DIR/build/unaligned.apk"
cd "$DIR/build/dex"
zip -u "$DIR/build/unaligned.apk" classes.dex
cd "$DIR"
zip -ur "$DIR/build/unaligned.apk" assets/

"$ZIPALIGN" -f -p 4 "$DIR/build/unaligned.apk" "$DIR/build/aligned.apk"

# 5. Sign APK
echo "[6/6] Signing APK with debug keystore..."
KEYSTORE="$DIR/debug.keystore"
if [ ! -f "$KEYSTORE" ]; then
  echo "Generating debug keystore..."
  keytool -genkey -v -keystore "$KEYSTORE" -alias androiddebugkey -keyalg RSA -keysize 2048 -validity 10000 \
    -storepass android -keypass android -dname "CN=OmniHost Debug,O=Alumungandr,C=US"
fi

"$APKSIGNER" sign --ks "$KEYSTORE" --ks-pass pass:android --key-pass pass:android \
  --out "$DIR/omnihost.apk" "$DIR/build/aligned.apk"

cp "$DIR/omnihost.apk" "$ROOT_DIR/omnihost.apk"

echo "=== SUCCESS! Standalone Android APK created at: $DIR/omnihost.apk and $ROOT_DIR/omnihost.apk ==="
ls -lh "$DIR/omnihost.apk"
